import asyncio
from datetime import datetime, timezone
from typing import Optional

import dramatiq
from dramatiq import middleware
from sqlalchemy.ext.asyncio import AsyncSession

from workers.app.broker import broker
from backend.app import crud, models, schemas
from backend.app.database import async_session
from backend.app.security import decrypt_value
from browser.app.driver import PlaywrightDriver
from browser.app.crawler import AppCrawler
from integrations.app.github_client import GitHubClient
from agents.app.factory import get_agent_by_name


def get_db():
    return async_session()


async def _log(execution_id: int, level: str, message: str):
    async with get_db() as db:
        await crud.append_execution_log(db, execution_id, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "context": {},
        })


@dramatiq.actor
def run_execution(execution_id: int):
    asyncio.run(_run_execution_async(execution_id))


async def _run_execution_async(execution_id: int):
    async with get_db() as db:
        execution = await crud.update_execution_status(db, execution_id, "running")
        if not execution:
            return
        project = await crud.get_project(db, execution.project_id)
        if not project:
            await crud.update_execution_status(db, execution_id, "failed", "Project not found")
            return

        await _log(execution_id, "info", f"Starting execution for project {project.name}")

        # Run Playwright tests
        try:
            test_data = await _run_playwright_tests(db, execution_id, project)
            await _log(execution_id, "info", f"Tests completed. Visited {len(test_data['pages_visited'])} pages")
        except Exception as e:
            await crud.update_execution_status(db, execution_id, "failed", str(e))
            await _log(execution_id, "error", f"Playwright tests failed: {e}")
            return

        # Detect bugs
        try:
            await _detect_bugs(db, execution_id, test_data)
            await _log(execution_id, "info", "Bug detection completed")
        except Exception as e:
            await crud.update_execution_status(db, execution_id, "failed", str(e))
            await _log(execution_id, "error", f"Bug detection failed: {e}")
            return

        await crud.update_execution_status(db, execution_id, "completed")
        await _log(execution_id, "info", "Execution completed")


async def _run_playwright_tests(db: AsyncSession, execution_id: int, project: models.Project):
    driver = PlaywrightDriver()
    await driver.start(headless=True, video_dir="videos/")

    test_session = models.TestSession(
        execution_id=execution_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(test_session)
    await db.flush()
    await db.refresh(test_session)

    password = None
    if project.app_password_encrypted:
        password = decrypt_value(project.app_password_encrypted)

    crawler = AppCrawler(driver, project.app_url, max_pages=20)
    result = await crawler.run(username=project.app_username, password=password)

    test_session.browser_context_id = driver.context._impl_obj._browser_context_id if driver.context else None
    test_session.screenshots = result["screenshots"]
    test_session.console_logs = result["console_logs"]
    test_session.network_requests = result["network_requests"]
    test_session.pages_visited = result["pages_visited"]
    test_session.completed_at = datetime.now(timezone.utc)
    test_session.duration_seconds = (
        (test_session.completed_at - test_session.started_at).total_seconds()
        if test_session.started_at else 0
    )
    await db.flush()
    await db.refresh(test_session)
    await driver.stop()
    return result


async def _detect_bugs(db: AsyncSession, execution_id: int, test_data: dict):
    execution = await crud.get_execution(db, execution_id)
    if not execution:
        return

    # Use tester agent if available
    try:
        agent = await get_agent_by_name(db, "tester")
        bugs = await agent.run_json({
            "console_logs": test_data["console_logs"],
            "network_requests": test_data["network_requests"],
            "broken_elements": test_data["broken_elements"],
            "pages_visited": test_data["pages_visited"],
        })
        if not isinstance(bugs, list):
            bugs = []
    except Exception:
        # Fallback to rule-based detection
        bugs = _rule_based_detect(test_data)

    total = 0
    for bug in bugs:
        if bug.get("false_positive"):
            continue
        total += 1
        ticket = schemas.TicketCreate(
            execution_id=execution_id,
            title=bug.get("title", "Unknown bug"),
            description=bug.get("description", ""),
            severity=bug.get("severity", "medium"),
            category=bug.get("category", "functionality"),
            console_logs=bug.get("evidence"),
        )
        db_ticket = await crud.create_ticket(db, ticket)
        create_github_issue.send(db_ticket.id)

    execution.total_bugs_found = total
    await db.flush()
    await db.refresh(execution)


def _rule_based_detect(test_data: dict):
    bugs = []
    seen = set()
    for log in test_data.get("console_logs", []):
        if log.get("level") in ("error",) and log.get("message") not in seen:
            seen.add(log["message"])
            bugs.append({
                "title": f"JS Error: {log['message'][:80]}",
                "description": f"Console error on {log.get('url')}: {log['message']}",
                "severity": "high",
                "category": "js_error",
                "evidence": [log],
            })
    for req in test_data.get("network_requests", []):
        status = req.get("status")
        if status and status >= 400 and req.get("url") not in seen:
            seen.add(req["url"])
            bugs.append({
                "title": f"Network Error {status}: {req['url'][:80]}",
                "description": f"Request to {req['url']} returned status {status}",
                "severity": "high" if status >= 500 else "medium",
                "category": "network_error",
                "evidence": [req],
            })
    for el in test_data.get("broken_elements", []):
        bugs.append({
            "title": f"Broken UI element: {el.get('type')}",
            "description": f"Found broken element: {el}",
            "severity": "medium",
            "category": "ui_broken",
            "evidence": [el],
        })
    return bugs


@dramatiq.actor
def create_github_issue(ticket_id: int):
    asyncio.run(_create_github_issue_async(ticket_id))


async def _create_github_issue_async(ticket_id: int):
    async with get_db() as db:
        ticket = await crud.get_ticket(db, ticket_id)
        if not ticket:
            return
        execution = await crud.get_execution(db, ticket.execution_id)
        if not execution:
            return
        project = await crud.get_project(db, execution.project_id)
        if not project or not project.github_token_encrypted:
            return

        token = decrypt_value(project.github_token_encrypted)
        client = GitHubClient(token)
        try:
            labels = ["bug", ticket.severity, ticket.category]
            body_parts = [ticket.description]
            if ticket.console_logs:
                body_parts.append("\n### Console Logs\n```json\n" + str(ticket.console_logs) + "\n```")
            if ticket.network_logs:
                body_parts.append("\n### Network Logs\n```json\n" + str(ticket.network_logs) + "\n```")
            issue = await client.create_issue(
                project.github_repo_owner,
                project.github_repo_name,
                ticket.title,
                "\n".join(body_parts),
                labels=labels,
            )
            ticket.github_issue_number = issue.get("number")
            ticket.github_issue_url = issue.get("html_url")
            await db.flush()
            await db.refresh(ticket)
            generate_patch.send(ticket_id)
        except Exception as e:
            await _log(execution.id, "error", f"Failed to create GitHub issue: {e}")
        finally:
            await client.close()


@dramatiq.actor
def generate_patch(ticket_id: int):
    asyncio.run(_generate_patch_async(ticket_id))


async def _generate_patch_async(ticket_id: int):
    async with get_db() as db:
        ticket = await crud.get_ticket(db, ticket_id)
        if not ticket:
            return
        ticket.status = "patching"
        await db.flush()

        execution = await crud.get_execution(db, ticket.execution_id)
        if not execution:
            return
        project = await crud.get_project(db, execution.project_id)
        if not project or not project.github_token_encrypted:
            return

        token = decrypt_value(project.github_token_encrypted)
        client = GitHubClient(token)
        try:
            # Gather some repo files for context (heuristic: list root and src)
            code_files = []
            for path in ["", "src"]:
                try:
                    files = await client.list_repo_files(project.github_repo_owner, project.github_repo_name, path)
                    for f in files:
                        if f.get("type") == "file" and f.get("name", "").endswith((".js", ".ts", ".tsx", ".py", ".html", ".css")):
                            content = await client.get_file_content(
                                project.github_repo_owner, project.github_repo_name, f["path"]
                            )
                            if content:
                                code_files.append({"path": f["path"], "content": content})
                            if len(code_files) >= 5:
                                break
                except Exception:
                    pass
                if len(code_files) >= 5:
                    break

            agent = await get_agent_by_name(db, "coder")
            patch_text = await agent.run({
                "bug_description": ticket.description,
                "code_files": code_files,
            })
            ticket.patch_content = patch_text
            await db.flush()
            await db.refresh(ticket)
            create_pull_request.send(ticket_id)
        except Exception as e:
            await _log(execution.id, "error", f"Patch generation failed: {e}")
        finally:
            await client.close()


@dramatiq.actor
def create_pull_request(ticket_id: int):
    asyncio.run(_create_pull_request_async(ticket_id))


async def _create_pull_request_async(ticket_id: int):
    async with get_db() as db:
        ticket = await crud.get_ticket(db, ticket_id)
        if not ticket or not ticket.patch_content:
            return
        execution = await crud.get_execution(db, ticket.execution_id)
        if not execution:
            return
        project = await crud.get_project(db, execution.project_id)
        if not project or not project.github_token_encrypted:
            return

        token = decrypt_value(project.github_token_encrypted)
        client = GitHubClient(token)
        try:
            default_branch = await client.get_default_branch(project.github_repo_owner, project.github_repo_name)
            branch_name = f"fix/issue-{ticket.github_issue_number or ticket_id}"
            await client.create_branch(project.github_repo_owner, project.github_repo_name, branch_name, default_branch)

            # Apply patch as a single commit to a representative file (simplified)
            await client.create_or_update_file(
                project.github_repo_owner,
                project.github_repo_name,
                f"patches/fix-{ticket_id}.patch",
                f"fix: {ticket.title}",
                ticket.patch_content,
                branch_name,
            )

            pr = await client.create_pull_request(
                project.github_repo_owner,
                project.github_repo_name,
                f"Fix: {ticket.title}",
                f"{ticket.description}\n\nCloses #{ticket.github_issue_number or ''}",
                branch_name,
                default_branch,
            )
            ticket.github_pr_number = pr.get("number")
            ticket.github_pr_url = pr.get("html_url")
            ticket.status = "pr_open"
            await db.flush()
            await db.refresh(ticket)
        except Exception as e:
            await _log(execution.id, "error", f"PR creation failed: {e}")
        finally:
            await client.close()


@dramatiq.actor
def trigger_deployment(ticket_id: int):
    asyncio.run(_trigger_deployment_async(ticket_id))


async def _trigger_deployment_async(ticket_id: int):
    async with get_db() as db:
        ticket = await crud.get_ticket(db, ticket_id)
        if not ticket:
            return
        execution = await crud.get_execution(db, ticket.execution_id)
        if not execution:
            return
        project = await crud.get_project(db, execution.project_id)
        if not project:
            return

        ticket.status = "deploying"
        await db.flush()
        await _log(execution.id, "info", f"Deployment triggered for ticket {ticket_id}")

        if project.deploy_webhook_url:
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        project.deploy_webhook_url,
                        json={
                            "ticket_id": ticket_id,
                            "pr_number": ticket.github_pr_number,
                            "commit_sha": ticket.patch_commit_sha,
                        },
                        timeout=30.0,
                    )
            except Exception as e:
                await _log(execution.id, "error", f"Webhook deployment failed: {e}")

        ticket.status = "deployed"
        await db.flush()
        verify_fix.send(ticket_id)


@dramatiq.actor
def verify_fix(ticket_id: int):
    asyncio.run(_verify_fix_async(ticket_id))


async def _verify_fix_async(ticket_id: int):
    async with get_db() as db:
        ticket = await crud.get_ticket(db, ticket_id)
        if not ticket:
            return
        execution = await crud.get_execution(db, ticket.execution_id)
        if not execution:
            return
        project = await crud.get_project(db, execution.project_id)
        if not project:
            return

        ticket.status = "verifying"
        await db.flush()
        await _log(execution.id, "info", f"Verifying fix for ticket {ticket_id}")

        # Re-run playwright on the app
        driver = PlaywrightDriver()
        await driver.start(headless=True)
        password = None
        if project.app_password_encrypted:
            password = decrypt_value(project.app_password_encrypted)
        crawler = AppCrawler(driver, project.app_url, max_pages=5)
        result = await crawler.run(username=project.app_username, password=password)
        await driver.stop()

        # Simple verification: check if same error still appears
        old_msgs = set()
        for log in ticket.console_logs or []:
            old_msgs.add(log.get("message", ""))

        new_errors = [log for log in result["console_logs"] if log.get("level") == "error"]
        still_present = any(log.get("message") in old_msgs for log in new_errors)

        if not still_present:
            ticket.status = "verified"
            await db.flush()
            await _log(execution.id, "info", f"Ticket {ticket_id} verified as fixed")

            # Close GitHub issue
            if project.github_token_encrypted and ticket.github_issue_number:
                token = decrypt_value(project.github_token_encrypted)
                client = GitHubClient(token)
                try:
                    await client.close_issue(project.github_repo_owner, project.github_repo_name, ticket.github_issue_number)
                    await client.create_comment(
                        project.github_repo_owner,
                        project.github_repo_name,
                        ticket.github_issue_number,
                        f"Fixed by PR #{ticket.github_pr_number or ''}",
                    )
                except Exception as e:
                    await _log(execution.id, "error", f"Failed to close issue: {e}")
                finally:
                    await client.close()
            execution.total_bugs_fixed = (execution.total_bugs_fixed or 0) + 1
            await db.flush()
        else:
            if ticket.retry_count < ticket.max_retries:
                ticket.status = "open"
                ticket.retry_count += 1
                await db.flush()
                await _log(execution.id, "warning", f"Ticket {ticket_id} not fixed, retrying ({ticket.retry_count}/{ticket.max_retries})")
                generate_patch.send(ticket_id)
            else:
                ticket.status = "failed"
                await db.flush()
                await _log(execution.id, "error", f"Ticket {ticket_id} failed after max retries")

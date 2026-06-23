"""
Continuous correction session worker.
Runs in a loop until all tickets are resolved (100% resolution).
No time limit - keeps going until done.
"""
import asyncio
import dramatiq
from datetime import datetime, timezone
from sqlalchemy import select, func, desc, case
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from workers.app.broker import broker
from backend.app import models, crud
from backend.app.security import decrypt_value
from integrations.app.github_client import GitHubClient


# WORK-02: la session continue est concue pour tourner longtemps (potentiellement des heures).
# Le TimeLimit Dramatiq par defaut (10 min) la tuerait. On releve la limite a 7 jours.
_SESSION_TIME_LIMIT_MS = 7 * 24 * 60 * 60 * 1000


@dramatiq.actor(max_retries=0, time_limit=_SESSION_TIME_LIMIT_MS)
def run_continuous_session(session_id: int):
    """Run a continuous correction session until all tickets are resolved."""
    asyncio.run(_run_continuous_session_async(session_id))


# Lazy engine/session creation to avoid event loop issues
_engine = None
_async_session_factory = None


def _get_session_factory():
    global _engine, _async_session_factory
    if _async_session_factory is None:
        from backend.app.config import settings
        # NullPool: evite de reutiliser des connexions liees a un event loop ferme entre messages.
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
            poolclass=NullPool,
        )
        _async_session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


def get_db():
    return _get_session_factory()()


async def _run_continuous_session_async(session_id: int):
    """
    Main loop for continuous session:
    1. Find all open tickets for the project
    2. Process each ticket (generate patch, review, deploy, verify)
    3. Repeat until no more open tickets
    4. Mark session as completed
    """
    async with get_db() as db:
        session = await db.get(models.Session, session_id)
        if not session:
            return
        
        if session.status not in ["running", "pending"]:
            return
        
        # Mark session as running
        session.status = "running"
        session.started_at = datetime.now(timezone.utc)
        await db.commit()
        
        project = await crud.get_project(db, session.project_id)
        if not project:
            await _session_log(db, session_id, "error", f"Project {session.project_id} not found")
            session.status = "failed"
            await db.commit()
            return
        
        await _session_log(db, session_id, "info", f"Starting continuous session for project: {project.name}")
        
        # Main loop - keep going until no more open tickets
        iteration = 0
        while True:
            iteration += 1
            
            # Check if session is still running (might have been paused/stopped)
            await db.refresh(session)
            if session.status == "stopped":
                await _session_log(db, session_id, "info", "Session stopped by user")
                break
            if session.status == "paused":
                await _session_log(db, session_id, "info", "Session paused, waiting...")
                await asyncio.sleep(5)
                continue
            
            # Find all open tickets for this project
            open_tickets = await _get_open_tickets(db, project.id)
            
            if not open_tickets:
                in_progress = await _get_in_progress_tickets(db, project.id)
                if not in_progress:
                    await _session_log(db, session_id, "info", f"All tickets resolved! Session completed after {iteration} iterations")
                    session.status = "completed"
                    session.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    break
                else:
                    await _session_log(db, session_id, "info", f"Waiting for {len(in_progress)} tickets in progress...")
                    await asyncio.sleep(10)
                    continue
            
            await _session_log(db, session_id, "info", f"Iteration {iteration}: Found {len(open_tickets)} open tickets")
            
            session.total_tickets_found = len(open_tickets) + session.total_tickets_resolved + session.total_tickets_failed
            await db.commit()
            
            for ticket in open_tickets:
                await db.refresh(session)
                if session.status in ["stopped", "paused"]:
                    break
                
                await _session_log(db, session_id, "info", f"Processing ticket #{ticket.id}: {ticket.title[:80]}")
                session.current_ticket_id = ticket.id
                await db.commit()
                
                success = await _process_ticket(db, session_id, ticket, project)
                
                if success:
                    session.total_tickets_resolved += 1
                    await _session_log(db, session_id, "info", f"Ticket #{ticket.id} resolved successfully")
                else:
                    session.total_tickets_failed += 1
                    await _session_log(db, session_id, "error", f"Ticket #{ticket.id} failed to resolve")
                
                session.current_ticket_id = None
                await db.commit()
            
            await asyncio.sleep(2)


async def _get_open_tickets(db, project_id: int) -> list[models.Ticket]:
    """Get all open tickets for a project."""
    result = await db.execute(
        select(models.Ticket)
        .join(models.Execution)
        .where(
            models.Execution.project_id == project_id,
            models.Ticket.status == "open",
        )
        .order_by(
            case(
                (models.Ticket.severity == "critical", 1),
                (models.Ticket.severity == "high", 2),
                (models.Ticket.severity == "medium", 3),
                else_=4,
            ),
            models.Ticket.created_at,
        )
        .limit(50)
    )
    return list(result.scalars().all())


async def _get_in_progress_tickets(db, project_id: int) -> list[models.Ticket]:
    """Get tickets currently being processed."""
    result = await db.execute(
        select(models.Ticket)
        .join(models.Execution)
        .where(
            models.Execution.project_id == project_id,
            models.Ticket.status.in_(["patching", "reviewing", "testing", "deploying"]),
        )
    )
    return list(result.scalars().all())


async def _process_ticket(db, session_id: int, ticket: models.Ticket, project: models.Project) -> bool:
    """Process a single ticket through the full pipeline."""
    start_time = datetime.now(timezone.utc)
    
    try:
        await _session_log(db, session_id, "info", f"Generating patch for ticket #{ticket.id}", ticket.id)
        ticket.status = "patching"
        await db.commit()
        
        await _generate_patch_sync(db, ticket.id)
        
        await db.refresh(ticket)
        if not ticket.patch_content:
            await _session_log(db, session_id, "error", f"Failed to generate patch for ticket #{ticket.id}", ticket.id)
            ticket.status = "failed"
            await db.commit()
            return False
        
        await _session_log(db, session_id, "info", f"Patch generated for ticket #{ticket.id}", ticket.id)
        
        await _session_log(db, session_id, "info", f"Reviewing patch for ticket #{ticket.id}", ticket.id)
        ticket.status = "reviewing"
        await db.commit()
        
        await _review_patch_sync(db, ticket.id)
        
        await db.refresh(ticket)
        if ticket.status == "failed":
            await _session_log(db, session_id, "error", f"Patch rejected for ticket #{ticket.id}", ticket.id)
            return False
        
        await _session_log(db, session_id, "info", f"Patch approved for ticket #{ticket.id}", ticket.id)
        
        await _session_log(db, session_id, "info", f"Creating PR for ticket #{ticket.id}", ticket.id)
        ticket.status = "creating_pr"
        await db.commit()
        
        await _create_pr_sync(db, ticket.id, project)
        
        await db.refresh(ticket)
        if not ticket.github_pr_number:
            await _session_log(db, session_id, "error", f"Failed to create PR for ticket #{ticket.id}", ticket.id)
            ticket.status = "failed"
            await db.commit()
            return False
        
        await _session_log(db, session_id, "info", f"PR #{ticket.github_pr_number} created for ticket #{ticket.id}", ticket.id)
        
        if project.deploy_webhook_url:
            await _session_log(db, session_id, "info", f"Deploying ticket #{ticket.id}", ticket.id)
            ticket.status = "deploying"
            await db.commit()
            
            await _deploy_sync(db, ticket.id, project)
            
            await _session_log(db, session_id, "info", f"Deployed ticket #{ticket.id}", ticket.id)
        
        await _session_log(db, session_id, "info", f"Verifying fix for ticket #{ticket.id}", ticket.id)
        ticket.status = "verifying"
        await db.commit()
        
        verified = await _verify_fix_sync(db, ticket.id)
        
        await db.refresh(ticket)
        
        end_time = datetime.now(timezone.utc)
        ticket.resolution_time_seconds = (end_time - start_time).total_seconds()
        
        if verified:
            ticket.status = "verified"
            await _session_log(db, session_id, "info", f"Ticket #{ticket.id} fully resolved and verified!", ticket.id)
            await db.commit()
            return True
        else:
            ticket.status = "failed"
            await _session_log(db, session_id, "error", f"Verification failed for ticket #{ticket.id}", ticket.id)
            await db.commit()
            return False
            
    except Exception as e:
        await _session_log(db, session_id, "error", f"Exception processing ticket #{ticket.id}: {str(e)}", ticket.id)
        ticket.status = "failed"
        await db.commit()
        return False


async def _generate_patch_sync(db, ticket_id: int):
    """Generate patch synchronously."""
    from workers.app.tasks import _generate_patch_async
    await _generate_patch_async(ticket_id, attempt=1, feedback="")


async def _review_patch_sync(db, ticket_id: int):
    """Review patch synchronously."""
    from workers.app.tasks import _review_patch_async
    await _review_patch_async(ticket_id, attempt=1)


async def _create_pr_sync(db, ticket_id: int, project: models.Project):
    """Create PR synchronously."""
    from workers.app.tasks import _create_pull_request_async
    await _create_pull_request_async(ticket_id)


async def _deploy_sync(db, ticket_id: int, project: models.Project):
    """Deploy synchronously."""
    import httpx
    from backend.app.utils import validate_url_no_ssrf
    ticket = await db.get(models.Ticket, ticket_id)
    if project.deploy_webhook_url and ticket:
        # SEC-04: valider l'URL avant POST sortant (anti-SSRF)
        try:
            validate_url_no_ssrf(project.deploy_webhook_url)
        except ValueError as e:
            print(f"[deploy] deploy_webhook_url rejete (SSRF) pour ticket {ticket_id}: {e}")
            return
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


async def _verify_fix_sync(db, ticket_id: int) -> bool:
    """Verify fix synchronously."""
    from workers.app.tasks import _verify_fix_async
    await _verify_fix_async(ticket_id)
    ticket = await db.get(models.Ticket, ticket_id)
    return ticket and ticket.status == "verified"


async def _session_log(db, session_id: int, level: str, message: str, ticket_id: Optional[int] = None):
    """Add a log entry to the session."""
    session = await db.get(models.Session, session_id)
    if not session:
        return
    
    logs = session.logs or []
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "ticket_id": ticket_id,
    })
    session.logs = logs
    await db.commit()
    
    try:
        from backend.app.routers.sessions import manager
        await manager.broadcast({
            "type": "log",
            "data": logs[-1],
        }, session_id)
    except Exception:
        pass
    
    print(f"[Session {session_id}] [{level}] {message}")

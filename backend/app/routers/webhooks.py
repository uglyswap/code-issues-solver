from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hmac
import hashlib

from backend.app import schemas, crud, models
from backend.app.database import get_db
from backend.app.config import settings

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

GITHUB_WEBHOOK_SECRET = settings.jwt_secret


def verify_github_signature(payload: bytes, signature: str) -> bool:
    if not signature:
        return False
    expected = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    payload_data = await request.json()
    event = x_github_event

    if event == "pull_request":
        action = payload_data.get("action")
        pr = payload_data.get("pull_request", {})
        merged = pr.get("merged", False)
        if action == "closed" and merged:
            pr_number = pr.get("number")
            result = await db.execute(
                select(models.Ticket).where(models.Ticket.github_pr_number == pr_number)
            )
            for ticket in result.scalars().all():
                ticket.status = "merged"
                await db.flush()
                from workers.app.tasks import trigger_deployment
                trigger_deployment.send(ticket.id)

    elif event == "deployment_status":
        deployment_status = payload_data.get("deployment_status", {})
        state = deployment_status.get("state")
        if state == "success":
            repo = payload_data.get("repository", {})
            full_name = repo.get("full_name", "")
            parts = full_name.split("/") if "/" in full_name else ("", "")
            if len(parts) == 2:
                owner, name = parts
                project_res = await db.execute(
                    select(models.Project).where(
                        models.Project.github_repo_owner == owner,
                        models.Project.github_repo_name == name,
                    )
                )
                project = project_res.scalar_one_or_none()
                if project:
                    exec_res = await db.execute(
                        select(models.Execution)
                        .where(models.Execution.project_id == project.id)
                        .order_by(models.Execution.created_at.desc())
                        .limit(1)
                    )
                    recent_exec = exec_res.scalar_one_or_none()
                    if recent_exec:
                        for ticket in recent_exec.tickets:
                            if ticket.status == "deployed":
                                from workers.app.tasks import verify_fix
                                verify_fix.send(ticket.id)

    return {"status": "ok"}

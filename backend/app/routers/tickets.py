from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user
from workers.app.tasks import generate_patch

router = APIRouter(prefix="/api", tags=["tickets"])


@router.get("/projects/{project_id}/tickets", response_model=schemas.PaginatedResponse)
async def list_tickets(
    project_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    skip = (page - 1) * per_page
    items, total = await crud.get_tickets(db, project_id, skip=skip, limit=per_page, status=status, severity=severity, category=category)
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/tickets/{ticket_id}", response_model=schemas.TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_ticket = await crud.get_ticket(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return db_ticket


@router.put("/tickets/{ticket_id}", response_model=schemas.TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket: schemas.TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    ALLOWED_STATUSES = {
        "open", "patching", "reviewing", "testing", "creating_pr", "pr_open",
        "deploying", "deployed", "verifying", "verified", "merged", "failed", "ignored",
    }
    if ticket.status is not None and ticket.status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {ticket.status}")
    if ticket.status == "ignored" and not ticket.ignored_reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ignored_reason is required when status is ignored")
    db_ticket = await crud.update_ticket(db, ticket_id, ticket)
    if not db_ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return db_ticket


@router.post("/tickets/{ticket_id}/retry", response_model=schemas.TicketResponse)
async def retry_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_ticket = await crud.get_ticket(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    # ROUTERS-14: ne pas autoriser un retry au-dela de max_retries (boucle infinie sinon)
    if db_ticket.retry_count >= (db_ticket.max_retries or 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max retries reached ({db_ticket.retry_count}/{db_ticket.max_retries})",
        )
    db_ticket.retry_count += 1
    db_ticket.status = "open"
    await db.flush()
    await db.refresh(db_ticket)
    generate_patch.send(ticket_id)
    return db_ticket

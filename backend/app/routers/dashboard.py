from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from typing import Optional
from datetime import datetime, timedelta

from backend.app import schemas, crud, models
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get global dashboard statistics."""
    # Base query
    query = select(models.Ticket)
    if project_id:
        query = query.join(models.Execution).where(models.Execution.project_id == project_id)
    
    # Total tickets
    total_result = await db.execute(select(func.count(models.Ticket.id)))
    total_tickets = total_result.scalar() or 0
    
    # Tickets by status
    status_query = select(
        models.Ticket.status,
        func.count(models.Ticket.id).label('count')
    ).group_by(models.Ticket.status)
    if project_id:
        status_query = status_query.join(models.Execution).where(models.Execution.project_id == project_id)
    
    status_result = await db.execute(status_query)
    tickets_by_status = {row[0]: row[1] for row in status_result}
    
    resolved_tickets = tickets_by_status.get('verified', 0) + tickets_by_status.get('deployed', 0)
    open_tickets = tickets_by_status.get('open', 0)
    in_progress_tickets = (
        tickets_by_status.get('patching', 0) + 
        tickets_by_status.get('reviewing', 0) + 
        tickets_by_status.get('testing', 0)
    )
    failed_tickets = tickets_by_status.get('failed', 0)
    
    # Resolution rate
    resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0.0
    
    # Average resolution time
    avg_time_query = select(func.avg(models.Ticket.resolution_time_seconds))
    if project_id:
        avg_time_query = avg_time_query.join(models.Execution).where(models.Execution.project_id == project_id)
    avg_time_query = avg_time_query.where(models.Ticket.resolution_time_seconds.isnot(None))
    
    avg_time_result = await db.execute(avg_time_query)
    avg_resolution_time = avg_time_result.scalar()
    
    # Tickets by severity
    severity_query = select(
        models.Ticket.severity,
        func.count(models.Ticket.id).label('count')
    ).group_by(models.Ticket.severity)
    if project_id:
        severity_query = severity_query.join(models.Execution).where(models.Execution.project_id == project_id)
    
    severity_result = await db.execute(severity_query)
    tickets_by_severity = {row[0]: row[1] for row in severity_result}
    
    # Tickets by category
    category_query = select(
        models.Ticket.category,
        func.count(models.Ticket.id).label('count')
    ).group_by(models.Ticket.category)
    if project_id:
        category_query = category_query.join(models.Execution).where(models.Execution.project_id == project_id)
    
    category_result = await db.execute(category_query)
    tickets_by_category = {row[0]: row[1] for row in category_result}
    
    return schemas.DashboardStats(
        total_tickets=total_tickets,
        resolved_tickets=resolved_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        failed_tickets=failed_tickets,
        resolution_rate=resolution_rate,
        avg_resolution_time_seconds=avg_resolution_time,
        tickets_by_severity=tickets_by_severity,
        tickets_by_category=tickets_by_category,
        tickets_by_status=tickets_by_status,
    )


@router.get("/timeline", response_model=list[schemas.TimelineEvent])
async def get_timeline(
    project_id: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get recent activity timeline."""
    query = select(models.Ticket).order_by(desc(models.Ticket.updated_at)).limit(limit)
    
    if project_id:
        query = query.join(models.Execution).where(models.Execution.project_id == project_id)
    
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    timeline = []
    for ticket in tickets:
        # Create timeline events based on ticket status and attempts
        if ticket.attempts_log:
            for attempt in ticket.attempts_log:
                timeline.append(schemas.TimelineEvent(
                    timestamp=datetime.fromisoformat(attempt['timestamp']),
                    event_type=attempt.get('status', 'unknown'),
                    ticket_id=ticket.id,
                    ticket_title=ticket.title,
                    severity=ticket.severity,
                    message=attempt.get('message', f"Attempt {attempt.get('attempt', 1)}"),
                    execution_id=ticket.execution_id,
                ))
        else:
            # Fallback: create event from ticket status
            timeline.append(schemas.TimelineEvent(
                timestamp=ticket.updated_at,
                event_type=ticket.status,
                ticket_id=ticket.id,
                ticket_title=ticket.title,
                severity=ticket.severity,
                message=f"Ticket {ticket.status}",
                execution_id=ticket.execution_id,
            ))
    
    # Sort by timestamp descending
    timeline.sort(key=lambda x: x.timestamp, reverse=True)
    return timeline[:limit]


@router.get("/sessions/active", response_model=list[schemas.SessionResponse])
async def get_active_sessions(
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get all active (running/paused) sessions."""
    query = select(models.Session).where(
        models.Session.status.in_(['running', 'paused', 'pending'])
    )
    
    if project_id:
        query = query.where(models.Session.project_id == project_id)
    
    query = query.order_by(desc(models.Session.created_at))
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        schemas.SessionResponse(
            id=s.id,
            project_id=s.project_id,
            status=s.status,
            trigger_type=s.trigger_type,
            started_at=s.started_at,
            completed_at=s.completed_at,
            total_tickets_found=s.total_tickets_found,
            total_tickets_resolved=s.total_tickets_resolved,
            total_tickets_failed=s.total_tickets_failed,
            current_ticket_id=s.current_ticket_id,
            logs=s.logs or [],
            auto_close_github_issues=s.auto_close_github_issues,
            max_concurrent_tickets=s.max_concurrent_tickets,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("", response_model=schemas.DashboardResponse)
async def get_dashboard(
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get complete dashboard data."""
    stats = await get_dashboard_stats(project_id, db, current_user)
    timeline = await get_timeline(project_id, 20, db, current_user)
    active_sessions = await get_active_sessions(project_id, db, current_user)
    
    return schemas.DashboardResponse(
        stats=stats,
        recent_activity=timeline,
        active_sessions=active_sessions,
    )

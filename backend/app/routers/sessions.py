from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from datetime import datetime, timezone
import asyncio
import json

from backend.app import schemas, crud, models
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user
from workers.app.session_worker import run_continuous_session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=schemas.SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session: schemas.SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Create a new continuous correction session."""
    # Verify project exists
    project = await crud.get_project(db, session.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create session
    db_session = models.Session(
        project_id=session.project_id,
        status="pending",
        trigger_type=session.trigger_type,
        auto_close_github_issues=session.auto_close_github_issues,
        max_concurrent_tickets=session.max_concurrent_tickets,
        logs=[],
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    
    # Start the session worker
    run_continuous_session.send(int(db_session.id))
    
    return db_session


@router.get("", response_model=list[schemas.SessionResponse])
async def list_sessions(
    project_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """List all sessions."""
    query = select(models.Session)
    
    if project_id:
        query = query.where(models.Session.project_id == project_id)
    
    if status_filter:
        query = query.where(models.Session.status == status_filter)
    
    query = query.order_by(desc(models.Session.created_at)).limit(limit)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return sessions


@router.get("/{session_id}", response_model=schemas.SessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get session details."""
    session = await db.get(models.Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/pause", response_model=schemas.SessionResponse)
async def pause_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Pause a running session."""
    session = await db.get(models.Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "running":
        raise HTTPException(status_code=400, detail="Session is not running")
    
    session.status = "paused"
    
    # Add log entry
    logs = session.logs or []
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "message": "Session paused by user",
        "ticket_id": None,
    })
    session.logs = logs
    
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/{session_id}/resume", response_model=schemas.SessionResponse)
async def resume_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Resume a paused session."""
    session = await db.get(models.Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "paused":
        raise HTTPException(status_code=400, detail="Session is not paused")
    
    session.status = "running"
    
    # Add log entry
    logs = session.logs or []
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "message": "Session resumed by user",
        "ticket_id": None,
    })
    session.logs = logs
    
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=schemas.SessionResponse)
async def stop_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Stop a session completely."""
    session = await db.get(models.Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status in ["completed", "stopped"]:
        raise HTTPException(status_code=400, detail="Session is already completed/stopped")
    
    session.status = "stopped"
    session.completed_at = datetime.now(timezone.utc)
    
    # Add log entry
    logs = session.logs or []
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "message": "Session stopped by user",
        "ticket_id": None,
    })
    session.logs = logs
    
    await db.commit()
    await db.refresh(session)
    return session


# WebSocket for real-time session updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
    
    async def connect(self, session_id: int, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, session_id: int, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def send_personal_message(self, message: dict, session_id: int):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass  # Connection closed
    
    async def broadcast(self, message: dict, session_id: int):
        await self.send_personal_message(message, session_id)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(...),
):
    """WebSocket for real-time session logs. Requires JWT token in query string."""
    # Validate JWT token
    from backend.app.security import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return
    
    await manager.connect(session_id, websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Client can send ping to keep alive
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


# Helper function to add log to session (to be called from workers)
async def add_session_log(db: AsyncSession, session_id: int, level: str, message: str, ticket_id: Optional[int] = None):
    """Add a log entry to a session."""
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
    
    # Broadcast to WebSocket clients
    await manager.broadcast({
        "type": "log",
        "data": logs[-1],
    }, session_id)

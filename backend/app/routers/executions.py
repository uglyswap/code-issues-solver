from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json
import asyncio

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user
from backend.app.security import decode_access_token
from workers.app.tasks import run_execution

router = APIRouter(prefix="/api", tags=["executions"])
security_bearer = HTTPBearer(auto_error=False)


def _get_user_from_token(token: str):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    return payload


@router.post("/projects/{project_id}/executions", response_model=schemas.ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_execution(
    project_id: int,
    data: schemas.ExecutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db_execution = await crud.create_execution(db, project_id, data.trigger_type)
    run_execution.send(db_execution.id)
    return db_execution


@router.get("/projects/{project_id}/executions", response_model=schemas.PaginatedResponse)
async def list_executions(
    project_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    skip = (page - 1) * per_page
    items, total = await crud.get_executions(db, project_id, skip=skip, limit=per_page, status=status)
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/executions/{execution_id}", response_model=schemas.ExecutionDetailResponse)
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_execution = await crud.get_execution(db, execution_id)
    if not db_execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return db_execution


@router.get("/executions/{execution_id}/logs")
async def execution_logs(
    execution_id: int,
    token: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
):
    auth_token = token or (credentials.credentials if credentials else None)
    user_payload = _get_user_from_token(auth_token) if auth_token else None
    if not user_payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    db_execution = await crud.get_execution(db, execution_id)
    if not db_execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    async def event_generator():
        last_index = 0
        while True:
            await db.refresh(db_execution)
            logs = db_execution.logs or []
            if len(logs) > last_index:
                for log in logs[last_index:]:
                    yield f"data: {json.dumps(log)}\n\n"
                last_index = len(logs)
            if db_execution.status in ("completed", "failed"):
                yield f"data: {json.dumps({'level':'info','message':'Stream ended','timestamp':'','context':{}})}\n\n"
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/executions/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Delete an execution. Only pending, completed, or failed executions can be deleted."""
    db_execution = await crud.get_execution(db, execution_id)
    if not db_execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    if db_execution.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot delete a running execution. Stop it first."
        )
    
    await crud.delete_execution(db, execution_id)
    return None


@router.post("/executions/{execution_id}/stop", response_model=schemas.ExecutionResponse)
async def stop_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Stop a running or pending execution."""
    db_execution = await crud.get_execution(db, execution_id)
    if not db_execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    if db_execution.status in ("completed", "failed", "stopped"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Execution is already {db_execution.status}"
        )
    
    db_execution = await crud.update_execution_status(db, execution_id, "stopped", "Manually stopped by user")
    return db_execution
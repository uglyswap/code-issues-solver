from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("", response_model=schemas.AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: schemas.AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_agent = await crud.create_agent(db, agent)
    return db_agent


@router.get("", response_model=schemas.PaginatedResponse)
async def list_agents(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    skip = (page - 1) * per_page
    items, total = await crud.get_agents(db, skip=skip, limit=per_page)
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{agent_id}", response_model=schemas.AgentResponse)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_agent = await crud.get_agent(db, agent_id)
    if not db_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return db_agent


@router.put("/{agent_id}", response_model=schemas.AgentResponse)
async def update_agent(
    agent_id: int,
    agent: schemas.AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_agent = await crud.update_agent(db, agent_id, agent)
    if not db_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return db_agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    deleted = await crud.delete_agent(db, agent_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return None

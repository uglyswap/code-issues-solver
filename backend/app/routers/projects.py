from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _project_to_dict(project, stats):
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "app_url": project.app_url,
        "app_username": project.app_username,
        "github_repo_owner": project.github_repo_owner,
        "github_repo_name": project.github_repo_name,
        "deploy_webhook_url": project.deploy_webhook_url,
        "schedule_cron": project.schedule_cron,
        "enabled": project.enabled,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "stats": stats,
    }


@router.post("", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: schemas.ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_project = await crud.create_project(db, project)
    stats = await crud.get_project_stats(db, db_project.id)
    return _project_to_dict(db_project, stats)


@router.get("", response_model=schemas.PaginatedResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    skip = (page - 1) * per_page
    items, total = await crud.get_projects(db, skip=skip, limit=per_page, enabled=enabled)
    enriched = []
    for item in items:
        stats = await crud.get_project_stats(db, item.id)
        enriched.append(_project_to_dict(item, stats))
    return {
        "items": enriched,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{project_id}", response_model=schemas.ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_project = await crud.get_project(db, project_id)
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    stats = await crud.get_project_stats(db, project_id)
    return _project_to_dict(db_project, stats)


@router.put("/{project_id}", response_model=schemas.ProjectResponse)
async def update_project(
    project_id: int,
    project: schemas.ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_project = await crud.update_project(db, project_id, project)
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    stats = await crud.get_project_stats(db, project_id)
    return _project_to_dict(db_project, stats)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    deleted = await crud.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return None

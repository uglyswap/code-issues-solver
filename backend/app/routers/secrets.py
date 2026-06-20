from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/projects/{project_id}/secrets", tags=["secrets"])


@router.post("", response_model=schemas.SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    project_id: int,
    secret: schemas.SecretCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db_secret = await crud.create_secret(db, project_id, secret)
    return db_secret


@router.get("", response_model=list[schemas.SecretResponse])
async def list_secrets(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    items = await crud.get_secrets(db, project_id)
    return items


@router.put("/{secret_id}", response_model=schemas.SecretResponse)
async def update_secret(
    project_id: int,
    secret_id: int,
    secret: schemas.SecretUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    db_secret = await crud.update_secret(db, secret_id, secret)
    if not db_secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return db_secret


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    project_id: int,
    secret_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    project = await crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    deleted = await crud.delete_secret(db, secret_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return None

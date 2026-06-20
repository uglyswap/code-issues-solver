from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.post("", response_model=schemas.AIProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider: schemas.AIProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_provider = await crud.create_ai_provider(db, provider)
    return db_provider


@router.get("", response_model=schemas.PaginatedResponse)
async def list_providers(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    skip = (page - 1) * per_page
    items, total = await crud.get_ai_providers(db, skip=skip, limit=per_page)
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/{provider_id}", response_model=schemas.AIProviderResponse)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_provider = await crud.get_ai_provider(db, provider_id)
    if not db_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return db_provider


@router.put("/{provider_id}", response_model=schemas.AIProviderResponse)
async def update_provider(
    provider_id: int,
    provider: schemas.AIProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    db_provider = await crud.update_ai_provider(db, provider_id, provider)
    if not db_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return db_provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    deleted = await crud.delete_ai_provider(db, provider_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return None

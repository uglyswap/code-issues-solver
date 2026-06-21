from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# Bug Patterns endpoints
@router.get("/patterns", response_model=list[schemas.BugPatternResponse])
async def list_bug_patterns(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """List all bug patterns, optionally filtered by category."""
    skip = (page - 1) * per_page
    patterns = await crud.get_bug_patterns(db, skip=skip, limit=per_page, category=category)
    return patterns


@router.get("/patterns/{pattern_id}", response_model=schemas.BugPatternResponse)
async def get_bug_pattern(
    pattern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Get a specific bug pattern by ID."""
    pattern = await crud.get_bug_pattern(db, pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern


@router.post("/patterns", response_model=schemas.BugPatternResponse, status_code=status.HTTP_201_CREATED)
async def create_bug_pattern(
    pattern: schemas.BugPatternCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Create a new bug pattern."""
    # Check if pattern_id already exists
    existing = await crud.get_bug_pattern_by_pattern_id(db, pattern.pattern_id)
    if existing:
        raise HTTPException(status_code=400, detail="Pattern ID already exists")
    
    return await crud.create_bug_pattern(db, pattern)


@router.put("/patterns/{pattern_id}", response_model=schemas.BugPatternResponse)
async def update_bug_pattern(
    pattern_id: int,
    pattern: schemas.BugPatternUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Update an existing bug pattern."""
    updated = await crud.update_bug_pattern(db, pattern_id, pattern)
    if not updated:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return updated


@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug_pattern(
    pattern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Delete a bug pattern."""
    deleted = await crud.delete_bug_pattern(db, pattern_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return None


# Successful Patches endpoints
@router.get("/patches", response_model=list[schemas.SuccessfulPatchResponse])
async def list_successful_patches(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """List all successful patches, optionally filtered by category."""
    skip = (page - 1) * per_page
    patches = await crud.get_successful_patches(db, skip=skip, limit=per_page, category=category)
    return patches


@router.get("/patches/{patch_id}", response_model=schemas.SuccessfulPatchResponse)
async def get_successful_patch(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Get a specific successful patch by ID."""
    patch = await crud.get_successful_patch(db, patch_id)
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    return patch


@router.post("/patches", response_model=schemas.SuccessfulPatchResponse, status_code=status.HTTP_201_CREATED)
async def create_successful_patch(
    patch: schemas.SuccessfulPatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Record a successful patch."""
    return await crud.create_successful_patch(db, patch)


@router.delete("/patches/{patch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_successful_patch(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Delete a successful patch."""
    deleted = await crud.delete_successful_patch(db, patch_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patch not found")
    return None


# Search endpoints for few-shot learning
@router.get("/search/patterns/{category}", response_model=list[schemas.BugPatternResponse])
async def search_patterns_by_category(
    category: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Search for bug patterns by category, ordered by success rate and occurrences."""
    patterns = await crud.get_bug_patterns(db, skip=0, limit=limit, category=category)
    # Sort by success_rate (desc) then occurrences (desc)
    patterns = sorted(patterns, key=lambda p: (p.success_rate, p.occurrences), reverse=True)
    return patterns


@router.get("/search/patches/{category}", response_model=list[schemas.SuccessfulPatchResponse])
async def search_patches_by_category(
    category: str,
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Search for successful patches by category, ordered by creation date (most recent first)."""
    patches = await crud.get_successful_patches(db, skip=0, limit=limit, category=category)
    return patches
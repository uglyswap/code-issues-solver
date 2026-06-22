from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user
from backend.app.security import decrypt_value

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


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Test the connection to an AI provider by making a minimal chat completion call."""
    db_provider = await crud.get_ai_provider(db, provider_id)
    if not db_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    
    try:
        # Decrypt API key
        api_key = decrypt_value(db_provider.api_key_encrypted)
        
        # Get the default model from the provider's models config
        models_config = db_provider.models or {}
        model = models_config.get("default", "gpt-3.5-turbo")
        
        # Test connection by making a minimal chat completion call
        test_url = f"{db_provider.base_url.rstrip('/')}/chat/completions"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                test_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                },
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Connection successful with model {model}",
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "message": f"API returned status {response.status_code}",
                    "status_code": response.status_code,
                    "detail": response.text[:500]
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "status_code": None
        }
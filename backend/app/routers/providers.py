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


# Fallback model lists for providers that don't support /models endpoint
FALLBACK_MODELS = {
    "anthropic": [
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        "claude-3-7-sonnet-20250219",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ],
    "alibaba": [
        "qwen3.7-plus",
        "qwen3.6-plus",
        "qwen-plus",
        "qwen-turbo",
        "qwen-max",
        "qwen2.5-coder-32b-instruct",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o3",
        "o3-mini",
        "o4-mini",
    ],
    "openrouter": [
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3.7-sonnet",
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "openai/o3",
        "openai/o4-mini",
        "google/gemini-2.5-pro",
        "google/gemini-2.5-flash",
        "meta-llama/llama-4-maverick",
        "meta-llama/llama-4-scout",
        "deepseek/deepseek-r1",
        "deepseek/deepseek-chat-v3",
    ],
}


def detect_provider_type(base_url: str) -> str:
    """Detect provider type from base URL."""
    url_lower = base_url.lower()
    if "anthropic" in url_lower:
        return "anthropic"
    elif "dashscope" in url_lower or "alibaba" in url_lower or "aliyun" in url_lower:
        return "alibaba"
    elif "openai" in url_lower:
        return "openai"
    elif "openrouter" in url_lower:
        return "openrouter"
    return "unknown"


@router.get("/{provider_id}/models")
async def list_provider_models(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Fetch available models from an AI provider."""
    db_provider = await crud.get_ai_provider(db, provider_id)
    if not db_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    
    try:
        api_key = decrypt_value(db_provider.api_key_encrypted)
        base_url = db_provider.base_url.rstrip("/")
        provider_type = detect_provider_type(base_url)
        
        # Try to fetch models from the API
        models_url = f"{base_url}/models"
        
    # Validate URL to prevent SSRF
    from backend.app.utils import validate_url_no_ssrf
    try:
        validate_url_no_ssrf(provider.base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                models_url,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                # OpenAI-compatible format: {"data": [{"id": "model-name", ...}]}
                if "data" in data:
                    model_ids = sorted([m["id"] for m in data["data"] if isinstance(m, dict) and "id" in m])
                    return {
                        "success": True,
                        "models": model_ids,
                        "source": "api",
                    }
                # Some providers return a list directly
                elif isinstance(data, list):
                    model_ids = sorted([m["id"] if isinstance(m, dict) else str(m) for m in data])
                    return {
                        "success": True,
                        "models": model_ids,
                        "source": "api",
                    }
        
        # Fallback to hardcoded lists
        if provider_type in FALLBACK_MODELS:
            return {
                "success": True,
                "models": FALLBACK_MODELS[provider_type],
                "source": "fallback",
            }
        
        return {
            "success": False,
            "message": f"Could not fetch models from API (status {response.status_code}) and no fallback for provider type '{provider_type}'",
            "models": [],
            "source": "none",
        }
    except Exception as e:
        # Try fallback on error
        provider_type = detect_provider_type(db_provider.base_url)
        if provider_type in FALLBACK_MODELS:
            return {
                "success": True,
                "models": FALLBACK_MODELS[provider_type],
                "source": "fallback",
                "warning": f"API call failed ({str(e)}), using fallback list",
            }
        return {
            "success": False,
            "message": f"Failed to fetch models: {str(e)}",
            "models": [],
            "source": "none",
        }
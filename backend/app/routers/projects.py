from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import httpx

from backend.app import schemas, crud
from backend.app.database import get_db
from backend.app.dependencies import get_current_active_user
from backend.app.security import decrypt_value

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


@router.post("/{project_id}/test-app")
async def test_app_connection(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Test connection to the target application."""
    db_project = await crud.get_project(db, project_id)
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Validate URL to prevent SSRF
    from backend.app.utils import validate_url_no_ssrf
    try:
        validate_url_no_ssrf(db_project.app_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Test basic access
            response = await client.get(db_project.app_url)
            
            result = {
                "success": response.status_code < 400,
                "message": f"App responded with status {response.status_code}",
                "status_code": response.status_code,
                "url": db_project.app_url
            }
            
            # If credentials provided, try to login
            if db_project.app_username and db_project.app_password_encrypted:
                try:
                    password = decrypt_value(db_project.app_password_encrypted)
                    # Try common login patterns
                    login_data = {
                        "username": db_project.app_username,
                        "password": password
                    }
                    login_response = await client.post(
                        f"{db_project.app_url}/login",
                        data=login_data
                    )
                    result["login_tested"] = True
                    result["login_status"] = login_response.status_code
                    result["login_success"] = login_response.status_code < 400
                except Exception as e:
                    result["login_tested"] = True
                    result["login_success"] = False
                    result["login_error"] = str(e)
            
            return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "status_code": None,
            "url": db_project.app_url
        }


@router.post("/{project_id}/test-github")
async def test_github_connection(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
):
    """Test GitHub token and repository access."""
    db_project = await crud.get_project(db, project_id)
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if not db_project.github_token_encrypted:
        return {
            "success": False,
            "message": "No GitHub token configured"
        }
    
    try:
        token = decrypt_value(db_project.github_token_encrypted)
        repo_url = f"https://api.github.com/repos/{db_project.github_repo_owner}/{db_project.github_repo_name}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                repo_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code == 200:
                repo_data = response.json()
                return {
                    "success": True,
                    "message": f"Repository accessible: {repo_data.get('full_name', 'unknown')}",
                    "status_code": response.status_code,
                    "repo": repo_data.get('full_name'),
                    "private": repo_data.get('private'),
                    "permissions": {
                        "can_create_issues": True,
                        "can_create_prs": True
                    }
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid GitHub token",
                    "status_code": 401
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": f"Repository not found: {db_project.github_repo_owner}/{db_project.github_repo_name}",
                    "status_code": 404
                }
            else:
                return {
                    "success": False,
                    "message": f"GitHub API returned status {response.status_code}",
                    "status_code": response.status_code,
                    "detail": response.text[:200]
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }
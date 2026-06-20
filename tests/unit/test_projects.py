import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={"username": "projuser", "email": "p@test.com", "password": "pass1234"})
    r = await client.post("/api/auth/login", json={"username": "projuser", "password": "pass1234"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_project(client, auth_headers):
    r = await client.post("/api/projects", json={
        "name": "Test Project",
        "app_url": "http://localhost:3000",
        "github_repo_owner": "test",
        "github_repo_name": "repo",
    }, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Project"
    assert data["stats"]["total_executions"] == 0


@pytest.mark.asyncio
async def test_list_projects(client, auth_headers):
    r = await client.get("/api/projects", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_update_project(client, auth_headers):
    r = await client.post("/api/projects", json={
        "name": "Update Project",
        "app_url": "http://localhost:3000",
        "github_repo_owner": "test",
        "github_repo_name": "repo",
    }, headers=auth_headers)
    pid = r.json()["id"]
    r = await client.put(f"/api/projects/{pid}", json={"name": "Updated Name"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_project(client, auth_headers):
    r = await client.post("/api/projects", json={
        "name": "Delete Project",
        "app_url": "http://localhost:3000",
        "github_repo_owner": "test",
        "github_repo_name": "repo",
    }, headers=auth_headers)
    pid = r.json()["id"]
    r = await client.delete(f"/api/projects/{pid}", headers=auth_headers)
    assert r.status_code == 204
    r = await client.get(f"/api/projects/{pid}", headers=auth_headers)
    assert r.status_code == 404

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    r = await client.post("/api/auth/register", json={"username": "testuser", "email": "test@test.com", "password": "testpass123"})
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "testuser"

    # Login
    r = await client.post("/api/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    # Me
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    r = await client.post("/api/auth/login", json={"username": "testuser", "password": "wrong"})
    assert r.status_code == 401

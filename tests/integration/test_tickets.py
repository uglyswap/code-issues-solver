import pytest
from backend.app.database import async_session
from backend.app import crud, schemas


@pytest.mark.asyncio
async def test_ticket_lifecycle(client, auth_headers):
    # Create project
    r = await client.post("/api/projects", json={
        "name": "Ticket Project",
        "app_url": "http://localhost:3000",
        "github_repo_owner": "test",
        "github_repo_name": "repo",
    }, headers=auth_headers)
    project_id = r.json()["id"]

    # Create execution
    r = await client.post(f"/api/projects/{project_id}/executions", json={"trigger_type": "manual"}, headers=auth_headers)
    execution_id = r.json()["id"]

    # Insert ticket directly for test
    async with async_session() as db:
        ticket = await crud.create_ticket(db, schemas.TicketCreate(
            execution_id=execution_id,
            title="Test Bug",
            description="A test bug",
            severity="high",
            category="js_error",
        ))
        ticket_id = ticket.id
        await db.commit()

    # Get ticket
    r = await client.get(f"/api/tickets/{ticket_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Test Bug"

    # Update ticket
    r = await client.put(f"/api/tickets/{ticket_id}", json={"status": "ignored", "ignored_reason": "false positive"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"

    # List tickets
    r = await client.get(f"/api/projects/{project_id}/tickets", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_full_execution_flow(client, auth_headers):
    # Create project
    r = await client.post("/api/projects", json={
        "name": "Flow Project",
        "app_url": "http://localhost:3000",
        "github_repo_owner": "test",
        "github_repo_name": "repo",
    }, headers=auth_headers)
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Start execution
    with patch("workers.app.tasks.run_execution.send") as mock_send:
        r = await client.post(f"/api/projects/{project_id}/executions", json={"trigger_type": "manual"}, headers=auth_headers)
        assert r.status_code == 201
        mock_send.assert_called_once()

    # List executions
    r = await client.get(f"/api/projects/{project_id}/executions", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

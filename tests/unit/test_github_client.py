import pytest
from unittest.mock import AsyncMock
from integrations.app.github_client import GitHubClient


@pytest.mark.asyncio
async def test_create_issue(mocker):
    client = GitHubClient("fake-token")
    mock_response = AsyncMock()
    mock_response.json.return_value = {"number": 42, "html_url": "https://github.com/test/repo/issues/42"}
    mock_response.raise_for_status = AsyncMock()
    mocker.patch.object(client.client, "post", return_value=mock_response)

    result = await client.create_issue("test", "repo", "Bug", "Description", ["bug"])
    assert result["number"] == 42
    await client.close()

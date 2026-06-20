import pytest
from unittest.mock import AsyncMock
from agents.app.base_agent import BaseAgent
from integrations.app.llm_client import BaseLLMClient


@pytest.mark.asyncio
async def test_base_agent_run():
    mock_client = AsyncMock(spec=BaseLLMClient)
    mock_client.chat_completion.return_value = '{"resolved": true, "explanation": "OK"}'
    agent = BaseAgent(
        name="verifier",
        prompt_template="Verify this bug: {{ bug_description }}",
        client=mock_client,
        model="gpt-4",
    )
    result = await agent.run_json({"bug_description": "Test bug"})
    assert result["resolved"] is True
    mock_client.chat_completion.assert_awaited_once()

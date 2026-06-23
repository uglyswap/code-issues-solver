from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app import models
from backend.app.security import decrypt_value
from integrations.app.llm_client import OpenRouterClient, AlibabaCloudClient, BaseLLMClient
from agents.app.base_agent import BaseAgent
from agents.app.prompts import TESTER_PROMPT, TRIAGE_PROMPT, CODER_PROMPT, REVIEWER_PROMPT, VERIFIER_PROMPT


DEFAULT_PROMPTS = {
    "tester": TESTER_PROMPT,
    "triage": TRIAGE_PROMPT,
    "coder": CODER_PROMPT,
    "reviewer": REVIEWER_PROMPT,
    "verifier": VERIFIER_PROMPT,
}


def create_llm_client(provider: models.AIProvider) -> BaseLLMClient:
    api_key = decrypt_value(provider.api_key_encrypted)
    if "openrouter" in provider.name.lower():
        return OpenRouterClient(api_key)
    # Fallback: si le nom ne matche pas mais que base_url pointe vers OpenRouter,
    # utiliser quand meme OpenRouterClient (routage plus robuste, retrocompatible).
    base_url = provider.base_url or ""
    if "openrouter" in base_url.lower():
        return OpenRouterClient(api_key)
    return AlibabaCloudClient(api_key, provider.base_url)


async def get_agent_by_name(db: AsyncSession, name: str) -> BaseAgent:
    result = await db.execute(
        select(models.Agent)
        .where(models.Agent.name == name, models.Agent.enabled == True)
    )
    agent_row = result.scalar_one_or_none()
    if not agent_row:
        raise ValueError(f"Agent {name} not found or disabled")

    provider = await db.get(models.AIProvider, agent_row.provider_id)
    if not provider or not provider.enabled:
        raise ValueError(f"Provider for agent {name} not found or disabled")

    client = create_llm_client(provider)
    prompt = agent_row.system_prompt_template or DEFAULT_PROMPTS.get(name, "")
    return BaseAgent(
        name=agent_row.name,
        prompt_template=prompt,
        client=client,
        model=agent_row.model,
        temperature=agent_row.temperature,
        max_tokens=agent_row.max_tokens,
    )

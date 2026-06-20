import asyncio
from backend.app.database import async_session
from backend.app import crud, schemas


async def seed():
    async with async_session() as db:
        # Create default admin user if not exists
        user = await crud.get_user_by_username(db, "admin")
        if not user:
            await crud.create_user(db, schemas.UserCreate(username="admin", email="admin@local", password="admin1234"))
            print("Created admin user (admin / admin1234)")

        # Create default providers if none exist
        providers = await crud.get_ai_providers(db, limit=1)
        if not providers[0]:
            await crud.create_ai_provider(
                db,
                schemas.AIProviderCreate(
                    name="openrouter",
                    api_key="placeholder",
                    base_url="https://openrouter.ai/api/v1",
                    models={"default": "openai/gpt-4o-mini"},
                    priority=1,
                )
            )
            print("Created default OpenRouter provider")

        # Create default agents if none exist
        agents = await crud.get_agents(db, limit=1)
        if not agents[0]:
            provider = await crud.get_ai_provider(db, 1)
            provider_id = provider.id if provider else None
            default_agents = [
                ("tester", "Analyze logs and detect bugs"),
                ("triage", "Classify and prioritize bugs"),
                ("coder", "Generate patches for bugs"),
                ("reviewer", "Review patches for correctness"),
                ("verifier", "Verify fixes after deployment"),
            ]
            for name, desc in default_agents:
                await crud.create_agent(
                    db,
                    schemas.AgentCreate(
                        name=name,
                        description=desc,
                        system_prompt_template="You are the {{ name }} agent. {{ description }}",
                        provider_id=provider_id,
                        model="openai/gpt-4o-mini",
                    )
                )
            print("Created default agents")


if __name__ == "__main__":
    asyncio.run(seed())

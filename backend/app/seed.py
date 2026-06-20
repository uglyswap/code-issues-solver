import asyncio
import os
from pathlib import Path
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
                ),
            )
            print("Created default OpenRouter provider")

        # Create default agents if none exist
        agents = await crud.get_agents(db, limit=1)
        if not agents[0]:
            provider = await crud.get_ai_provider(db, 1)
            provider_id = provider.id if provider else None

            # Load prompts from files
            prompts_dir = Path(__file__).parent.parent.parent / "agents" / "prompts"
            agent_configs = [
                {
                    "name": "tester",
                    "description": "Analyse les résultats de tests Playwright et détecte tous les bugs (erreurs JS, problèmes réseau, UI cassée, fonctionnalités broken)",
                    "prompt_file": "tester.md",
                    "model": "anthropic/claude-3.5-sonnet",
                    "temperature": 0.3,
                    "max_tokens": 8000,
                },
                {
                    "name": "triage",
                    "description": "Classifie les bugs par sévérité et catégorie, priorise pour le développement, identifie les causes racines et suggère des approches de résolution",
                    "prompt_file": "triage.md",
                    "model": "anthropic/claude-3.5-sonnet",
                    "temperature": 0.2,
                    "max_tokens": 6000,
                },
                {
                    "name": "coder",
                    "description": "Génère des patches de correction pour les bugs identifiés, avec tests unitaires et d'intégration pour éviter les régressions",
                    "prompt_file": "coder.md",
                    "model": "anthropic/claude-3.5-sonnet",
                    "temperature": 0.1,
                    "max_tokens": 12000,
                },
                {
                    "name": "reviewer",
                    "description": "Relit les patches générés, vérifie la qualité du code, détecte les problèmes de sécurité/performance, et valide avant merge",
                    "prompt_file": "reviewer.md",
                    "model": "anthropic/claude-3.5-sonnet",
                    "temperature": 0.2,
                    "max_tokens": 6000,
                },
                {
                    "name": "verifier",
                    "description": "Vérifie post-déploiement que les bugs sont réellement résolus, teste les cas limites, détecte les régressions, et valide la fermeture des tickets",
                    "prompt_file": "verifier.md",
                    "model": "anthropic/claude-3.5-sonnet",
                    "temperature": 0.1,
                    "max_tokens": 8000,
                },
            ]

            for config in agent_configs:
                prompt_path = prompts_dir / config["prompt_file"]
                if prompt_path.exists():
                    prompt_content = prompt_path.read_text()
                else:
                    print(f"Warning: prompt file {prompt_path} not found, using fallback")
                    prompt_content = f"You are the {config['name']} agent. {config['description']}"

                await crud.create_agent(
                    db,
                    schemas.AgentCreate(
                        name=config["name"],
                        description=config["description"],
                        system_prompt_template=prompt_content,
                        provider_id=provider_id,
                        model=config["model"],
                        temperature=config["temperature"],
                        max_tokens=config["max_tokens"],
                    ),
                )
            print("Created 5 default agents with specialized prompts (tester, triage, coder, reviewer, verifier)")


if __name__ == "__main__":
    asyncio.run(seed())

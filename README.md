# Code Issues Solver

Système autonome de test, détection et correction automatique de bugs pour applications web.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   React UI  │────▶│  FastAPI     │────▶│ PostgreSQL  │
│   (Vite)    │     │  Backend     │     │   Redis     │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Dramatiq   │
                    │   Workers    │
                    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │Playwright│ │ GitHub   │ │ AI Agents│
        │ Browser  │ │   API    │ │(OpenRouter)│
        └──────────┘ └──────────┘ └──────────┘
```

## Composants

- **Backend FastAPI** : API REST, authentification JWT, gestion des projets/secrets/providers/agents
- **Workers Dramatiq** : Tâches asynchrones (test, détection, patch, PR, déploiement, vérification)
- **UI React 18** : Interface TypeScript + Tailwind, 6 pages principales
- **PostgreSQL 16** : 8 tables (projects, secrets, ai_providers, agents, executions, test_sessions, tickets, audit_logs)
- **Redis** : Broker de messages pour Dramatiq
- **Nginx** : Reverse proxy

## Workflow

1. Configuration d'un projet (URL app, credentials, token GitHub)
2. Lancement d'une exécution (manuelle, cron, webhook)
3. Playwright teste l'application (screenshots, logs console, réseau)
4. Détection automatique des bugs (erreurs JS, éléments cassés, 404/500)
5. Création de GitHub Issues pour chaque bug détecté
6. Génération de patches via agents IA
7. Ouverture de Pull Requests GitHub
8. Déploiement après merge
9. Vérification post-déploiement
10. Fermeture automatique des issues résolues

## Déploiement

### Prérequis

- Docker & Docker Compose
- Token GitHub avec permissions `repo`
- Clé API OpenRouter ou Alibaba Cloud

### Installation

```bash
git clone https://github.com/uglyswap/code-issues-solver.git
cd code-issues-solver

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# Lancer les services
docker-compose up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Nginx | 3500 | Reverse proxy (UI + API) |
| UI React | 3501 | Interface directe |
| Backend | 8000 | API FastAPI (interne) |
| PostgreSQL | 5432 | Base de données |
| Redis | 6379 | Broker de messages |

### Accès

- **Interface** : http://localhost:3500
- **API** : http://localhost:3500/api
- **Swagger** : http://localhost:3500/api/docs

## Configuration

### Providers IA

Configurez plusieurs providers avec fallback automatique :

```json
{
  "name": "OpenRouter",
  "type": "openrouter",
  "api_key": "sk-or-...",
  "model": "anthropic/claude-3.5-sonnet",
  "priority": 1
}
```

### Agents

5 agents spécialisés :

| Agent | Rôle |
|-------|------|
| `tester` | Test de l'application web |
| `triage` | Classification des bugs |
| `coder` | Génération de patches |
| `reviewer` | Relecture des PRs |
| `verifier` | Vérification post-déploiement |

### Secrets

Stockage chiffré AES-256-GCM pour :
- Tokens GitHub
- Clés API
- Credentials de test

## API

### Authentification

```bash
# Login
curl -X POST http://localhost:3500/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# Réponse
{"access_token":"eyJ...","token_type":"bearer"}
```

### Projets

```bash
# Lister
curl http://localhost:3500/api/projects \
  -H "Authorization: Bearer *** Créer
curl -X POST http://localhost:3500/api/projects \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mon App",
    "url": "https://monapp.com",
    "github_repo": "user/repo",
    "test_username": "test@example.com",
    "test_password": "secret"
  }'
```

### Exécutions

```bash
# Lancer un test
curl -X POST http://localhost:3500/api/projects/1/executions \
  -H "Authorization: Bearer *** \
  -d '{"trigger_type":"manual"}'
```

## GitHub Actions

3 workflows configurés :

- **CI** : Tests, lint, build à chaque push/PR
- **Deploy** : Déploiement automatique après merge sur `main`
- **Auto-repair** : Notification après déploiement pour relancer un cycle de test

## Développement

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd ui
npm install
npm run dev

# Workers
dramatiq app.workers
```

## Tests

```bash
# Tests unitaires
pytest tests/

# Couverture
pytest --cov=backend --cov-report=html

# Lint
ruff check backend/
black --check backend/
```

## Sécurité

- Authentification JWT avec expiration
- Secrets chiffrés AES-256-GCM
- CORS configurable
- Audit logs complets
- Scan secrets avec detect-secrets

## Monitoring

- Logs structurés JSON
- Health checks sur tous les services
- Métriques Prometheus (à venir)
- Alertes sur échecs

## Licence

MIT

# Deployment

## Docker Compose (Recommended)

```bash
cp .env.example .env
# Edit .env with your secrets
make docker-up
```

Services:
- `postgres` — PostgreSQL 16
- `redis` — Redis 7
- `backend` — FastAPI on port 3500
- `workers` — Dramatiq workers (2 replicas)
- `ui` — React SPA on port 3501
- `nginx` — Reverse proxy on port 80

## VPS Deployment

The included GitHub Actions workflow (`deploy.yml`) deploys to `207.180.243.246` via SSH.

Requirements on the VPS:
- Docker and Docker Compose installed
- SSH key configured in repository secrets

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `ENCRYPTION_KEY` | Fernet key for secret encryption |
| `JWT_SECRET` | JWT signing secret |
| `CORS_ORIGINS` | Allowed frontend origins |

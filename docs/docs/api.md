# API Documentation

The API is automatically documented via FastAPI's OpenAPI/Swagger UI.

## Access

- Swagger UI: `http://localhost:3500/docs`
- OpenAPI JSON: `http://localhost:3500/openapi.json`

## Authentication

Most endpoints require a JWT token in the `Authorization: Bearer *** header.

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/auth/me` | Current user |
| POST | `/api/projects` | Create project |
| GET | `/api/projects` | List projects |
| POST | `/api/projects/{id}/executions` | Start execution |
| GET | `/api/executions/{id}/logs` | SSE log stream |
| GET | `/api/projects/{id}/tickets` | List tickets |
| POST | `/api/tickets/{id}/retry` | Retry ticket fix |
| POST | `/api/webhooks/github` | GitHub webhooks |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| GET | `/metrics` | Prometheus metrics |

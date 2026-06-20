# Architecture

## Overview

Code Issues Solver is a monorepo with the following services:

- **Backend**: FastAPI application providing REST API and SSE streams.
- **Workers**: Dramatiq workers processing async tasks.
- **Browser**: Playwright automation for crawling and testing.
- **Agents**: LLM-powered agents for bug detection, triage, coding, review, and verification.
- **Integrations**: GitHub API, OpenRouter, and Alibaba Cloud clients.
- **UI**: React 18 SPA with Tailwind CSS.

## Data Flow

1. User creates a Project via UI.
2. User triggers an Execution.
3. Backend creates an Execution record and enqueues `run_execution`.
4. Worker runs Playwright tests, collects logs and screenshots.
5. Worker detects bugs using AI agent or rule-based fallback.
6. For each bug, a Ticket is created and a GitHub Issue is opened.
7. AI Coder agent generates a patch.
8. Worker creates a branch, commits the patch, and opens a PR.
9. On PR merge, deployment is triggered.
10. Verifier agent re-tests to confirm the fix and closes the issue.

## Database Schema

See `backend/app/models.py` for the full SQLAlchemy models.

Key tables:
- `projects` — target applications
- `executions` — test runs
- `test_sessions` — Playwright session data
- `tickets` — detected bugs
- `ai_providers` and `agents` — LLM configuration

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.limiter import limiter
from backend.app.routers import auth, projects, providers, agents, executions, tickets, webhooks, health, secrets


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Code Issues Solver",
    description="Autonomous web app testing, detection, and fixing system",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(providers.router)
app.include_router(agents.router)
app.include_router(executions.router)
app.include_router(tickets.router)
app.include_router(webhooks.router)
app.include_router(secrets.router)
app.include_router(health.router)

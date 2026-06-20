from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)

    audit_logs = relationship("AuditLog", back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    app_url = Column(String(500), nullable=False)
    app_username = Column(String(255))
    app_password_encrypted = Column(Text)
    github_repo_owner = Column(String(255), nullable=False)
    github_repo_name = Column(String(255), nullable=False)
    github_token_encrypted = Column(Text)
    deploy_webhook_url = Column(String(500))
    schedule_cron = Column(String(100))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    executions = relationship("Execution", back_populates="project", cascade="all, delete-orphan")
    secrets = relationship("Secret", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project")


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    base_url = Column(String(500), nullable=False)
    models = Column(JSON, nullable=False, default=dict)
    priority = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)

    agents = relationship("Agent", back_populates="provider")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    system_prompt_template = Column(Text, nullable=False)
    provider_id = Column(Integer, ForeignKey("ai_providers.id"))
    model = Column(String(255), nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=4000)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)

    provider = relationship("AIProvider", back_populates="agents")


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    trigger_type = Column(String(50), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    total_bugs_found = Column(Integer, default=0)
    total_bugs_fixed = Column(Integer, default=0)
    logs = Column(JSON, default=list)
    error_message = Column(Text)
    created_at = Column(DateTime, default=now_utc)

    project = relationship("Project", back_populates="executions")
    test_sessions = relationship("TestSession", back_populates="execution", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="execution", cascade="all, delete-orphan")


class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True)
    browser_context_id = Column(String(255))
    screenshots = Column(JSON, default=list)
    console_logs = Column(JSON, default=list)
    network_requests = Column(JSON, default=list)
    pages_visited = Column(JSON, default=list)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=now_utc)

    execution = relationship("Execution", back_populates="test_sessions")
    tickets = relationship("Ticket", back_populates="test_session")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id", ondelete="CASCADE"))
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    screenshot_path = Column(String(500))
    console_logs = Column(JSON)
    network_logs = Column(JSON)
    status = Column(String(50), nullable=False, default="open")
    github_issue_number = Column(Integer)
    github_issue_url = Column(String(500))
    github_pr_number = Column(Integer)
    github_pr_url = Column(String(500))
    patch_content = Column(Text)
    patch_commit_sha = Column(String(100))
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    ignored_reason = Column(Text)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    execution = relationship("Execution", back_populates="tickets")
    test_session = relationship("TestSession", back_populates="tickets")


class Secret(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    value_encrypted = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=now_utc)

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_secret_name"),)

    project = relationship("Project", back_populates="secrets")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=now_utc)

    user = relationship("User", back_populates="audit_logs")
    project = relationship("Project", back_populates="audit_logs")

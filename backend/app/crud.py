from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from backend.app import models, schemas
from backend.app.security import hash_password, verify_password, encrypt_value, decrypt_value


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password),
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[models.User]:
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_projects(db: AsyncSession, skip: int = 0, limit: int = 20, enabled: Optional[bool] = None):
    query = select(models.Project)
    if enabled is not None:
        query = query.where(models.Project.enabled == enabled)
    query = query.order_by(desc(models.Project.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(func.count(models.Project.id))
    if enabled is not None:
        count_query = count_query.where(models.Project.enabled == enabled)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    return items, total


async def get_project(db: AsyncSession, project_id: int) -> Optional[models.Project]:
    result = await db.execute(select(models.Project).where(models.Project.id == project_id))
    return result.scalar_one_or_none()


async def create_project(db: AsyncSession, project: schemas.ProjectCreate) -> models.Project:
    db_project = models.Project(
        name=project.name,
        description=project.description,
        app_url=project.app_url,
        app_username=project.app_username,
        app_password_encrypted=encrypt_value(project.app_password) if project.app_password else None,
        github_repo_owner=project.github_repo_owner,
        github_repo_name=project.github_repo_name,
        github_token_encrypted=encrypt_value(project.github_token) if project.github_token else None,
        deploy_webhook_url=project.deploy_webhook_url,
        schedule_cron=project.schedule_cron,
        enabled=project.enabled,
    )
    db.add(db_project)
    await db.flush()
    await db.refresh(db_project)
    return db_project


async def update_project(db: AsyncSession, project_id: int, project: schemas.ProjectUpdate) -> Optional[models.Project]:
    db_project = await get_project(db, project_id)
    if not db_project:
        return None
    data = project.model_dump(exclude_unset=True)
    if "app_password" in data:
        val = data.pop("app_password")
        if val:
            db_project.app_password_encrypted = encrypt_value(val)
    if "github_token" in data:
        val = data.pop("github_token")
        if val:
            db_project.github_token_encrypted = encrypt_value(val)
    for key, value in data.items():
        setattr(db_project, key, value)
    await db.flush()
    await db.refresh(db_project)
    return db_project


async def delete_project(db: AsyncSession, project_id: int) -> bool:
    db_project = await get_project(db, project_id)
    if not db_project:
        return False
    await db.delete(db_project)
    await db.flush()
    return True


async def get_project_stats(db: AsyncSession, project_id: int) -> schemas.ProjectStats:
    exec_count = await db.execute(
        select(func.count(models.Execution.id)).where(models.Execution.project_id == project_id)
    )
    total_executions = exec_count.scalar() or 0

    open_tickets = await db.execute(
        select(func.count(models.Ticket.id)).where(
            models.Ticket.execution_id.in_(
                select(models.Execution.id).where(models.Execution.project_id == project_id)
            ),
            models.Ticket.status == "open",
        )
    )
    open_tickets_count = open_tickets.scalar() or 0

    total_tickets = await db.execute(
        select(func.count(models.Ticket.id)).where(
            models.Ticket.execution_id.in_(
                select(models.Execution.id).where(models.Execution.project_id == project_id)
            )
        )
    )
    total_tickets_count = total_tickets.scalar() or 0

    last_exec = await db.execute(
        select(models.Execution.started_at)
        .where(models.Execution.project_id == project_id)
        .order_by(desc(models.Execution.started_at))
        .limit(1)
    )
    last_execution_at = last_exec.scalar_one_or_none()

    return schemas.ProjectStats(
        total_executions=total_executions,
        open_tickets=open_tickets_count,
        total_tickets=total_tickets_count,
        last_execution_at=last_execution_at,
    )


async def get_ai_providers(db: AsyncSession, skip: int = 0, limit: int = 20):
    result = await db.execute(
        select(models.AIProvider).order_by(models.AIProvider.priority).offset(skip).limit(limit)
    )
    items = result.scalars().all()
    # Convert SQLAlchemy objects to dicts to avoid serialization issues
    items_dict = [
        {
            "id": p.id,
            "name": p.name,
            "base_url": p.base_url,
            "models": p.models,
            "priority": p.priority,
            "enabled": p.enabled,
            "created_at": p.created_at,
        }
        for p in items
    ]
    total_result = await db.execute(select(func.count(models.AIProvider.id)))
    total = total_result.scalar()
    return items_dict, total


async def get_ai_provider(db: AsyncSession, provider_id: int) -> Optional[models.AIProvider]:
    result = await db.execute(select(models.AIProvider).where(models.AIProvider.id == provider_id))
    return result.scalar_one_or_none()


async def create_ai_provider(db: AsyncSession, provider: schemas.AIProviderCreate) -> models.AIProvider:
    db_provider = models.AIProvider(
        name=provider.name,
        api_key_encrypted=encrypt_value(provider.api_key),
        base_url=provider.base_url,
        models=provider.models,
        priority=provider.priority,
        enabled=provider.enabled,
    )
    db.add(db_provider)
    await db.flush()
    await db.refresh(db_provider)
    return db_provider


async def update_ai_provider(db: AsyncSession, provider_id: int, provider: schemas.AIProviderUpdate) -> Optional[models.AIProvider]:
    db_provider = await get_ai_provider(db, provider_id)
    if not db_provider:
        return None
    data = provider.model_dump(exclude_unset=True)
    if "api_key" in data:
        val = data.pop("api_key")
        if val:
            db_provider.api_key_encrypted = encrypt_value(val)
    for key, value in data.items():
        setattr(db_provider, key, value)
    await db.flush()
    await db.refresh(db_provider)
    return db_provider


async def delete_ai_provider(db: AsyncSession, provider_id: int) -> bool:
    db_provider = await get_ai_provider(db, provider_id)
    if not db_provider:
        return False
    await db.delete(db_provider)
    await db.flush()
    return True


async def get_agents(db: AsyncSession, skip: int = 0, limit: int = 20):
    result = await db.execute(select(models.Agent).offset(skip).limit(limit))
    items = result.scalars().all()
    total_result = await db.execute(select(func.count(models.Agent.id)))
    total = total_result.scalar()
    return items, total


async def get_agent(db: AsyncSession, agent_id: int) -> Optional[models.Agent]:
    result = await db.execute(select(models.Agent).where(models.Agent.id == agent_id))
    return result.scalar_one_or_none()


async def get_agent_by_name(db: AsyncSession, name: str) -> Optional[models.Agent]:
    result = await db.execute(select(models.Agent).where(models.Agent.name == name))
    return result.scalar_one_or_none()


async def create_agent(db: AsyncSession, agent: schemas.AgentCreate) -> models.Agent:
    db_agent = models.Agent(
        name=agent.name,
        description=agent.description,
        system_prompt_template=agent.system_prompt_template,
        provider_id=agent.provider_id,
        model=agent.model,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        enabled=agent.enabled,
    )
    db.add(db_agent)
    await db.flush()
    await db.refresh(db_agent)
    return db_agent


async def update_agent(db: AsyncSession, agent_id: int, agent: schemas.AgentUpdate) -> Optional[models.Agent]:
    db_agent = await get_agent(db, agent_id)
    if not db_agent:
        return None
    data = agent.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_agent, key, value)
    await db.flush()
    await db.refresh(db_agent)
    return db_agent


async def delete_agent(db: AsyncSession, agent_id: int) -> bool:
    db_agent = await get_agent(db, agent_id)
    if not db_agent:
        return False
    await db.delete(db_agent)
    await db.flush()
    return True


async def get_executions(db: AsyncSession, project_id: int, skip: int = 0, limit: int = 20, status: Optional[str] = None):
    query = select(models.Execution).where(models.Execution.project_id == project_id)
    if status:
        query = query.where(models.Execution.status == status)
    query = query.order_by(desc(models.Execution.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Convert SQLAlchemy objects to dicts to avoid serialization issues
    items_dict = [
        {
            "id": e.id,
            "project_id": e.project_id,
            "status": e.status,
            "trigger_type": e.trigger_type,
            "started_at": e.started_at,
            "completed_at": e.completed_at,
            "total_bugs_found": e.total_bugs_found,
            "total_bugs_fixed": e.total_bugs_fixed,
            "logs": e.logs,
            "error_message": e.error_message,
            "created_at": e.created_at,
        }
        for e in items
    ]

    count_query = select(func.count(models.Execution.id)).where(models.Execution.project_id == project_id)
    if status:
        count_query = count_query.where(models.Execution.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    return items_dict, total


async def get_execution(db: AsyncSession, execution_id: int) -> Optional[models.Execution]:
    result = await db.execute(select(models.Execution).where(models.Execution.id == execution_id))
    return result.scalar_one_or_none()


async def create_execution(db: AsyncSession, project_id: int, trigger_type: str) -> models.Execution:
    db_execution = models.Execution(
        project_id=project_id,
        status="pending",
        trigger_type=trigger_type,
    )
    db.add(db_execution)
    await db.flush()
    await db.refresh(db_execution)
    return db_execution


async def update_execution_status(db: AsyncSession, execution_id: int, status: str, error_message: Optional[str] = None):
    db_execution = await get_execution(db, execution_id)
    if not db_execution:
        return None
    db_execution.status = status
    if error_message is not None:
        db_execution.error_message = error_message
    if status == "running":
        from datetime import datetime, timezone
        db_execution.started_at = datetime.now(timezone.utc)
    if status in ("completed", "failed", "stopped"):
        from datetime import datetime, timezone
        db_execution.completed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(db_execution)
    return db_execution


async def delete_execution(db: AsyncSession, execution_id: int) -> bool:
    """Delete an execution by ID."""
    db_execution = await get_execution(db, execution_id)
    if not db_execution:
        return False
    await db.delete(db_execution)
    await db.flush()
    return True


async def append_execution_log(db: AsyncSession, execution_id: int, log: dict):
    db_execution = await get_execution(db, execution_id)
    if not db_execution:
        return None
    logs = list(db_execution.logs or [])
    logs.append(log)
    db_execution.logs = logs
    await db.flush()
    await db.refresh(db_execution)
    return db_execution


async def get_tickets(db: AsyncSession, project_id: int, skip: int = 0, limit: int = 20,
                      status: Optional[str] = None, severity: Optional[str] = None, category: Optional[str] = None):
    query = select(models.Ticket).where(
        models.Ticket.execution_id.in_(
            select(models.Execution.id).where(models.Execution.project_id == project_id)
        )
    )
    if status:
        query = query.where(models.Ticket.status == status)
    if severity:
        query = query.where(models.Ticket.severity == severity)
    if category:
        query = query.where(models.Ticket.category == category)
    query = query.order_by(desc(models.Ticket.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(func.count(models.Ticket.id)).where(
        models.Ticket.execution_id.in_(
            select(models.Execution.id).where(models.Execution.project_id == project_id)
        )
    )
    if status:
        count_query = count_query.where(models.Ticket.status == status)
    if severity:
        count_query = count_query.where(models.Ticket.severity == severity)
    if category:
        count_query = count_query.where(models.Ticket.category == category)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    return items, total


async def get_ticket(db: AsyncSession, ticket_id: int) -> Optional[models.Ticket]:
    result = await db.execute(select(models.Ticket).where(models.Ticket.id == ticket_id))
    return result.scalar_one_or_none()


async def create_ticket(db: AsyncSession, ticket: schemas.TicketCreate) -> models.Ticket:
    db_ticket = models.Ticket(
        execution_id=ticket.execution_id,
        test_session_id=ticket.test_session_id,
        title=ticket.title,
        description=ticket.description,
        severity=ticket.severity,
        category=ticket.category,
        screenshot_path=ticket.screenshot_path,
        console_logs=ticket.console_logs,
        network_logs=ticket.network_logs,
    )
    db.add(db_ticket)
    await db.flush()
    await db.refresh(db_ticket)
    return db_ticket


async def update_ticket(db: AsyncSession, ticket_id: int, ticket: schemas.TicketUpdate) -> Optional[models.Ticket]:
    db_ticket = await get_ticket(db, ticket_id)
    if not db_ticket:
        return None
    data = ticket.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_ticket, key, value)
    await db.flush()
    await db.refresh(db_ticket)
    return db_ticket


async def get_secrets(db: AsyncSession, project_id: int):
    result = await db.execute(
        select(models.Secret).where(models.Secret.project_id == project_id).order_by(models.Secret.name)
    )
    return result.scalars().all()


async def get_secret(db: AsyncSession, secret_id: int) -> Optional[models.Secret]:
    result = await db.execute(select(models.Secret).where(models.Secret.id == secret_id))
    return result.scalar_one_or_none()


async def create_secret(db: AsyncSession, project_id: int, secret: schemas.SecretCreate) -> models.Secret:
    db_secret = models.Secret(
        project_id=project_id,
        name=secret.name,
        value_encrypted=encrypt_value(secret.value),
        description=secret.description,
    )
    db.add(db_secret)
    await db.flush()
    await db.refresh(db_secret)
    return db_secret


async def update_secret(db: AsyncSession, secret_id: int, secret: schemas.SecretUpdate) -> Optional[models.Secret]:
    db_secret = await get_secret(db, secret_id)
    if not db_secret:
        return None
    data = secret.model_dump(exclude_unset=True)
    if "value" in data:
        val = data.pop("value")
        if val:
            db_secret.value_encrypted = encrypt_value(val)
    if "name" in data:
        db_secret.name = data["name"]
    if "description" in data:
        db_secret.description = data["description"]
    await db.flush()
    await db.refresh(db_secret)
    return db_secret


async def delete_secret(db: AsyncSession, secret_id: int) -> bool:
    db_secret = await get_secret(db, secret_id)
    if not db_secret:
        return False
    await db.delete(db_secret)
    await db.flush()
    return True


async def create_audit_log(db: AsyncSession, log: schemas.AuditLogBase, user_id: Optional[int] = None):
    db_log = models.AuditLog(
        user_id=user_id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        details=log.details,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
    )
    db.add(db_log)
    await db.flush()
    await db.refresh(db_log)
    return db_log


# Bug Pattern CRUD
async def get_bug_patterns(db: AsyncSession, skip: int = 0, limit: int = 20, category: Optional[str] = None):
    query = select(models.BugPattern)
    if category:
        query = query.where(models.BugPattern.category == category)
    query = query.order_by(desc(models.BugPattern.occurrences)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_bug_pattern(db: AsyncSession, pattern_id: int) -> Optional[models.BugPattern]:
    result = await db.execute(select(models.BugPattern).where(models.BugPattern.id == pattern_id))
    return result.scalar_one_or_none()


async def get_bug_pattern_by_pattern_id(db: AsyncSession, pattern_id: str) -> Optional[models.BugPattern]:
    result = await db.execute(select(models.BugPattern).where(models.BugPattern.pattern_id == pattern_id))
    return result.scalar_one_or_none()


async def create_bug_pattern(db: AsyncSession, pattern: schemas.BugPatternCreate) -> models.BugPattern:
    db_pattern = models.BugPattern(
        pattern_id=pattern.pattern_id,
        category=pattern.category,
        description=pattern.description,
        root_cause=pattern.root_cause,
        solution_template=pattern.solution_template,
        example_files=pattern.example_files or [],
        success_rate=pattern.success_rate,
        occurrences=pattern.occurrences,
    )
    db.add(db_pattern)
    await db.flush()
    await db.refresh(db_pattern)
    return db_pattern


async def update_bug_pattern(db: AsyncSession, pattern_id: int, pattern: schemas.BugPatternUpdate) -> Optional[models.BugPattern]:
    db_pattern = await get_bug_pattern(db, pattern_id)
    if not db_pattern:
        return None
    data = pattern.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_pattern, key, value)
    await db.flush()
    await db.refresh(db_pattern)
    return db_pattern


async def delete_bug_pattern(db: AsyncSession, pattern_id: int) -> bool:
    db_pattern = await get_bug_pattern(db, pattern_id)
    if not db_pattern:
        return False
    await db.delete(db_pattern)
    await db.flush()
    return True


# Successful Patch CRUD
async def get_successful_patches(db: AsyncSession, skip: int = 0, limit: int = 20, category: Optional[str] = None):
    query = select(models.SuccessfulPatch)
    if category:
        query = query.where(models.SuccessfulPatch.category == category)
    query = query.order_by(desc(models.SuccessfulPatch.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_successful_patch(db: AsyncSession, patch_id: int) -> Optional[models.SuccessfulPatch]:
    result = await db.execute(select(models.SuccessfulPatch).where(models.SuccessfulPatch.id == patch_id))
    return result.scalar_one_or_none()


async def create_successful_patch(db: AsyncSession, patch: schemas.SuccessfulPatchCreate) -> models.SuccessfulPatch:
    db_patch = models.SuccessfulPatch(
        ticket_id=patch.ticket_id,
        category=patch.category,
        title=patch.title,
        description=patch.description,
        patch_content=patch.patch_content,
        files_changed=patch.files_changed or [],
        success_rate=patch.success_rate,
    )
    db.add(db_patch)
    await db.flush()
    await db.refresh(db_patch)
    return db_patch


async def delete_successful_patch(db: AsyncSession, patch_id: int) -> bool:
    db_patch = await get_successful_patch(db, patch_id)
    if not db_patch:
        return False
    await db.delete(db_patch)
    await db.flush()
    return True
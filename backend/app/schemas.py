from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    email: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    app_url: str = Field(..., max_length=500)
    app_username: Optional[str] = Field(None, max_length=255)
    app_password: Optional[str] = None
    github_repo_owner: str = Field(..., max_length=255)
    github_repo_name: str = Field(..., max_length=255)
    github_token: Optional[str] = None
    deploy_webhook_url: Optional[str] = Field(None, max_length=500)
    schedule_cron: Optional[str] = Field(None, max_length=100)
    enabled: bool = True


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    app_url: Optional[str] = Field(None, max_length=500)
    app_username: Optional[str] = Field(None, max_length=255)
    app_password: Optional[str] = None
    github_repo_owner: Optional[str] = Field(None, max_length=255)
    github_repo_name: Optional[str] = Field(None, max_length=255)
    github_token: Optional[str] = None
    deploy_webhook_url: Optional[str] = Field(None, max_length=500)
    schedule_cron: Optional[str] = Field(None, max_length=100)
    enabled: Optional[bool] = None


class ProjectStats(BaseModel):
    total_executions: int
    open_tickets: int
    total_tickets: int
    last_execution_at: Optional[datetime]


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    app_url: str
    app_username: Optional[str]
    github_repo_owner: str
    github_repo_name: str
    deploy_webhook_url: Optional[str]
    schedule_cron: Optional[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    stats: Optional[ProjectStats] = None


class AIProviderBase(BaseModel):
    name: str = Field(..., max_length=255)
    api_key: str
    base_url: str = Field(..., max_length=500)
    models: Dict[str, Any]
    priority: int = 1
    enabled: bool = True


class AIProviderCreate(AIProviderBase):
    pass


class AIProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = None
    base_url: Optional[str] = Field(None, max_length=500)
    models: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class AIProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    base_url: str
    models: Dict[str, Any]
    priority: int
    enabled: bool
    created_at: datetime


class AgentBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    system_prompt_template: str
    provider_id: Optional[int] = None
    model: str = Field(..., max_length=255)
    temperature: float = 0.7
    max_tokens: int = 4000
    enabled: bool = True


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    system_prompt_template: Optional[str] = None
    provider_id: Optional[int] = None
    model: Optional[str] = Field(None, max_length=255)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    enabled: Optional[bool] = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    system_prompt_template: str
    provider_id: Optional[int]
    model: str
    temperature: float
    max_tokens: int
    enabled: bool
    created_at: datetime


class ExecutionBase(BaseModel):
    project_id: int
    status: str = "pending"
    trigger_type: str


class ExecutionCreate(BaseModel):
    trigger_type: str = "manual"


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    status: str
    trigger_type: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_bugs_found: int
    total_bugs_fixed: int
    logs: List[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime


class ExecutionDetailResponse(ExecutionResponse):
    test_sessions: List["TestSessionResponse"] = []
    tickets: List["TicketResponse"] = []


class TestSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    execution_id: int
    browser_context_id: Optional[str]
    screenshots: List[Dict[str, Any]]
    console_logs: List[Dict[str, Any]]
    network_requests: List[Dict[str, Any]]
    pages_visited: List[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    created_at: datetime


class TicketBase(BaseModel):
    execution_id: int
    test_session_id: Optional[int] = None
    title: str = Field(..., max_length=500)
    description: str
    severity: str
    category: str
    screenshot_path: Optional[str] = None
    console_logs: Optional[List[Dict[str, Any]]] = None
    network_logs: Optional[List[Dict[str, Any]]] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    ignored_reason: Optional[str] = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    execution_id: int
    test_session_id: Optional[int]
    title: str
    description: str
    severity: str
    category: str
    screenshot_path: Optional[str]
    console_logs: Optional[List[Dict[str, Any]]]
    network_logs: Optional[List[Dict[str, Any]]]
    status: str
    github_issue_number: Optional[int]
    github_issue_url: Optional[str]
    github_pr_number: Optional[int]
    github_pr_url: Optional[str]
    patch_content: Optional[str]
    patch_commit_sha: Optional[str]
    retry_count: int
    max_retries: int
    ignored_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class SecretBase(BaseModel):
    name: str = Field(..., max_length=255)
    value: str
    description: Optional[str] = None


class SecretCreate(SecretBase):
    pass


class SecretUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    value: Optional[str] = None
    description: Optional[str] = None


class SecretResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    description: Optional[str]
    created_at: datetime


class AuditLogBase(BaseModel):
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogResponse(AuditLogBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int]
    created_at: datetime


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None


class WebhookPayload(BaseModel):
    event: str
    action: Optional[str] = None
    pull_request: Optional[Dict[str, Any]] = None
    deployment_status: Optional[Dict[str, Any]] = None
    repository: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    checks: Dict[str, str]


# Bug Pattern schemas
class BugPatternBase(BaseModel):
    pattern_id: str
    category: str
    description: str
    root_cause: str
    solution_template: str
    example_files: Optional[List[str]] = None
    success_rate: float = 0.0
    occurrences: int = 0


class BugPatternCreate(BugPatternBase):
    pass


class BugPatternUpdate(BaseModel):
    description: Optional[str] = None
    root_cause: Optional[str] = None
    solution_template: Optional[str] = None
    example_files: Optional[List[str]] = None
    success_rate: Optional[float] = None
    occurrences: Optional[int] = None


class BugPatternResponse(BugPatternBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


# Successful Patch schemas
class SuccessfulPatchBase(BaseModel):
    category: str
    title: str
    description: str
    patch_content: str
    files_changed: Optional[List[str]] = None
    success_rate: float = 1.0


class SuccessfulPatchCreate(SuccessfulPatchBase):
    ticket_id: int


class SuccessfulPatchResponse(SuccessfulPatchBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticket_id: int
    created_at: datetime
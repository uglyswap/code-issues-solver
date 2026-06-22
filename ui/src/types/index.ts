export interface User { id: number; username: string; email: string; is_active: boolean; created_at: string }
export interface Project { id: number; name: string; description?: string; app_url: string; app_username?: string; github_repo_owner: string; github_repo_name: string; deploy_webhook_url?: string; schedule_cron?: string; enabled: boolean; created_at: string; updated_at: string; stats?: ProjectStats }
export interface ProjectStats { total_executions: number; open_tickets: number; total_tickets: number; last_execution_at?: string }
export interface AIProvider { id: number; name: string; base_url: string; models: Record<string, unknown>; priority: number; enabled: boolean; created_at: string }
export interface Agent { id: number; name: string; description?: string; system_prompt_template: string; provider_id?: number; model: string; temperature: number; max_tokens: number; enabled: boolean; created_at: string }
export interface Execution { id: number; project_id: number; status: string; trigger_type: string; started_at?: string; completed_at?: string; total_bugs_found: number; total_bugs_fixed: number; logs: LogEntry[]; error_message?: string; created_at: string; test_sessions?: TestSession[]; tickets?: Ticket[] }
export interface TestSession { id: number; execution_id: number; browser_context_id?: string; screenshots: Array<{ url: string; path: string; timestamp: string }>; console_logs: Array<{ level: string; message: string; url: string; timestamp: string }>; network_requests: Array<Record<string, unknown>>; pages_visited: string[]; started_at?: string; completed_at?: string; duration_seconds?: number; created_at: string }
export interface Ticket { id: number; execution_id: number; test_session_id?: number; title: string; description: string; severity: string; category: string; screenshot_path?: string; console_logs?: unknown[]; network_logs?: unknown[]; status: string; github_issue_number?: number; github_issue_url?: string; github_pr_number?: number; github_pr_url?: string; patch_content?: string; patch_commit_sha?: string; retry_count: number; max_retries: number; ignored_reason?: string; resolution_summary?: ResolutionSummary; attempts_log?: AttemptLog[]; resolution_time_seconds?: number; files_changed?: string[]; test_results_before?: Record<string, unknown>; test_results_after?: Record<string, unknown>; screenshots_before?: string[]; screenshots_after?: string[]; created_at: string; updated_at: string }
export interface ResolutionSummary { problem: string; solution: string; root_cause: string; files_affected: string[] }
export interface AttemptLog { attempt: number; timestamp: string; status: string; feedback?: string; patch?: string; message?: string }
export interface Secret { id: number; project_id: number; name: string; description?: string; created_at: string }
export interface LogEntry { timestamp: string; level: string; message: string; context?: Record<string, unknown> }
export interface PaginatedResponse<T> { items: T[]; total: number; page: number; per_page: number }

// Dashboard types
export interface DashboardStats {
  total_tickets: number; resolved_tickets: number; open_tickets: number;
  in_progress_tickets: number; failed_tickets: number; resolution_rate: number;
  avg_resolution_time_seconds?: number; tickets_by_severity: Record<string, number>;
  tickets_by_category: Record<string, number>; tickets_by_status: Record<string, number>;
}
export interface TimelineEvent {
  timestamp: string; event_type: string; ticket_id: number;
  ticket_title: string; severity: string; message: string; execution_id?: number;
}
export interface DashboardData { stats: DashboardStats; recent_activity: TimelineEvent[]; active_sessions: Session[] }

// Session types
export interface Session {
  id: number; project_id: number; status: string; trigger_type: string;
  started_at?: string; completed_at?: string;
  total_tickets_found: number; total_tickets_resolved: number; total_tickets_failed: number;
  current_ticket_id?: number; logs: SessionLog[];
  auto_close_github_issues: boolean; max_concurrent_tickets: number;
  created_at: string; updated_at: string;
}
export interface SessionLog { timestamp: string; level: string; message: string; ticket_id?: number }

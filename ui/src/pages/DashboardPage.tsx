import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardApi, sessionsApi, projectsApi } from '../services/api'
import type { DashboardData, Session, Project } from '../types'
import {
  Loader2, Play, Pause, Square, RefreshCw,
  CheckCircle, XCircle, Clock, AlertTriangle,
  TrendingUp, Activity, Zap,
} from 'lucide-react'
import toast from 'react-hot-toast'

function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    open: 'bg-blue-100 text-blue-700',
    patching: 'bg-yellow-100 text-yellow-700',
    reviewing: 'bg-purple-100 text-purple-700',
    creating_pr: 'bg-indigo-100 text-indigo-700',
    deploying: 'bg-cyan-100 text-cyan-700',
    verifying: 'bg-teal-100 text-teal-700',
    verified: 'bg-green-100 text-green-700',
    deployed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    running: 'bg-green-100 text-green-700',
    paused: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-blue-100 text-blue-700',
    stopped: 'bg-slate-100 text-slate-700',
    pending: 'bg-slate-100 text-slate-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-slate-100 text-slate-700'}`}>
      {status}
    </span>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-slate-100 text-slate-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[severity] || 'bg-slate-100 text-slate-700'}`}>
      {severity}
    </span>
  )
}

function StatCard({ title, value, subtitle, icon: Icon, color }: {
  title: string; value: string | number; subtitle?: string; icon: any; color: string
}) {
  return (
    <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-slate-500">{title}</span>
        <div className={`p-2 rounded-lg ${color}`}><Icon className="w-4 h-4" /></div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  )
}

function ProgressBar({ resolved, total, failed }: { resolved: number; total: number; failed: number }) {
  const resolvedPct = total > 0 ? (resolved / total) * 100 : 0
  const failedPct = total > 0 ? (failed / total) * 100 : 0
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>{resolved}/{total} resolved</span>
        <span>{Math.round(resolvedPct)}%</span>
      </div>
      <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
        <div className="h-full flex">
          <div className="bg-green-500 transition-all duration-500" style={{ width: `${resolvedPct}%` }} />
          <div className="bg-red-500 transition-all duration-500" style={{ width: `${failedPct}%` }} />
        </div>
      </div>
      {failed > 0 && <p className="text-xs text-red-500 mt-1">{failed} failed</p>}
    </div>
  )
}

function SessionCard({ session, projects }: { session: Session; projects: Project[] }) {
  const queryClient = useQueryClient()
  const project = projects.find(p => p.id === session.project_id)
  
  const pauseMutation = useMutation({
    mutationFn: () => sessionsApi.pause(session.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Session paused') },
  })
  const resumeMutation = useMutation({
    mutationFn: () => sessionsApi.resume(session.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Session resumed') },
  })
  const stopMutation = useMutation({
    mutationFn: () => sessionsApi.stop(session.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Session stopped') },
  })

  return (
    <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Link to={`/sessions/${session.id}`} className="font-semibold text-primary-700 hover:underline">
            Session #{session.id}
          </Link>
          <StatusBadge status={session.status} />
        </div>
        <div className="flex gap-1">
          {session.status === 'running' && (
            <button onClick={() => pauseMutation.mutate()} className="p-1.5 rounded-lg hover:bg-yellow-50 text-yellow-600" title="Pause">
              <Pause className="w-4 h-4" />
            </button>
          )}
          {session.status === 'paused' && (
            <button onClick={() => resumeMutation.mutate()} className="p-1.5 rounded-lg hover:bg-green-50 text-green-600" title="Resume">
              <Play className="w-4 h-4" />
            </button>
          )}
          {['running', 'paused'].includes(session.status) && (
            <button onClick={() => stopMutation.mutate()} className="p-1.5 rounded-lg hover:bg-red-50 text-red-600" title="Stop">
              <Square className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      <p className="text-sm text-slate-600 mb-3">Project: {project?.name || 'Unknown'}</p>
      <ProgressBar
        resolved={session.total_tickets_resolved}
        total={session.total_tickets_found}
        failed={session.total_tickets_failed}
      />
      {session.logs.length > 0 && (
        <div className="mt-3 max-h-32 overflow-y-auto">
          <p className="text-xs text-slate-500 mb-1">Latest activity:</p>
          {session.logs.slice(-3).reverse().map((log, i) => (
            <p key={i} className={`text-xs ${log.level === 'error' ? 'text-red-600' : log.level === 'warning' ? 'text-yellow-600' : 'text-slate-600'}`}>
              {log.message}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const [projectId, setProjectId] = useState<number | undefined>()
  const queryClient = useQueryClient()
  
  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(r => r.data),
  })
  
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['dashboard', projectId],
    queryFn: () => dashboardApi.get(projectId).then(r => r.data as DashboardData),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  })
  
  const projects: Project[] = projectsData?.items || []
  
  const startSessionMutation = useMutation({
    mutationFn: (projectId: number) => sessionsApi.create({ project_id: projectId }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Session started!') },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Error starting session'),
  })

  if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin w-8 h-8 text-primary-600" /></div>
  if (!data) return <div className="text-center text-slate-500">Failed to load dashboard</div>

  const { stats, recent_activity, active_sessions } = data

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-slate-500">Real-time overview of bug detection and resolution</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={projectId || ''}
            onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">All Projects</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button onClick={() => refetch()} className="p-2 rounded-lg border hover:bg-slate-50" title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Total Tickets" value={stats.total_tickets} icon={Activity} color="bg-blue-50 text-blue-600" />
        <StatCard title="Resolved" value={stats.resolved_tickets} subtitle={`${stats.resolution_rate.toFixed(1)}% resolution rate`} icon={CheckCircle} color="bg-green-50 text-green-600" />
        <StatCard title="In Progress" value={stats.in_progress_tickets} icon={Clock} color="bg-yellow-50 text-yellow-600" />
        <StatCard title="Failed" value={stats.failed_tickets} icon={XCircle} color="bg-red-50 text-red-600" />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Resolution Time */}
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold">Avg Resolution Time</h3>
          </div>
          <p className="text-3xl font-bold">{formatDuration(stats.avg_resolution_time_seconds)}</p>
        </div>

        {/* By Severity */}
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <h3 className="font-semibold mb-3">By Severity</h3>
          <div className="space-y-2">
            {Object.entries(stats.tickets_by_severity).map(([sev, count]) => (
              <div key={sev} className="flex items-center justify-between">
                <SeverityBadge severity={sev} />
                <span className="font-medium">{count}</span>
              </div>
            ))}
            {Object.keys(stats.tickets_by_severity).length === 0 && <p className="text-sm text-slate-400">No data</p>}
          </div>
        </div>

        {/* By Category */}
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <h3 className="font-semibold mb-3">Top Categories</h3>
          <div className="space-y-2">
            {Object.entries(stats.tickets_by_category).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([cat, count]) => (
              <div key={cat} className="flex items-center justify-between">
                <span className="text-sm text-slate-600 truncate">{cat}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
            {Object.keys(stats.tickets_by_category).length === 0 && <p className="text-sm text-slate-400">No data</p>}
          </div>
        </div>
      </div>

      {/* Active Sessions */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            Active Sessions
          </h2>
          {projects.length > 0 && (
            <select
              className="border rounded-lg px-3 py-1.5 text-sm"
              onChange={(e) => { if (e.target.value) { startSessionMutation.mutate(Number(e.target.value)); e.target.value = '' } }}
              defaultValue=""
            >
              <option value="">+ Start session...</option>
              {projects.filter(p => p.enabled).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          )}
        </div>
        {active_sessions.length === 0 ? (
          <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200 text-center">
            <p className="text-slate-500 mb-3">No active sessions</p>
            <p className="text-sm text-slate-400">Start a session to continuously resolve all bugs in a project</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {active_sessions.map(s => <SessionCard key={s.id} session={s} projects={projects} />)}
          </div>
        )}
      </div>

      {/* Timeline */}
      <div>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary-600" />
          Recent Activity
        </h2>
        {recent_activity.length === 0 ? (
          <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200 text-center">
            <p className="text-slate-500">No recent activity</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 divide-y">
            {recent_activity.slice(0, 20).map((event, i) => (
              <div key={i} className="p-4 flex items-start gap-3 hover:bg-slate-50">
                <div className={`mt-1 p-1.5 rounded-full ${
                  event.event_type === 'verified' || event.event_type === 'deployed' ? 'bg-green-100' :
                  event.event_type === 'failed' ? 'bg-red-100' :
                  event.event_type === 'open' ? 'bg-blue-100' : 'bg-yellow-100'
                }`}>
                  {event.event_type === 'verified' || event.event_type === 'deployed' ? <CheckCircle className="w-3 h-3 text-green-600" /> :
                   event.event_type === 'failed' ? <XCircle className="w-3 h-3 text-red-600" /> :
                   event.event_type === 'open' ? <AlertTriangle className="w-3 h-3 text-blue-600" /> :
                   <Clock className="w-3 h-3 text-yellow-600" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Link to={`/tickets/${event.ticket_id}`} className="text-sm font-medium text-primary-700 hover:underline truncate">
                      {event.ticket_title}
                    </Link>
                    <SeverityBadge severity={event.severity} />
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{event.message}</p>
                </div>
                <span className="text-xs text-slate-400 whitespace-nowrap">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { sessionsApi, projectsApi } from '../services/api'
import type { Session, Project } from '../types'
import { Loader2, Play, Pause, Square, Plus, Zap, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'

function formatDuration(start?: string, end?: string): string {
  if (!start) return '-'
  const s = new Date(start).getTime()
  const e = end ? new Date(end).getTime() : Date.now()
  const secs = Math.floor((e - s) / 1000)
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${secs % 60}s`
  return `${secs}s`
}

export default function SessionsPage() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [selectedProject, setSelectedProject] = useState<number | ''>('')
  const [statusFilter, setStatusFilter] = useState('')

  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(r => r.data),
  })

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['sessions', statusFilter],
    queryFn: () => sessionsApi.list(undefined, statusFilter || undefined).then(r => r.data as Session[]),
    refetchInterval: 5000,
  })

  const projects: Project[] = projectsData?.items || []
  const sessions: Session[] = sessionsData || []

  const createMutation = useMutation({
    mutationFn: (projectId: number) => sessionsApi.create({ project_id: projectId }),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      setShowCreate(false)
      setSelectedProject('')
      toast.success('Session started!')
      window.location.href = `/sessions/${data.id}`
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Error starting session'),
  })

  const pauseMutation = useMutation({
    mutationFn: (id: number) => sessionsApi.pause(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['sessions'] }); toast.success('Session paused') },
  })
  const resumeMutation = useMutation({
    mutationFn: (id: number) => sessionsApi.resume(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['sessions'] }); toast.success('Session resumed') },
  })
  const stopMutation = useMutation({
    mutationFn: (id: number) => sessionsApi.stop(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['sessions'] }); toast.success('Session stopped') },
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-500" />
            Sessions
          </h1>
          <p className="text-sm text-slate-500">Continuous correction sessions - runs until all bugs are resolved</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="running">Running</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
            <option value="stopped">Stopped</option>
          </select>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
          >
            <Plus className="w-4 h-4" /> New Session
          </button>
        </div>
      </div>

      {/* Create Session Form */}
      {showCreate && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="font-semibold text-lg mb-4">Start New Session</h2>
          <p className="text-sm text-slate-600 mb-4">
            A continuous session will scan the project for bugs and fix them one by one until all issues are resolved.
            The session runs indefinitely with no time limit.
          </p>
          <div className="flex items-center gap-3">
            <select
              className="border rounded-lg px-3 py-2 flex-1"
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">Select a project...</option>
              {projects.filter(p => p.enabled).map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button
              onClick={() => selectedProject && createMutation.mutate(Number(selectedProject))}
              disabled={!selectedProject || createMutation.isPending}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              <Play className="w-4 h-4" /> Start
            </button>
          </div>
        </div>
      )}

      {/* Sessions List */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 className="animate-spin w-8 h-8 text-primary-600" /></div>
      ) : sessions.length === 0 ? (
        <div className="bg-white p-12 rounded-xl shadow-sm border border-slate-200 text-center">
          <Zap className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">No sessions yet</p>
          <p className="text-sm text-slate-400 mt-1">Start a session to continuously resolve all bugs in a project</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map(session => {
            const project = projects.find(p => p.id === session.project_id)
            const progressPct = session.total_tickets_found > 0
              ? Math.round((session.total_tickets_resolved / session.total_tickets_found) * 100) : 0

            return (
              <div key={session.id} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Link to={`/sessions/${session.id}`} className="font-semibold text-primary-700 hover:underline text-lg">
                        Session #{session.id}
                      </Link>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        session.status === 'running' ? 'bg-green-100 text-green-700' :
                        session.status === 'paused' ? 'bg-yellow-100 text-yellow-700' :
                        session.status === 'completed' ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {session.status === 'running' && <span className="inline-block w-1.5 h-1.5 bg-green-500 rounded-full mr-1 animate-pulse" />}
                        {session.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500 mt-0.5">
                      {project?.name || 'Unknown project'} \u2022 {session.trigger_type} \u2022 Duration: {formatDuration(session.started_at, session.completed_at)}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    {session.status === 'running' && (
                      <button onClick={() => pauseMutation.mutate(session.id)} className="p-1.5 rounded-lg hover:bg-yellow-50 text-yellow-600" title="Pause">
                        <Pause className="w-4 h-4" />
                      </button>
                    )}
                    {session.status === 'paused' && (
                      <button onClick={() => resumeMutation.mutate(session.id)} className="p-1.5 rounded-lg hover:bg-green-50 text-green-600" title="Resume">
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    {['running', 'paused', 'pending'].includes(session.status) && (
                      <button onClick={() => stopMutation.mutate(session.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-600" title="Stop">
                        <Square className="w-4 h-4" />
                      </button>
                    )}
                    <Link to={`/sessions/${session.id}`} className="p-1.5 rounded-lg hover:bg-slate-50 text-slate-600" title="View details">
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                  </div>
                </div>

                {/* Progress */}
                <div className="mb-2">
                  <div className="flex justify-between text-xs text-slate-500 mb-1">
                    <span>{session.total_tickets_resolved} resolved / {session.total_tickets_found} found</span>
                    <span>{progressPct}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
                    <div className="h-full flex">
                      <div className="bg-green-500 transition-all duration-500" style={{ width: `${progressPct}%` }} />
                      <div className="bg-red-500 transition-all duration-500" style={{ width: `${session.total_tickets_found > 0 ? (session.total_tickets_failed / session.total_tickets_found) * 100 : 0}%` }} />
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="flex gap-4 text-xs text-slate-500">
                  <span>Found: <strong>{session.total_tickets_found}</strong></span>
                  <span>Resolved: <strong className="text-green-600">{session.total_tickets_resolved}</strong></span>
                  <span>Failed: <strong className="text-red-600">{session.total_tickets_failed}</strong></span>
                  {session.current_ticket_id && (
                    <span>Current: <Link to={`/tickets/${session.current_ticket_id}`} className="text-primary-600 hover:underline">#{session.current_ticket_id}</Link></span>
                  )}
                </div>

                {/* Latest logs */}
                {session.logs && session.logs.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <p className="text-xs text-slate-400 mb-1">Latest:</p>
                    {session.logs.slice(-2).reverse().map((log, i) => (
                      <p key={i} className={`text-xs ${log.level === 'error' ? 'text-red-600' : 'text-slate-600'}`}>
                        {log.message}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

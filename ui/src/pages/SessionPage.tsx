import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sessionsApi, projectsApi } from '../services/api'
import type { Session, SessionLog, Project } from '../types'
import {
  Loader2, Play, Pause, Square, ArrowLeft,
  CheckCircle, XCircle, Clock, AlertTriangle,
  Activity,
} from 'lucide-react'
import toast from 'react-hot-toast'

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function LogLine({ log }: { log: SessionLog }) {
  const icon = log.level === 'error' ? <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" /> :
    log.level === 'warning' ? <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 shrink-0" /> :
    log.message.includes('\u2705') || log.message.includes('resolved') ? <CheckCircle className="w-3.5 h-3.5 text-green-500 shrink-0" /> :
    <Clock className="w-3.5 h-3.5 text-blue-500 shrink-0" />

  return (
    <div className="flex items-start gap-2 py-1.5 px-2 hover:bg-slate-50 rounded font-mono text-xs">
      <span className="text-slate-400 shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
      {icon}
      <span className={`${log.level === 'error' ? 'text-red-700' : log.level === 'warning' ? 'text-yellow-700' : 'text-slate-700'}`}>
        {log.message}
      </span>
      {log.ticket_id && (
        <Link to={`/tickets/${log.ticket_id}`} className="text-primary-600 hover:underline shrink-0">
          #{log.ticket_id}
        </Link>
      )}
    </div>
  )
}

export default function SessionPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = Number(id)
  const queryClient = useQueryClient()
  const logEndRef = useRef<HTMLDivElement>(null)
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [elapsed, setElapsed] = useState(0)

  const { data: sessionData, isLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId).then(r => r.data as Session),
    refetchInterval: 3000,
  })

  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list().then(r => r.data),
  })

  const project = projectsData?.items?.find((p: Project) => p.id === sessionData?.project_id)
  const session = sessionData as Session | undefined

  // WebSocket for real-time logs
  useEffect(() => {
    if (!sessionId) return
    const wsUrl = sessionsApi.wsUrl(sessionId)
    const websocket = new WebSocket(wsUrl)
    
    websocket.onopen = () => {
      console.log('WebSocket connected')
      const interval = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) websocket.send('ping')
      }, 30000)
      websocket.addEventListener('close', () => clearInterval(interval))
    }
    
    websocket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'log') {
          queryClient.invalidateQueries({ queryKey: ['session', sessionId] })
        }
      } catch {}
    }
    
    websocket.onerror = () => {}
    websocket.onclose = () => {}
    
    setWs(websocket)
    return () => { websocket.close() }
  }, [sessionId, queryClient])

  // Elapsed time counter
  useEffect(() => {
    if (!session?.started_at) return
    const interval = setInterval(() => {
      const start = new Date(session.started_at!).getTime()
      const end = session.completed_at ? new Date(session.completed_at).getTime() : Date.now()
      setElapsed(Math.floor((end - start) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [session?.started_at, session?.completed_at])

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [session?.logs?.length])

  const pauseMutation = useMutation({
    mutationFn: () => sessionsApi.pause(sessionId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['session', sessionId] }); toast.success('Session paused') },
  })
  const resumeMutation = useMutation({
    mutationFn: () => sessionsApi.resume(sessionId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['session', sessionId] }); toast.success('Session resumed') },
  })
  const stopMutation = useMutation({
    mutationFn: () => sessionsApi.stop(sessionId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['session', sessionId] }); toast.success('Session stopped') },
  })

  if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin w-8 h-8 text-primary-600" /></div>
  if (!session) return <div className="text-center text-slate-500">Session not found</div>

  const progressPct = session.total_tickets_found > 0
    ? Math.round((session.total_tickets_resolved / session.total_tickets_found) * 100) : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link to="/dashboard" className="p-2 rounded-lg border hover:bg-slate-50">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Session #{session.id}</h1>
            <p className="text-sm text-slate-500">
              {project?.name || 'Unknown project'} \u2022 {session.trigger_type}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            session.status === 'running' ? 'bg-green-100 text-green-700' :
            session.status === 'paused' ? 'bg-yellow-100 text-yellow-700' :
            session.status === 'completed' ? 'bg-blue-100 text-blue-700' :
            session.status === 'stopped' ? 'bg-slate-100 text-slate-700' :
            'bg-slate-100 text-slate-700'
          }`}>
            {session.status === 'running' && <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse" />}
            {session.status}
          </span>
          {session.status === 'running' && (
            <button onClick={() => pauseMutation.mutate()} className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-yellow-300 text-yellow-700 hover:bg-yellow-50 text-sm">
              <Pause className="w-4 h-4" /> Pause
            </button>
          )}
          {session.status === 'paused' && (
            <button onClick={() => resumeMutation.mutate()} className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-green-300 text-green-700 hover:bg-green-50 text-sm">
              <Play className="w-4 h-4" /> Resume
            </button>
          )}
          {['running', 'paused', 'pending'].includes(session.status) && (
            <button onClick={() => stopMutation.mutate()} className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-red-300 text-red-700 hover:bg-red-50 text-sm">
              <Square className="w-4 h-4" /> Stop
            </button>
          )}
        </div>
      </div>

      {/* Progress Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <p className="text-xs text-slate-500">Duration</p>
          <p className="text-xl font-bold font-mono">{formatDuration(elapsed)}</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <p className="text-xs text-slate-500">Found</p>
          <p className="text-xl font-bold">{session.total_tickets_found}</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <p className="text-xs text-slate-500">Resolved</p>
          <p className="text-xl font-bold text-green-600">{session.total_tickets_resolved}</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <p className="text-xs text-slate-500">Failed</p>
          <p className="text-xl font-bold text-red-600">{session.total_tickets_failed}</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <p className="text-xs text-slate-500">Progress</p>
          <p className="text-xl font-bold">{progressPct}%</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-slate-600">Resolution Progress</span>
          <span className="font-medium">{session.total_tickets_resolved} / {session.total_tickets_found}</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-4 overflow-hidden">
          <div className="h-full flex transition-all duration-500">
            <div className="bg-green-500" style={{ width: `${progressPct}%` }} />
            <div className="bg-red-500" style={{ width: `${session.total_tickets_found > 0 ? (session.total_tickets_failed / session.total_tickets_found) * 100 : 0}%` }} />
          </div>
        </div>
        {session.current_ticket_id && (
          <p className="text-sm text-slate-500 mt-2 flex items-center gap-1">
            <Activity className="w-4 h-4 animate-pulse" />
            Currently processing: <Link to={`/tickets/${session.current_ticket_id}`} className="text-primary-600 hover:underline">Ticket #{session.current_ticket_id}</Link>
          </p>
        )}
        {session.status === 'completed' && (
          <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
            <CheckCircle className="w-4 h-4" />
            All tickets resolved! Session completed in {formatDuration(elapsed)}.
          </p>
        )}
      </div>

      {/* Real-time Logs */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-semibold flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            Live Logs
          </h2>
          <div className="flex items-center gap-2">
            {ws?.readyState === WebSocket.OPEN && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" /> Connected
              </span>
            )}
            <span className="text-xs text-slate-400">{session.logs?.length || 0} entries</span>
          </div>
        </div>
        <div className="max-h-96 overflow-y-auto p-2">
          {(session.logs || []).length === 0 ? (
            <p className="text-center text-slate-400 py-8">No logs yet</p>
          ) : (
            (session.logs || []).map((log, i) => <LogLine key={i} log={log} />)
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  )
}

import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { executionsApi } from '../services/api'
import { Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

export default function ExecutionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const executionId = Number(id)
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([])
  const logsEndRef = useRef<HTMLDivElement>(null)
  const { data, isLoading } = useQuery({ queryKey: ['execution', executionId], queryFn: () => executionsApi.get(executionId).then((r) => r.data) })
  useEffect(() => {
    const url = executionsApi.logs(executionId)
    const token = localStorage.getItem('token')
    const evtSource = new EventSource(`${url}?token=${token || ''}`, { withCredentials: false })
    evtSource.onmessage = (event) => { try { const parsed = JSON.parse(event.data); if (parsed.message === 'Stream ended') { evtSource.close(); return }; setLogs((prev) => [...prev, parsed]) } catch {} }
    evtSource.onerror = () => { evtSource.close() }
    return () => evtSource.close()
  }, [executionId])
  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [logs])
  const execution = data
  if (isLoading || !execution) return <div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Execution #{execution.id}</h1>
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-2">
        <p><strong>Status:</strong> {execution.status}</p>
        <p><strong>Trigger:</strong> {execution.trigger_type}</p>
        <p><strong>Bugs Found:</strong> {execution.total_bugs_found}</p>
        <p><strong>Bugs Fixed:</strong> {execution.total_bugs_fixed}</p>
        <p><strong>Started:</strong> {execution.started_at ? new Date(execution.started_at).toLocaleString() : '-'}</p>
        <p><strong>Completed:</strong> {execution.completed_at ? new Date(execution.completed_at).toLocaleString() : '-'}</p>
        {execution.error_message && <p className="text-red-600"><strong>Error:</strong> {execution.error_message}</p>}
      </div>
      <div>
        <h2 className="text-lg font-semibold mb-2">Live Logs</h2>
        <div className="bg-slate-900 text-slate-100 p-4 rounded-xl h-96 overflow-y-auto font-mono text-sm space-y-1">
          {logs.map((log, i) => (<div key={i} className={`${log.level === 'error' ? 'text-red-400' : log.level === 'warning' ? 'text-yellow-400' : 'text-slate-300'}`}><span className="text-slate-500 text-xs mr-2">{String(log.timestamp || '').split('.')[0]}</span><span className="font-bold uppercase text-xs mr-2">{String(log.level)}</span>{String(log.message)}</div>))}
          <div ref={logsEndRef} />
        </div>
      </div>
      {execution.tickets && execution.tickets.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-2">Tickets</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {execution.tickets.map((ticket: any) => (<div key={ticket.id} className="bg-white p-4 rounded-xl shadow-sm border border-slate-200"><div className="font-medium">{ticket.title}</div><div className="text-xs text-slate-500 mt-1">{ticket.severity} | {ticket.category} | {ticket.status}</div></div>))}
          </div>
        </div>
      )}
    </div>
  )
}

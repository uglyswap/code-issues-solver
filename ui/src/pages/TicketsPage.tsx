import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ticketsApi, projectsApi } from '../services/api'
import type { Ticket, Project } from '../types'
import { Loader2 } from 'lucide-react'

export default function TicketsPage() {
  const [projectId, setProjectId] = useState<number | ''>('')
  const [statusFilter, setStatusFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const { data: projectsData } = useQuery({ queryKey: ['projects'], queryFn: () => projectsApi.list().then((r) => r.data) })
  const { data, isLoading } = useQuery({ queryKey: ['tickets', projectId, statusFilter, severityFilter], queryFn: () => { const pid = projectId || projectsData?.items?.[0]?.id; if (!pid) return { items: [] }; return ticketsApi.list(pid, { page: 1, per_page: 50, status: statusFilter || undefined, severity: severityFilter || undefined }).then((r) => r.data) }, enabled: !!projectsData })
  const tickets: Ticket[] = data?.items || []
  const projects: Project[] = projectsData?.items || []
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold">Tickets</h1>
        <select className="border rounded-lg px-3 py-2" value={projectId} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : '')}><option value="">All Projects</option>{projects.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}</select>
        <select className="border rounded-lg px-3 py-2" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="">All Statuses</option><option value="open">Open</option><option value="patched">Patched</option><option value="pr_open">PR Open</option><option value="merged">Merged</option><option value="deployed">Deployed</option><option value="verified">Verified</option><option value="failed">Failed</option><option value="ignored">Ignored</option></select>
        <select className="border rounded-lg px-3 py-2" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}><option value="">All Severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
      </div>
      {isLoading ? (<div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tickets.map((ticket) => (
            <div key={ticket.id} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
              <div className="flex items-center justify-between mb-2"><Link to={`/tickets/${ticket.id}`} className="font-semibold text-primary-700 hover:underline truncate">{ticket.title}</Link></div>
              <p className="text-sm text-slate-600 line-clamp-2">{ticket.description}</p>
              <div className="flex flex-wrap gap-2 text-xs mt-3">
                <span className={`px-2 py-1 rounded ${ticket.severity === 'critical' ? 'bg-red-100 text-red-700' : ticket.severity === 'high' ? 'bg-orange-100 text-orange-700' : ticket.severity === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-slate-100 text-slate-700'}`}>{ticket.severity}</span>
                <span className="bg-slate-100 px-2 py-1 rounded">{ticket.category}</span>
                <span className="bg-slate-100 px-2 py-1 rounded">{ticket.status}</span>
              </div>
              {ticket.github_issue_url && (<a href={ticket.github_issue_url} target="_blank" rel="noreferrer" className="text-xs text-primary-600 hover:underline mt-2 inline-block">View GitHub Issue #{ticket.github_issue_number}</a>)}
            </div>
          ))}
          {tickets.length === 0 && <div className="text-slate-500">No tickets found</div>}
        </div>
      )}
    </div>
  )
}

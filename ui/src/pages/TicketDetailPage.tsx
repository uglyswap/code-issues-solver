import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ticketsApi } from '../services/api'
import { Loader2, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const ticketId = Number(id)
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['ticket', ticketId], queryFn: () => ticketsApi.get(ticketId).then((r) => r.data) })
  const retryMutation = useMutation({ mutationFn: () => ticketsApi.retry(ticketId), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] }); toast.success('Retry started') }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const ticket = data
  if (isLoading || !ticket) return <div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Ticket #{ticket.id}</h1>
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{ticket.title}</h2>
          {ticket.status === 'failed' && (<button onClick={() => retryMutation.mutate()} className="flex items-center gap-2 bg-primary-600 text-white px-3 py-1.5 rounded-lg hover:bg-primary-700 text-sm"><RefreshCw className="w-4 h-4" /> Retry</button>)}
        </div>
        <p className="text-slate-700">{ticket.description}</p>
        <div className="flex flex-wrap gap-2 text-sm">
          <span className={`px-2 py-1 rounded ${ticket.severity === 'critical' ? 'bg-red-100 text-red-700' : ticket.severity === 'high' ? 'bg-orange-100 text-orange-700' : ticket.severity === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-slate-100 text-slate-700'}`}>{ticket.severity}</span>
          <span className="bg-slate-100 px-2 py-1 rounded">{ticket.category}</span>
          <span className="bg-slate-100 px-2 py-1 rounded">{ticket.status}</span>
          <span className="bg-slate-100 px-2 py-1 rounded">Retry: {ticket.retry_count}/{ticket.max_retries}</span>
        </div>
        {ticket.github_issue_url && (<p><a href={ticket.github_issue_url} target="_blank" rel="noreferrer" className="text-primary-600 hover:underline">GitHub Issue #{ticket.github_issue_number}</a></p>)}
        {ticket.github_pr_url && (<p><a href={ticket.github_pr_url} target="_blank" rel="noreferrer" className="text-primary-600 hover:underline">PR #{ticket.github_pr_number}</a></p>)}
        {ticket.patch_content && (<div><h3 className="font-semibold mt-4 mb-1">Patch</h3><pre className="bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto text-sm">{ticket.patch_content}</pre></div>)}
        {ticket.console_logs && (<div><h3 className="font-semibold mt-4 mb-1">Console Logs</h3><pre className="bg-slate-100 p-4 rounded-lg overflow-x-auto text-sm">{JSON.stringify(ticket.console_logs, null, 2)}</pre></div>)}
      </div>
    </div>
  )
}

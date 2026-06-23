import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ticketsApi } from '../services/api'
import type { Ticket, AttemptLog } from '../types'
import {
  Loader2, RefreshCw, ArrowLeft, CheckCircle, XCircle,
  Clock, ExternalLink, FileCode, GitBranch,
  Zap, Play, Eye,
} from 'lucide-react'
import toast from 'react-hot-toast'

function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${(seconds / 3600).toFixed(1)}h`
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    open: 'bg-blue-100 text-blue-700 border-blue-200',
    patching: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    reviewing: 'bg-purple-100 text-purple-700 border-purple-200',
    creating_pr: 'bg-indigo-100 text-indigo-700 border-indigo-200',
    deploying: 'bg-cyan-100 text-cyan-700 border-cyan-200',
    verifying: 'bg-teal-100 text-teal-700 border-teal-200',
    verified: 'bg-green-100 text-green-700 border-green-200',
    deployed: 'bg-green-100 text-green-700 border-green-200',
    failed: 'bg-red-100 text-red-700 border-red-200',
    ignored: 'bg-slate-100 text-slate-700 border-slate-200',
  }
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${colors[status] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
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

function AttemptTimeline({ attempts }: { attempts: AttemptLog[] }) {
  return (
    <div className="space-y-0">
      {attempts.map((attempt, i) => (
        <div key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              attempt.status === 'success' || attempt.status === 'approved' ? 'bg-green-100' :
              attempt.status === 'failed' || attempt.status === 'rejected' ? 'bg-red-100' :
              'bg-yellow-100'
            }`}>
              {attempt.status === 'success' || attempt.status === 'approved' ? <CheckCircle className="w-4 h-4 text-green-600" /> :
               attempt.status === 'failed' || attempt.status === 'rejected' ? <XCircle className="w-4 h-4 text-red-600" /> :
               <Clock className="w-4 h-4 text-yellow-600" />}
            </div>
            {i < attempts.length - 1 && <div className="w-0.5 h-full bg-slate-200 min-h-[20px]" />}
          </div>
          <div className="pb-4 flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">Attempt {attempt.attempt}</span>
              <span className="text-xs text-slate-400">{new Date(attempt.timestamp).toLocaleString()}</span>
            </div>
            <p className="text-sm text-slate-600 mt-0.5">{attempt.message || attempt.status}</p>
            {attempt.feedback && (
              <div className="mt-2 p-2 bg-slate-50 rounded text-xs text-slate-600 font-mono">
                {attempt.feedback}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>()
  const ticketId = Number(id)
  const queryClient = useQueryClient()
  
  const { data: ticket, isLoading } = useQuery({
    queryKey: ['ticket', ticketId],
    queryFn: () => ticketsApi.get(ticketId).then((r) => r.data as Ticket),
  })
  
  const retryMutation = useMutation({
    mutationFn: () => ticketsApi.retry(ticketId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['ticket', ticketId] }); toast.success('Retry started') },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Error'),
  })

  if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin w-8 h-8 text-primary-600" /></div>
  if (!ticket) return <div className="text-center text-slate-500">Ticket not found</div>

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Link to="/tickets" className="p-2 rounded-lg border hover:bg-slate-50 mt-1">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold">Ticket #{ticket.id}</h1>
            <StatusBadge status={ticket.status} />
            <SeverityBadge severity={ticket.severity} />
          </div>
          <p className="text-slate-600 mt-1">{ticket.title}</p>
          <div className="flex items-center gap-3 mt-2 text-sm text-slate-500">
            <span className="flex items-center gap-1"><FileCode className="w-4 h-4" />{ticket.category}</span>
            <span className="flex items-center gap-1"><Clock className="w-4 h-4" />Created {new Date(ticket.created_at).toLocaleString()}</span>
            {ticket.resolution_time_seconds && (
              <span className="flex items-center gap-1"><Zap className="w-4 h-4" />Resolved in {formatDuration(ticket.resolution_time_seconds)}</span>
            )}
          </div>
        </div>
        {ticket.status === 'failed' && (
          <button onClick={() => retryMutation.mutate()} className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        )}
      </div>

      {/* Resolution Summary */}
      {ticket.resolution_summary && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <Eye className="w-5 h-5 text-primary-600" />
            Resolution Summary
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-slate-500 mb-1">Problem Detected</h3>
              <p className="text-slate-700 bg-red-50 p-3 rounded-lg border border-red-100">
                {ticket.resolution_summary.problem}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-500 mb-1">Solution Applied</h3>
              <p className="text-slate-700 bg-green-50 p-3 rounded-lg border border-green-100">
                {ticket.resolution_summary.solution}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-500 mb-1">Root Cause</h3>
              <p className="text-slate-700 bg-yellow-50 p-3 rounded-lg border border-yellow-100">
                {ticket.resolution_summary.root_cause}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-500 mb-1">Files Affected</h3>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                {ticket.resolution_summary.files_affected?.map((f, i) => (
                  <p key={i} className="text-sm font-mono text-slate-700">{f}</p>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Description */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <h2 className="font-semibold text-lg mb-2">Description</h2>
        <p className="text-slate-700 whitespace-pre-wrap">{ticket.description}</p>
      </div>

      {/* Attempt Timeline */}
      {ticket.attempts_log && ticket.attempts_log.length > 0 && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="font-semibold text-lg mb-4 flex items-center gap-2">
            <Play className="w-5 h-5 text-primary-600" />
            Resolution Timeline ({ticket.attempts_log.length} attempts)
          </h2>
          <AttemptTimeline attempts={ticket.attempts_log} />
        </div>
      )}

      {/* Files Changed */}
      {ticket.files_changed && ticket.files_changed.length > 0 && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="font-semibold text-lg mb-3 flex items-center gap-2">
            <FileCode className="w-5 h-5 text-primary-600" />
            Files Changed ({ticket.files_changed.length})
          </h2>
          <div className="space-y-1">
            {ticket.files_changed.map((file, i) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-slate-50 rounded font-mono text-sm">
                <FileCode className="w-4 h-4 text-slate-400" />
                {file}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Patch Content */}
      {ticket.patch_content && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="font-semibold text-lg mb-3 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-primary-600" />
            Patch
          </h2>
          <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg overflow-x-auto text-sm">
            {ticket.patch_content}
          </pre>
        </div>
      )}

      {/* GitHub Links */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <h2 className="font-semibold text-lg mb-3">GitHub</h2>
        <div className="space-y-2">
          {ticket.github_issue_url && (
            <a href={ticket.github_issue_url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-primary-600 hover:underline">
              <ExternalLink className="w-4 h-4" />
              GitHub Issue #{ticket.github_issue_number}
            </a>
          )}
          {ticket.github_pr_url && (
            <a href={ticket.github_pr_url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-primary-600 hover:underline">
              <ExternalLink className="w-4 h-4" />
              Pull Request #{ticket.github_pr_number}
            </a>
          )}
          {!ticket.github_issue_url && !ticket.github_pr_url && (
            <p className="text-slate-400 text-sm">No GitHub links</p>
          )}
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <h2 className="font-semibold text-lg mb-3">Details</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-slate-500">Retry Count</p>
            <p className="font-medium">{ticket.retry_count} / {ticket.max_retries}</p>
          </div>
          <div>
            <p className="text-slate-500">Created</p>
            <p className="font-medium">{new Date(ticket.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <p className="text-slate-500">Updated</p>
            <p className="font-medium">{new Date(ticket.updated_at).toLocaleDateString()}</p>
          </div>
          {ticket.patch_commit_sha && (
            <div>
              <p className="text-slate-500">Commit</p>
              <p className="font-mono text-xs">{ticket.patch_commit_sha.substring(0, 8)}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

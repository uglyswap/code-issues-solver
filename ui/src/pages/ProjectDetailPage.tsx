import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, executionsApi } from '../services/api'
import { Play, ArrowLeft } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const projectId = Number(id)
  const { data } = useQuery({ queryKey: ['project', projectId], queryFn: () => projectsApi.get(projectId).then((r) => r.data) })
  const startMutation = useMutation({ mutationFn: () => executionsApi.create(projectId, { trigger_type: 'manual' }), onSuccess: () => { toast.success('Execution started'); queryClient.invalidateQueries({ queryKey: ['executions', projectId] }) }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const project = data
  if (!project) return <div>Loading...</div>
  return (
    <div>
      <button onClick={() => navigate('/projects')} className="flex items-center gap-2 text-slate-600 hover:text-slate-900 mb-4"><ArrowLeft className="w-4 h-4" /> Back</button>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{project.name}</h1>
        <button onClick={() => startMutation.mutate()} className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"><Play className="w-4 h-4" /> Run Execution</button>
      </div>
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-3">
        <p><strong>URL:</strong> {project.app_url}</p>
        <p><strong>GitHub:</strong> {project.github_repo_owner}/{project.github_repo_name}</p>
        <p><strong>Enabled:</strong> {project.enabled ? 'Yes' : 'No'}</p>
        <p><strong>Total Executions:</strong> {project.stats?.total_executions || 0}</p>
        <p><strong>Open Tickets:</strong> {project.stats?.open_tickets || 0}</p>
        <p><strong>Total Tickets:</strong> {project.stats?.total_tickets || 0}</p>
        {project.description && <p><strong>Description:</strong> {project.description}</p>}
      </div>
    </div>
  )
}

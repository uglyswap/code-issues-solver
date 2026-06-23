import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { executionsApi, projectsApi } from '../services/api'
import type { Execution, Project } from '../types'
import { Loader2 } from 'lucide-react'

export default function ExecutionsPage() {
  const [projectId, setProjectId] = useState<number | ''>('')
  const { data: projectsData } = useQuery({ queryKey: ['projects'], queryFn: () => projectsApi.list().then((r) => r.data) })
  const { data, isLoading } = useQuery({ queryKey: ['executions', projectId], queryFn: () => { const pid = projectId || projectsData?.items?.[0]?.id; if (!pid) return { items: [] }; return executionsApi.list(pid, { page: 1, per_page: 50 }).then((r) => r.data) }, enabled: !!projectsData })
  const executions: Execution[] = data?.items || []
  const projects: Project[] = projectsData?.items || []
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Executions</h1>
        <select className="border rounded-lg px-3 py-2" value={projectId} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : '')}>
          <option value="">All Projects</option>
          {projects.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
        </select>
      </div>
      {isLoading ? (<div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50"><tr><th className="text-left px-4 py-3">ID</th><th className="text-left px-4 py-3">Status</th><th className="text-left px-4 py-3">Trigger</th><th className="text-left px-4 py-3">Bugs Found</th><th className="text-left px-4 py-3">Started</th><th className="text-left px-4 py-3">Actions</th></tr></thead>
            <tbody>
              {executions.map((ex) => (
                <tr key={ex.id} className="border-t">
                  <td className="px-4 py-3">{ex.id}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 rounded text-xs font-medium ${ex.status === 'completed' ? 'bg-green-100 text-green-700' : ex.status === 'failed' ? 'bg-red-100 text-red-700' : ex.status === 'running' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-700'}`}>{ex.status}</span></td>
                  <td className="px-4 py-3">{ex.trigger_type}</td>
                  <td className="px-4 py-3">{ex.total_bugs_found}</td>
                  <td className="px-4 py-3">{ex.started_at ? new Date(ex.started_at).toLocaleString() : '-'}</td>
                  <td className="px-4 py-3"><Link to={`/executions/${ex.id}`} className="text-primary-600 hover:underline">Details</Link></td>
                </tr>
              ))}
              {executions.length === 0 && (<tr><td colSpan={6} className="px-4 py-6 text-center text-slate-500">No executions yet</td></tr>)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

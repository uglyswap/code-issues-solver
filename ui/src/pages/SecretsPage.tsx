import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { secretsApi, projectsApi } from '../services/api'
import type { Secret, Project } from '../types'
import { Plus, Trash2, Edit, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function SecretsPage() {
  const queryClient = useQueryClient()
  const [projectId, setProjectId] = useState<number | ''>('')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Secret | null>(null)
  const [form, setForm] = useState<Record<string, unknown>>({})
  const { data: projectsData } = useQuery({ queryKey: ['projects'], queryFn: () => projectsApi.list().then((r) => r.data) })
  const { data, isLoading } = useQuery({ queryKey: ['secrets', projectId], queryFn: () => { const pid = projectId || projectsData?.items?.[0]?.id; if (!pid) return []; return secretsApi.list(pid).then((r) => r.data) }, enabled: !!projectsData })
  const createMutation = useMutation({ mutationFn: () => { const pid = projectId || projectsData?.items?.[0]?.id; return secretsApi.create(pid!, form) }, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['secrets', projectId] }); setShowForm(false); setForm({}); toast.success('Secret created') }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const updateMutation = useMutation({ mutationFn: () => { const pid = projectId || projectsData?.items?.[0]?.id; return secretsApi.update(pid!, editing!.id, form) }, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['secrets', projectId] }); setEditing(null); setForm({}); toast.success('Secret updated') }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const deleteMutation = useMutation({ mutationFn: (secretId: number) => { const pid = projectId || projectsData?.items?.[0]?.id; return secretsApi.delete(pid!, secretId) }, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['secrets', projectId] }); toast.success('Secret deleted') } })
  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); if (editing) { updateMutation.mutate() } else { createMutation.mutate() } }
  const secrets: Secret[] = data || []
  const projects: Project[] = projectsData?.items || []
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">Secrets</h1>
        <div className="flex gap-2">
          <select className="border rounded-lg px-3 py-2" value={projectId} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : '')}><option value="">Select Project</option>{projects.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}</select>
          <button onClick={() => { setShowForm(true); setEditing(null); setForm({}) }} className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"><Plus className="w-4 h-4" /> New Secret</button>
        </div>
      </div>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-900">
          <strong>Qu'est-ce qu'un Secret ?</strong> Un secret est une variable d'environnement chiffrée associée à un projet. 
          Utilisez-les pour stocker des tokens API, des credentials, ou toute donnée sensible dont vos agents ont besoin.
        </p>
        <div className="mt-2 text-xs text-blue-700">
          Les secrets sont chiffrés avec Fernet avant d'être stockés en base. Ils ne sont jamais affichés en clair.
        </div>
      </div>
      {(showForm || editing) && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-6 space-y-4">
          <h2 className="font-semibold text-lg">{editing ? 'Edit Secret' : 'New Secret'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <input placeholder="Name" required className="border rounded-lg px-3 py-2 w-full" value={String(form.name || '')} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">Nom du secret (ex: "GITHUB_TOKEN", "API_KEY")</p>
            </div>
            <div>
              <input placeholder="Value" required type="password" className="border rounded-lg px-3 py-2 w-full" value={String(form.value || '')} onChange={(e) => setForm({ ...form, value: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">Valeur du secret (chiffrée automatiquement)</p>
            </div>
          </div>
          <div>
            <textarea placeholder="Description" className="w-full border rounded-lg px-3 py-2" value={String(form.description || '')} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <p className="text-xs text-slate-500 mt-1">Description optionnelle (ex: "Token GitHub pour créer des issues")</p>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">{editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => { setShowForm(false); setEditing(null) }} className="px-4 py-2 rounded-lg border">Cancel</button>
          </div>
        </form>
      )}
      {isLoading ? (<div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50"><tr><th className="text-left px-4 py-3">Name</th><th className="text-left px-4 py-3">Description</th><th className="text-left px-4 py-3">Actions</th></tr></thead>
            <tbody>
              {secrets.map((s) => (
                <tr key={s.id} className="border-t">
                  <td className="px-4 py-3 font-medium">{s.name}</td>
                  <td className="px-4 py-3 text-slate-600">{s.description || '-'}</td>
                  <td className="px-4 py-3 flex gap-2">
                    <button onClick={() => { setEditing(s); setForm({...s} as Record<string, unknown>); setShowForm(true) }} className="text-slate-500 hover:text-primary-600"><Edit className="w-4 h-4" /></button>
                    <button onClick={() => deleteMutation.mutate(s.id)} className="text-slate-500 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
              {secrets.length === 0 && <tr><td colSpan={3} className="px-4 py-6 text-center text-slate-500">No secrets yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

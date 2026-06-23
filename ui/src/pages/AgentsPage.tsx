import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentsApi, providersApi } from '../services/api'
import type { Agent } from '../types'
import { Plus, Trash2, Edit, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function AgentsPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Agent | null>(null)
  const [form, setForm] = useState<Record<string, unknown>>({ enabled: true, temperature: 0.7, max_tokens: 4000 })
  const { data, isLoading } = useQuery({ queryKey: ['agents'], queryFn: () => agentsApi.list().then((r) => r.data) })
  const { data: providersData } = useQuery({ queryKey: ['providers'], queryFn: () => providersApi.list().then((r) => r.data) })
  const createMutation = useMutation({ mutationFn: agentsApi.create, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['agents'] }); setShowForm(false); setForm({ enabled: true, temperature: 0.7, max_tokens: 4000 }); toast.success('Agent created') }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const updateMutation = useMutation({ mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => agentsApi.update(id, data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['agents'] }); setEditing(null); toast.success('Agent updated') }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const deleteMutation = useMutation({ mutationFn: agentsApi.delete, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['agents'] }); toast.success('Agent deleted') } })
  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); if (editing) { updateMutation.mutate({ id: editing.id, data: form }) } else { createMutation.mutate(form) } }
  const agents: Agent[] = data?.items || []
  const providers = providersData?.items || []
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">Agents</h1>
        <button onClick={() => { setShowForm(true); setEditing(null); setForm({ enabled: true, temperature: 0.7, max_tokens: 4000 }) }} className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"><Plus className="w-4 h-4" /> New Agent</button>
      </div>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-900">
          <strong>Qu'est-ce qu'un Agent ?</strong> Un agent IA spécialisé dans une tâche du workflow de correction automatique. 
          5 agents sont créés par défaut : <strong>tester</strong> (détecte les bugs), <strong>triage</strong> (classifie), 
          <strong>coder</strong> (génère les patches), <strong>reviewer</strong> (vérifie la qualité), <strong>verifier</strong> (valide post-déploiement).
        </p>
        <div className="mt-2 text-xs text-blue-700">
          Chaque agent a un prompt spécialisé, un modèle IA, et une température adaptée à sa tâche.
        </div>
      </div>
      {(showForm || editing) && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-6 space-y-4">
          <h2 className="font-semibold text-lg">{editing ? 'Edit Agent' : 'New Agent'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <input placeholder="Name" required className="border rounded-lg px-3 py-2 w-full" value={String(form.name || '')} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">Nom de l'agent (ex: "tester", "coder")</p>
            </div>
            <div>
              <input placeholder="Model" required className="border rounded-lg px-3 py-2 w-full" value={String(form.model || '')} onChange={(e) => setForm({ ...form, model: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">Modèle IA (ex: "anthropic/claude-3.5-sonnet")</p>
            </div>
            <div>
              <input placeholder="Temperature" type="number" step="0.1" className="border rounded-lg px-3 py-2 w-full" value={String(form.temperature ?? 0.7)} onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })} />
              <p className="text-xs text-slate-500 mt-1">Température (0.1 = précis, 0.7 = créatif)</p>
            </div>
            <div>
              <input placeholder="Max Tokens" type="number" className="border rounded-lg px-3 py-2 w-full" value={String(form.max_tokens ?? 4000)} onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })} />
              <p className="text-xs text-slate-500 mt-1">Tokens max (8000 recommandé pour Claude)</p>
            </div>
            <div>
              <select className="border rounded-lg px-3 py-2 w-full" value={String(form.provider_id || '')} onChange={(e) => setForm({ ...form, provider_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">Select Provider</option>
                {providers.map((p: any) => (<option key={p.id} value={p.id}>{p.name}</option>))}
              </select>
              <p className="text-xs text-slate-500 mt-1">Provider IA à utiliser (OpenRouter, Alibaba, etc.)</p>
            </div>
            <label className="flex items-center gap-2"><input type="checkbox" checked={Boolean(form.enabled)} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Enabled</label>
          </div>
          <div>
            <textarea placeholder="System Prompt Template (Jinja2)" required rows={6} className="w-full border rounded-lg px-3 py-2 font-mono text-sm" value={String(form.system_prompt_template || '')} onChange={(e) => setForm({ ...form, system_prompt_template: e.target.value })} />
            <p className="text-xs text-slate-500 mt-1">Prompt système de l'agent (supporte les variables Jinja2 comme {"{{"}bug_description{"}}"})</p>
          </div>
          <div>
            <textarea placeholder="Description" className="w-full border rounded-lg px-3 py-2" value={String(form.description || '')} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <p className="text-xs text-slate-500 mt-1">Description du rôle de l'agent</p>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">{editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => { setShowForm(false); setEditing(null) }} className="px-4 py-2 rounded-lg border">Cancel</button>
          </div>
        </form>
      )}
      {isLoading ? (<div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((a) => (
            <div key={a.id} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <div className="font-semibold">{a.name}</div>
                <div className="flex gap-2">
                  <button onClick={() => { setEditing(a); setForm({...a}); setShowForm(true) }} className="text-slate-500 hover:text-primary-600"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => deleteMutation.mutate(a.id)} className="text-slate-500 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <p className="text-sm text-slate-600">Model: {a.model}</p>
              <p className="text-xs text-slate-500 mt-1">Temp: {a.temperature} | Max Tokens: {a.max_tokens}</p>
              <div className="flex flex-wrap gap-2 text-xs mt-2">
                <span className={`px-2 py-1 rounded ${a.enabled ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{a.enabled ? 'Enabled' : 'Disabled'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

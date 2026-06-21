import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { providersApi } from '../services/api'
import type { AIProvider } from '../types'
import { Plus, Trash2, Edit, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ProvidersPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<AIProvider | null>(null)
  const [form, setForm] = useState<Record<string, unknown>>({ enabled: true, priority: 1, models: {} })
  const { data, isLoading } = useQuery({ queryKey: ['providers'], queryFn: () => providersApi.list().then((r) => r.data) })
  const createMutation = useMutation({ mutationFn: providersApi.create, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['providers'] }); setShowForm(false); setForm({ enabled: true, priority: 1, models: {} }); toast.success('Provider created') }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const updateMutation = useMutation({ mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => providersApi.update(id, data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['providers'] }); setEditing(null); toast.success('Provider updated') }, onError: (err: any) => toast.error(err.response?.data?.detail || 'Error') })
  const deleteMutation = useMutation({ mutationFn: providersApi.delete, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['providers'] }); toast.success('Provider deleted') } })
  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); const payload = { ...form }; if (typeof payload.models === 'string') { try { payload.models = JSON.parse(payload.models) } catch {} } if (editing) { updateMutation.mutate({ id: editing.id, data: payload }) } else { createMutation.mutate(payload) } }
  const providers: AIProvider[] = data?.items || []
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">AI Providers</h1>
        <button onClick={() => { setShowForm(true); setEditing(null); setForm({ enabled: true, priority: 1, models: {} }) }} className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"><Plus className="w-4 h-4" /> New Provider</button>
      </div>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-900">
          <strong>Qu'est-ce qu'un AI Provider ?</strong> Un provider configure un service d'IA (OpenRouter, Alibaba, etc.) 
          avec sa clé API. Les agents IA utilisent ces providers pour générer des patches, analyser les bugs, etc.
        </p>
        <div className="mt-2 text-xs text-blue-700">
          <strong>Exemple :</strong> OpenRouter avec l'API key sk-or-... et la base URL https://openrouter.ai/api/v1
        </div>
      </div>
      {(showForm || editing) && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-6 space-y-4">
          <h2 className="font-semibold text-lg">{editing ? 'Edit Provider' : 'New Provider'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <input placeholder="Name" required className="border rounded-lg px-3 py-2 w-full" value={String(form.name || '')} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">Nom du provider (ex: "openrouter", "alibaba")</p>
            </div>
            <div>
              <input placeholder="Base URL" required className="border rounded-lg px-3 py-2 w-full" value={String(form.base_url || '')} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">URL de l'API (ex: https://openrouter.ai/api/v1)</p>
            </div>
            <div>
              <input placeholder="API Key" required type="password" className="border rounded-lg px-3 py-2 w-full" value={String(form.api_key || '')} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">Clé API du provider (chiffrée en base)</p>
            </div>
            <div>
              <input placeholder="Priority" type="number" className="border rounded-lg px-3 py-2 w-full" value={String(form.priority || 1)} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} />
              <p className="text-xs text-slate-500 mt-1">Priorité (1 = plus haute, utilisé si plusieurs providers)</p>
            </div>
            <div>
              <input placeholder='{"default":"gpt-4"}' className="border rounded-lg px-3 py-2 w-full" value={typeof form.models === 'string' ? form.models : JSON.stringify(form.models)} onChange={(e) => setForm({ ...form, models: e.target.value })} />
              <p className="text-xs text-slate-500 mt-1">Modèles disponibles en JSON (ex: {"{"}"default":"anthropic/claude-3.5-sonnet"{"}"})</p>
            </div>
            <label className="flex items-center gap-2"><input type="checkbox" checked={Boolean(form.enabled)} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Enabled</label>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">{editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => { setShowForm(false); setEditing(null) }} className="px-4 py-2 rounded-lg border">Cancel</button>
          </div>
        </form>
      )}
      {isLoading ? (<div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers.map((p) => (
            <div key={p.id} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <div className="font-semibold">{p.name}</div>
                <div className="flex gap-2">
                  <button onClick={() => { setEditing(p); setForm({ ...p, models: JSON.stringify(p.models) }); setShowForm(true) }} className="text-slate-500 hover:text-primary-600"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => deleteMutation.mutate(p.id)} className="text-slate-500 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <p className="text-sm text-slate-600">{p.base_url}</p>
              <div className="flex flex-wrap gap-2 text-xs mt-2">
                <span className="bg-slate-100 px-2 py-1 rounded">Priority: {p.priority}</span>
                <span className={`px-2 py-1 rounded ${p.enabled ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{p.enabled ? 'Enabled' : 'Disabled'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

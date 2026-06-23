import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { projectsApi } from '../services/api'
import { getErrorDetail } from '../lib/errors'
import type { Project } from '../types'
import { Plus, Loader2, Trash2, Edit, Globe, GitBranch } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ProjectsPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Project | null>(null)
  const [form, setForm] = useState<Record<string, unknown>>({ enabled: true })

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ['projects'], queryFn: () => projectsApi.list().then((r) => r.data) })

  const createMutation = useMutation({ mutationFn: projectsApi.create, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['projects'] }); setShowForm(false); setForm({ enabled: true }); toast.success('Project created') }, onError: (err) => toast.error(getErrorDetail(err)) })
  const updateMutation = useMutation({ mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => projectsApi.update(id, data), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['projects'] }); setEditing(null); setForm({ enabled: true }); toast.success('Project updated') }, onError: (err) => toast.error(getErrorDetail(err)) })
  const deleteMutation = useMutation({ mutationFn: projectsApi.delete, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['projects'] }); toast.success('Project deleted') }, onError: (err) => toast.error(getErrorDetail(err)) })
  const testAppMutation = useMutation({ mutationFn: projectsApi.testApp, onSuccess: (res, projectId) => { if (res.data.success) { toast.success(`✓ App ${projectId}: ${res.data.message}`) } else { toast.error(`✗ App ${projectId}: ${res.data.message}`) } }, onError: () => { toast.error('App test failed') } })
  const testGithubMutation = useMutation({ mutationFn: projectsApi.testGithub, onSuccess: (res, projectId) => { if (res.data.success) { toast.success(`✓ GitHub ${projectId}: ${res.data.message}`) } else { toast.error(`✗ GitHub ${projectId}: ${res.data.message}`) } }, onError: () => { toast.error('GitHub test failed') } })

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); if (editing) { updateMutation.mutate({ id: editing.id, data: form }) } else { createMutation.mutate(form) } }
  const handleDelete = (project: Project) => { if (window.confirm(`Delete project "${project.name}"? This action cannot be undone.`)) { deleteMutation.mutate(project.id) } }
  const projects: Project[] = data?.items || []

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button onClick={() => { setShowForm(true); setEditing(null); setForm({ enabled: true }) }} className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"><Plus className="w-4 h-4" /> New Project</button>
      </div>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-900">
          <strong>Qu'est-ce qu'un projet ?</strong> Un projet configure une application web à tester automatiquement. 
          Le système lance Playwright pour détecter les bugs, crée des GitHub Issues, génère des patches via les agents IA, 
          ouvre des Pull Requests, et redéploie jusqu'à ce que tout fonctionne.
        </p>
        <div className="mt-2 text-xs text-blue-700">
          <strong>Champs requis :</strong> URL de l'app, repo GitHub (owner + name), token GitHub avec permissions issues/PRs.
        </div>
      </div>
      {(showForm || editing) && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-6 space-y-4">
          <h2 className="font-semibold text-lg">{editing ? 'Edit Project' : 'New Project'}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="project-name" className="block text-sm font-medium text-slate-700 mb-1">Name</label>
              <input id="project-name" aria-describedby="project-name-help" placeholder="Name" required className="border rounded-lg px-3 py-2 w-full" value={String(form.name || '')} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <p id="project-name-help" className="text-xs text-slate-500 mt-1">Nom du projet (ex: "Mon Application")</p>
            </div>
            <div>
              <label htmlFor="project-app-url" className="block text-sm font-medium text-slate-700 mb-1">App URL</label>
              <input id="project-app-url" aria-describedby="project-app-url-help" placeholder="App URL" required className="border rounded-lg px-3 py-2 w-full" value={String(form.app_url || '')} onChange={(e) => setForm({ ...form, app_url: e.target.value })} />
              <p id="project-app-url-help" className="text-xs text-slate-500 mt-1">URL de l'application à tester (ex: https://monapp.com)</p>
            </div>
            <div>
              <label htmlFor="project-github-owner" className="block text-sm font-medium text-slate-700 mb-1">GitHub Owner</label>
              <input id="project-github-owner" aria-describedby="project-github-owner-help" placeholder="GitHub Owner" required className="border rounded-lg px-3 py-2 w-full" value={String(form.github_repo_owner || '')} onChange={(e) => setForm({ ...form, github_repo_owner: e.target.value })} />
              <p id="project-github-owner-help" className="text-xs text-slate-500 mt-1">Propriétaire du repo GitHub (ex: "uglyswap")</p>
            </div>
            <div>
              <label htmlFor="project-github-repo" className="block text-sm font-medium text-slate-700 mb-1">GitHub Repo</label>
              <input id="project-github-repo" aria-describedby="project-github-repo-help" placeholder="GitHub Repo" required className="border rounded-lg px-3 py-2 w-full" value={String(form.github_repo_name || '')} onChange={(e) => setForm({ ...form, github_repo_name: e.target.value })} />
              <p id="project-github-repo-help" className="text-xs text-slate-500 mt-1">Nom du repo GitHub à corriger (ex: "code-issues-solver")</p>
            </div>
            <div>
              <label htmlFor="project-app-username" className="block text-sm font-medium text-slate-700 mb-1">App Username</label>
              <input id="project-app-username" aria-describedby="project-app-username-help" placeholder="App Username" className="border rounded-lg px-3 py-2 w-full" value={String(form.app_username || '')} onChange={(e) => setForm({ ...form, app_username: e.target.value })} />
              <p id="project-app-username-help" className="text-xs text-slate-500 mt-1">Username pour se connecter à l'app (optionnel)</p>
            </div>
            <div>
              <label htmlFor="project-app-password" className="block text-sm font-medium text-slate-700 mb-1">App Password</label>
              <input id="project-app-password" aria-describedby="project-app-password-help" placeholder="App Password" type="password" autoComplete="new-password" className="border rounded-lg px-3 py-2 w-full" value={String(form.app_password || '')} onChange={(e) => setForm({ ...form, app_password: e.target.value })} />
              <p id="project-app-password-help" className="text-xs text-slate-500 mt-1">Password pour se connecter à l'app (optionnel)</p>
            </div>
            <div>
              <label htmlFor="project-github-token" className="block text-sm font-medium text-slate-700 mb-1">GitHub Token</label>
              <input id="project-github-token" aria-describedby="project-github-token-help" placeholder="GitHub Token" type="password" autoComplete="new-password" className="border rounded-lg px-3 py-2 w-full" value={String(form.github_token || '')} onChange={(e) => setForm({ ...form, github_token: e.target.value })} />
              <p id="project-github-token-help" className="text-xs text-slate-500 mt-1">Token GitHub avec permissions repo, issues, pull requests</p>
            </div>
            <div>
              <label htmlFor="project-deploy-webhook" className="block text-sm font-medium text-slate-700 mb-1">Deploy Webhook URL</label>
              <input id="project-deploy-webhook" aria-describedby="project-deploy-webhook-help" placeholder="Deploy Webhook URL" className="border rounded-lg px-3 py-2 w-full" value={String(form.deploy_webhook_url || '')} onChange={(e) => setForm({ ...form, deploy_webhook_url: e.target.value })} />
              <p id="project-deploy-webhook-help" className="text-xs text-slate-500 mt-1">URL webhook pour déclencher le déploiement après merge PR (optionnel)</p>
            </div>
            <div>
              <label htmlFor="project-schedule-cron" className="block text-sm font-medium text-slate-700 mb-1">Schedule Cron</label>
              <input id="project-schedule-cron" aria-describedby="project-schedule-cron-help" placeholder="Schedule Cron" className="border rounded-lg px-3 py-2 w-full" value={String(form.schedule_cron || '')} onChange={(e) => setForm({ ...form, schedule_cron: e.target.value })} />
              <p id="project-schedule-cron-help" className="text-xs text-slate-500 mt-1">Expression cron pour exécution automatique (ex: "0 2 * * *" = chaque jour à 2h)</p>
            </div>
            <label className="flex items-center gap-2"><input type="checkbox" checked={Boolean(form.enabled)} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Enabled</label>
          </div>
          <div>
            <label htmlFor="project-description" className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea id="project-description" placeholder="Description" className="w-full border rounded-lg px-3 py-2" value={String(form.description || '')} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={createMutation.isPending || updateMutation.isPending} className="flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed">{(createMutation.isPending || updateMutation.isPending) && <Loader2 className="animate-spin w-4 h-4" />}{(createMutation.isPending || updateMutation.isPending) ? 'Saving...' : editing ? 'Update' : 'Create'}</button>
            <button type="button" onClick={() => { setShowForm(false); setEditing(null) }} className="px-4 py-2 rounded-lg border">Cancel</button>
          </div>
        </form>
      )}
      {isLoading ? (<div className="flex justify-center"><Loader2 className="animate-spin w-6 h-6" /></div>) : isError ? (
        <div role="alert" className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 mb-3">Failed to load projects</p>
          <button onClick={() => refetch()} className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">Retry</button>
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center text-slate-500">No projects yet</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div key={project.id} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <Link to={`/projects/${project.id}`} className="font-semibold text-lg text-primary-700 hover:underline">{project.name}</Link>
                <div className="flex gap-2">
                  <button type="button" aria-label={`Test app connection for ${project.name}`} onClick={() => testAppMutation.mutate(project.id)} disabled={testAppMutation.isPending} className="text-slate-500 hover:text-blue-600 disabled:opacity-50" title="Test app connection"><Globe className="w-4 h-4" aria-hidden="true" /></button>
                  <button type="button" aria-label={`Test GitHub connection for ${project.name}`} onClick={() => testGithubMutation.mutate(project.id)} disabled={testGithubMutation.isPending} className="text-slate-500 hover:text-purple-600 disabled:opacity-50" title="Test GitHub connection"><GitBranch className="w-4 h-4" aria-hidden="true" /></button>
                  <button type="button" aria-label={`Edit ${project.name}`} onClick={() => { setEditing(project); setForm({...project} as Record<string, unknown>); setShowForm(true) }} className="text-slate-500 hover:text-primary-600"><Edit className="w-4 h-4" aria-hidden="true" /></button>
                  <button type="button" aria-label={`Delete ${project.name}`} onClick={() => handleDelete(project)} className="text-slate-500 hover:text-red-600"><Trash2 className="w-4 h-4" aria-hidden="true" /></button>
                </div>
              </div>
              <p className="text-slate-600 text-sm mb-3">{project.app_url}</p>
              <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                <span className="bg-slate-100 px-2 py-1 rounded">Execs: {project.stats?.total_executions || 0}</span>
                <span className="bg-slate-100 px-2 py-1 rounded">Open: {project.stats?.open_tickets || 0}</span>
                <span className={`px-2 py-1 rounded ${project.enabled ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{project.enabled ? 'Enabled' : 'Disabled'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
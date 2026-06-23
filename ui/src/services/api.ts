import axios from 'axios'
import { queryClient } from '../lib/query-client'

const API_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // Clear react-query cache to avoid leaking one account's cached data to another.
      queryClient.clear()
      window.location.assign('/')
    }
    return Promise.reject(error)
  }
)

export default api

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/api/auth/login', { username, password }),
  register: (username: string, email: string, password: string) =>
    api.post('/api/auth/register', { username, email, password }),
  me: () => api.get('/api/auth/me'),
}

export const projectsApi = {
  list: (params?: { page?: number; per_page?: number; enabled?: boolean }) =>
    api.get('/api/projects', { params }),
  get: (id: number) => api.get(`/api/projects/${id}`),
  create: (data: Record<string, unknown>) => api.post('/api/projects', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/projects/${id}`, data),
  delete: (id: number) => api.delete(`/api/projects/${id}`),
  testApp: (id: number) => api.post(`/api/projects/${id}/test-app`),
  testGithub: (id: number) => api.post(`/api/projects/${id}/test-github`),
}

export const providersApi = {
  list: (params?: { page?: number; per_page?: number }) => api.get('/api/providers', { params }),
  get: (id: number) => api.get(`/api/providers/${id}`),
  create: (data: Record<string, unknown>) => api.post('/api/providers', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/providers/${id}`, data),
  delete: (id: number) => api.delete(`/api/providers/${id}`),
  test: (id: number) => api.post(`/api/providers/${id}/test`),
}

export const agentsApi = {
  list: (params?: { page?: number; per_page?: number }) => api.get('/api/agents', { params }),
  get: (id: number) => api.get(`/api/agents/${id}`),
  create: (data: Record<string, unknown>) => api.post('/api/agents', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/agents/${id}`, data),
  delete: (id: number) => api.delete(`/api/agents/${id}`),
}

export const executionsApi = {
  list: (projectId: number, params?: { page?: number; per_page?: number; status?: string }) =>
    api.get(`/api/projects/${projectId}/executions`, { params }),
  get: (id: number) => api.get(`/api/executions/${id}`),
  create: (projectId: number, data: { trigger_type: string }) =>
    api.post(`/api/projects/${projectId}/executions`, data),
  logs: (id: number) => `${API_URL}/api/executions/${id}/logs`,
}

export const ticketsApi = {
  list: (projectId: number, params?: { page?: number; per_page?: number; status?: string; severity?: string; category?: string }) =>
    api.get(`/api/projects/${projectId}/tickets`, { params }),
  get: (id: number) => api.get(`/api/tickets/${id}`),
  update: (id: number, data: Record<string, unknown>) => api.put(`/api/tickets/${id}`, data),
  retry: (id: number) => api.post(`/api/tickets/${id}/retry`),
}

export const secretsApi = {
  list: (projectId: number) => api.get(`/api/projects/${projectId}/secrets`),
  create: (projectId: number, data: Record<string, unknown>) =>
    api.post(`/api/projects/${projectId}/secrets`, data),
  update: (projectId: number, id: number, data: Record<string, unknown>) =>
    api.put(`/api/projects/${projectId}/secrets/${id}`, data),
  delete: (projectId: number, id: number) => api.delete(`/api/projects/${projectId}/secrets/${id}`),
}

export const dashboardApi = {
  get: (projectId?: number) => api.get('/api/dashboard', { params: projectId ? { project_id: projectId } : {} }),
  stats: (projectId?: number) => api.get('/api/dashboard/stats', { params: projectId ? { project_id: projectId } : {} }),
  timeline: (projectId?: number, limit = 50) => api.get('/api/dashboard/timeline', { params: { ...(projectId ? { project_id: projectId } : {}), limit } }),
  activeSessions: (projectId?: number) => api.get('/api/dashboard/sessions/active', { params: projectId ? { project_id: projectId } : {} }),
}

export const sessionsApi = {
  list: (projectId?: number, status?: string) => api.get('/api/sessions', { params: { ...(projectId ? { project_id: projectId } : {}), ...(status ? { status_filter: status } : {}) } }),
  get: (id: number) => api.get(`/api/sessions/${id}`),
  create: (data: { project_id: number; trigger_type?: string; auto_close_github_issues?: boolean }) => api.post('/api/sessions', data),
  pause: (id: number) => api.post(`/api/sessions/${id}/pause`),
  resume: (id: number) => api.post(`/api/sessions/${id}/resume`),
  stop: (id: number) => api.post(`/api/sessions/${id}/stop`),
  wsUrl: (id: number) => {
    const baseUrl = API_URL.replace(/^http/, 'ws')
    return `${baseUrl}/api/sessions/ws/${id}`
  },
}

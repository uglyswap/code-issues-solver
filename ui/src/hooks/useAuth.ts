import { useState, useEffect } from 'react'
import { authApi } from '../services/api'
import type { User } from '../types'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setIsLoading(false); return }
    authApi.me().then((res) => setUser(res.data)).catch(() => localStorage.removeItem('token')).finally(() => setIsLoading(false))
  }, [])

  const login = async (username: string, password: string) => {
    const res = await authApi.login(username, password)
    localStorage.setItem('token', res.data.access_token)
    const me = await authApi.me()
    setUser(me.data)
  }

  const logout = () => { localStorage.removeItem('token'); setUser(null) }

  return { user, isLoading, login, logout }
}

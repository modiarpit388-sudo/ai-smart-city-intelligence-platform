import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, getToken, setToken } from './api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const out = () => setUser(null)
    window.addEventListener('scai-logout', out)
    if (!getToken()) { setReady(true); return () => window.removeEventListener('scai-logout', out) }
    api.get('/api/auth/me').then((r) => setUser(r.user)).catch(() => setToken(null)).finally(() => setReady(true))
    return () => window.removeEventListener('scai-logout', out)
  }, [])

  const login = useCallback(async (email, password) => {
    const r = await api.post('/api/auth/login', { email, password })
    setToken(r.token); setUser(r.user); return r.user
  }, [])
  const register = useCallback(async (payload) => {
    const r = await api.post('/api/auth/register', payload)
    setToken(r.token); setUser(r.user); return r.user
  }, [])
  const logout = useCallback(() => { setToken(null); setUser(null) }, [])
  const refresh = useCallback(async () => { const r = await api.get('/api/auth/me'); setUser(r.user) }, [])

  return <Ctx.Provider value={{ user, ready, login, register, logout, refresh }}>{children}</Ctx.Provider>
}

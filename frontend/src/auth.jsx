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
  // Step 1: validates the form and emails an OTP. Does NOT sign the user in.
  const register = useCallback((payload) => api.post('/api/auth/register', payload), [])
  // Step 2: verifies the OTP, creates the account and signs the user in.
  const verifyOtp = useCallback(async (email, otp) => {
    const r = await api.post('/api/auth/verify-otp', { email, otp })
    setToken(r.token); setUser(r.user); return r.user
  }, [])
  const resendOtp = useCallback((email) => api.post('/api/auth/resend-otp', { email }), [])
  // Sign out: cancel the session key on the server (fire-and-forget), then wipe everything in this tab.
  const logout = useCallback(() => {
    const t = getToken()
    if (t) fetch('/api/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${t}` }, keepalive: true }).catch(() => {})
    setToken(null); setUser(null)
    try { sessionStorage.clear() } catch { /* ignore */ }
  }, [])
  const refresh = useCallback(async () => { const r = await api.get('/api/auth/me'); setUser(r.user) }, [])

  return <Ctx.Provider value={{ user, ready, login, register, verifyOtp, resendOtp, logout, refresh }}>{children}</Ctx.Provider>
}

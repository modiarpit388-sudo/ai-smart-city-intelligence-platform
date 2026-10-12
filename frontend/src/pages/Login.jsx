import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LogIn, UserPlus } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Ambient, ParticleField, Skyline } from '../components/CityBackdrop'

const HOME = { citizen: '/home', authority: '/department', admin: '/dashboard' }
const DEMOS = [
  { label: 'Citizen', email: 'citizen@smartcity.ai', pw: 'Citizen@123' },
  { label: 'Authority', email: 'traffic@smartcity.ai', pw: 'Authority@123' },
  { label: 'Admin', email: 'admin@smartcity.ai', pw: 'Admin@123' },
]

export default function Login() {
  const { login, register } = useAuth()
  const nav = useNavigate()
  const [mode, setMode] = useState('login')
  const [f, setF] = useState({ name: '', email: '', password: '', area_id: '' })
  const [areas, setAreas] = useState([])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { fetch('/api/auth/areas').then((r) => r.json()).then((d) => setAreas(d.areas || [])).catch(() => {}) }, [])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e, creds) => {
    e?.preventDefault(); setErr(''); setBusy(true)
    try {
      const u = creds ? await login(creds.email, creds.pw)
        : mode === 'login' ? await login(f.email, f.password)
        : await register({ ...f, area_id: f.area_id || undefined })
      nav(HOME[u.role] || '/map')
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }

  return (
    <>
      <Ambient />
      <div className="auth">
        <ParticleField />
        <Skyline />
        <div className="auth-hero">
          <div style={{ position: 'relative', zIndex: 2 }}>
            <motion.div className="eyebrow" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>Bengaluru · Urban Intelligence</motion.div>
            <motion.h1 initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.7 }}>
              AI <span className="grad">Smart City</span> Intelligence Platform
            </motion.h1>
            <motion.p className="lead" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
              Nine machine-learning models forecast traffic, accident risk, air quality, electricity, water and waste — and an NLP engine routes every citizen complaint — all on one live command center.
            </motion.p>
          </div>
          <motion.div className="hero-stats" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}>
            <div><b className="grad">20</b><span>Localities</span></div>
            <div><b className="grad">9</b><span>AI Models</span></div>
            <div><b className="grad">3</b><span>User Portals</span></div>
            <div><b className="grad">24/7</b><span>Live Forecasts</span></div>
          </motion.div>
        </div>

        <div className="auth-card-wrap">
          <motion.form className="auth-card stack" onSubmit={submit} initial={{ opacity: 0, y: 40, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.6, delay: 0.2 }}>
            <div>
              <h2>{mode === 'login' ? 'Welcome back' : 'Create citizen account'}</h2>
              <span className="mute">{mode === 'login' ? 'Sign in to the command center' : 'Join to track your locality and file complaints'}</span>
            </div>
            {mode === 'register' && <div className="field"><label>Full name</label><input className="input" value={f.name} onChange={set('name')} placeholder="Ananya Rao" required /></div>}
            <div className="field"><label>Email</label><input className="input" type="email" value={f.email} onChange={set('email')} placeholder="you@example.com" required /></div>
            <div className="field"><label>Password</label><input className="input" type="password" value={f.password} onChange={set('password')} placeholder="••••••••" required /></div>
            {mode === 'register' && (
              <div className="field"><label>Home locality</label>
                <select className="input" value={f.area_id} onChange={set('area_id')}><option value="">Select your area…</option>{areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select>
              </div>
            )}
            {err && <div className="err">{err}</div>}
            <button className="btn primary" disabled={busy} style={{ padding: 12 }}>{mode === 'login' ? <><LogIn />Sign in</> : <><UserPlus />Create account</>}</button>
            <div className="center mute" style={{ fontSize: 13 }}>
              {mode === 'login' ? 'New citizen? ' : 'Already registered? '}
              <a href="#" onClick={(e) => { e.preventDefault(); setMode(mode === 'login' ? 'register' : 'login'); setErr('') }}>{mode === 'login' ? 'Register' : 'Sign in'}</a>
            </div>
            <div>
              <div className="mute" style={{ fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase' }}>One-click demo access</div>
              <div className="demo-row">{DEMOS.map((d) => <button type="button" key={d.label} onClick={(e) => submit(e, d)}>{d.label}</button>)}</div>
            </div>
          </motion.form>
        </div>
      </div>
    </>
  )
}

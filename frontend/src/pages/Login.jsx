import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, LogIn, MailCheck, UserPlus } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Ambient, ParticleField, Skyline } from '../components/CityBackdrop'
import Credit from '../components/Credit'

// Password rules shown live while registering (keep in sync with backend/app/services/password_policy.py)
const PW_RULES = [
  { label: 'At least 8 characters', test: (p) => p.length >= 8 },
  { label: 'One uppercase letter (A–Z)', test: (p) => /[A-Z]/.test(p) },
  { label: 'One lowercase letter (a–z)', test: (p) => /[a-z]/.test(p) },
  { label: 'One digit (0–9)', test: (p) => /\d/.test(p) },
  { label: 'One special character (@ # $ % !)', test: (p) => /[^A-Za-z0-9]/.test(p) },
]
const pwOk = (p) => PW_RULES.every((r) => r.test(p))

const HOME = { citizen: '/home', authority: '/department', admin: '/dashboard' }
const DEMOS = [
  { label: 'Citizen', email: 'citizen@smartcity.ai', pw: 'Citizen@123' },
  { label: 'Authority', email: 'traffic@smartcity.ai', pw: 'Authority@123' },
  { label: 'Admin', email: 'admin@smartcity.ai', pw: 'Admin@123' },
]

export default function Login() {
  const { login, register, verifyOtp, resendOtp } = useAuth()
  const nav = useNavigate()
  const [mode, setMode] = useState('login') // login | register | verify
  const [f, setF] = useState({ name: '', email: '', password: '', area_id: '' })
  const [areas, setAreas] = useState([])
  const [err, setErr] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)
  const [otp, setOtp] = useState('')            // 6-digit code typed by the user
  const [emailSent, setEmailSent] = useState(true) // false = server has no email provider configured
  const [cooldown, setCooldown] = useState(0)   // seconds until "Resend" is enabled
  const otpRef = useRef(null)

  useEffect(() => { fetch('/api/auth/areas').then((r) => r.json()).then((d) => setAreas(d.areas || [])).catch(() => {}) }, [])
  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])
  useEffect(() => { if (mode === 'verify') otpRef.current?.focus() }, [mode])

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e, creds) => {
    e?.preventDefault(); setErr(''); setInfo(''); setBusy(true)
    try {
      if (creds || mode === 'login') {
        const u = creds ? await login(creds.email, creds.pw) : await login(f.email, f.password)
        nav(HOME[u.role] || '/map')
      } else if (mode === 'register') {
        // Step 1: the server validates the form and emails a one-time code
        const r = await register({ ...f, area_id: f.area_id || undefined })
        setOtp(''); setCooldown(r.resend_in || 60); setEmailSent(r.email_sent !== false); setMode('verify')
      } else {
        // Step 2: verify the code -> account is created and the user is signed in
        const u = await verifyOtp(f.email, otp)
        nav(HOME[u.role] || '/map')
      }
    } catch (ex) {
      setErr(ex.message)
      if (ex.code === 'otp_invalid') setOtp('')
    } finally { setBusy(false) }
  }

  const resend = async () => {
    setErr(''); setInfo(''); setBusy(true)
    try {
      const r = await resendOtp(f.email)
      setOtp(''); setCooldown(r.resend_in || 60); setEmailSent(r.email_sent !== false)
      setInfo(r.email_sent === false ? '' : 'A new code has been sent to your email.')
      otpRef.current?.focus()
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }

  const backToRegister = (e) => { e.preventDefault(); setMode('register'); setErr(''); setInfo(''); setOtp('') }
  const toggleMode = (e) => { e.preventDefault(); setMode(mode === 'login' ? 'register' : 'login'); setErr('') }

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
              <h2>{mode === 'login' ? 'Welcome back' : mode === 'verify' ? 'Verify your email' : 'Create citizen account'}</h2>
              <span className="mute">
                {mode === 'login' ? 'Sign in to the command center'
                  : mode === 'verify' ? (emailSent ? <>We sent a 6-digit code to <b>{f.email}</b></> : <>Verifying <b>{f.email}</b></>)
                  : 'Join to track your locality and file complaints'}
              </span>
            </div>

            {mode !== 'verify' && (
              <>
                {mode === 'register' && <div className="field"><label>Full name</label><input className="input" value={f.name} onChange={set('name')} placeholder="Ananya Rao" required /></div>}
                <div className="field"><label>Email</label><input className="input" type="email" value={f.email} onChange={set('email')} placeholder="you@example.com" required /></div>
                <div className="field"><label>Password</label><input className="input" type="password" value={f.password} onChange={set('password')} placeholder="••••••••" required />
                  {mode === 'register' && f.password && (
                    <ul className="pw-rules">
                      {PW_RULES.map((r) => <li key={r.label} className={r.test(f.password) ? 'ok' : ''}>{r.test(f.password) ? '✓' : '○'} {r.label}</li>)}
                    </ul>
                  )}
                </div>
                {mode === 'register' && (
                  <div className="field"><label>Home locality</label>
                    <select className="input" value={f.area_id} onChange={set('area_id')}><option value="">Select your area…</option>{areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select>
                  </div>
                )}
              </>
            )}

            {mode === 'verify' && (
              <div className="field">
                <label>Verification code</label>
                <input ref={otpRef} className="input otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                  value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="······" required />
                {emailSent
                  ? <span className="mute" style={{ fontSize: 12 }}>Check your inbox (and spam folder). The code expires in 10 minutes.</span>
                  : <div className="err" style={{ fontSize: 12.5, lineHeight: 1.5 }}>
                      ⚠ <b>No email was sent</b> – email delivery is not set up on this server yet, so the code was only printed in the
                      server terminal. Set it up with <code>python manage.py setupmail</code> (see EMAIL_SETUP.md), then restart the server and register again.
                    </div>}
              </div>
            )}

            {info && <div className="mute" style={{ fontSize: 13, color: 'var(--cyan)' }}>{info}</div>}
            {err && <div className="err">{err}</div>}

            <button className="btn primary" disabled={busy || (mode === 'verify' && otp.length !== 6) || (mode === 'register' && !pwOk(f.password))} style={{ padding: 12 }}>
              {mode === 'login' ? <><LogIn />Sign in</>
                : mode === 'verify' ? <><MailCheck />Verify &amp; create account</>
                : <><UserPlus />Send verification code</>}
            </button>

            {mode === 'verify' ? (
              <div className="center mute" style={{ fontSize: 13 }}>
                Didn’t get it?{' '}
                {cooldown > 0 ? <span>Resend in {cooldown}s</span>
                  : <a href="#" onClick={(e) => { e.preventDefault(); if (!busy) resend() }}>Resend code</a>}
                <div style={{ marginTop: 6 }}><a href="#" onClick={backToRegister}><ArrowLeft size={12} style={{ verticalAlign: -2 }} /> Change email</a></div>
              </div>
            ) : (
              <div className="center mute" style={{ fontSize: 13 }}>
                {mode === 'login' ? 'New citizen? ' : 'Already registered? '}
                <a href="#" onClick={toggleMode}>{mode === 'login' ? 'Register' : 'Sign in'}</a>
              </div>
            )}

            {mode !== 'verify' && (
              <div>
                <div className="mute" style={{ fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase' }}>One-click demo access</div>
                <div className="demo-row">{DEMOS.map((d) => <button type="button" key={d.label} onClick={(e) => submit(e, d)}>{d.label}</button>)}</div>
              </div>
            )}
          </motion.form>
        </div>
        <Credit />
      </div>
    </>
  )
}

import { useEffect, useRef, useState, useCallback } from 'react'
import { animate, motion } from 'framer-motion'
import { api } from './api'
import { useAuth } from './auth'

// ------------------------------------------------------------- colours / helpers
export const LEVEL_COLOR = {
  LOW: '#34d399', MEDIUM: '#fbbf24', HIGH: '#fb923c', 'VERY HIGH': '#fb7185',
  GOOD: '#34d399', SATISFACTORY: '#a3e635', MODERATE: '#fbbf24', POOR: '#fb923c', 'VERY POOR': '#fb7185', SEVERE: '#e11d48',
  NORMAL: '#34d399',
}
export const levelColor = (l) => LEVEL_COLOR[String(l || '').toUpperCase()] || '#8b9bc4'
export const slug = (s) => String(s || '').toLowerCase().replace(/\s+/g, '-')
export const trafficColor = (v) => (v < 35 ? '#34d399' : v < 60 ? '#fbbf24' : v < 80 ? '#fb923c' : '#fb7185')
export const aqiColor = (v) => (v <= 50 ? '#34d399' : v <= 100 ? '#a3e635' : v <= 200 ? '#fbbf24' : v <= 300 ? '#fb923c' : v <= 400 ? '#fb7185' : '#e11d48')
export const riskColor = (v) => (v < 35 ? '#34d399' : v < 75 ? '#fbbf24' : '#fb7185')
export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '')

// ------------------------------------------------------------- data hook
export function useFetch(path, deps = [], { interval } = {}) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback((silent) => {
    if (!path) return
    if (!silent) setLoading(true)
    return api.get(path).then((d) => { setData(d); setError(null) }).catch((e) => setError(e)).finally(() => setLoading(false))
  }, [path])
  useEffect(() => { load(); }, [load, ...deps]) // eslint-disable-line
  useEffect(() => {
    if (!interval) return
    const id = setInterval(() => load(true), interval)
    return () => clearInterval(id)
  }, [interval, load])
  return { data, error, loading, reload: () => load(false) }
}

// ------------------------------------------------------------- small components
export function Loader({ text = 'Scanning city data…' }) {
  return <div className="loader"><div className="radar" /><span>{text}</span></div>
}
export function ErrorBox({ error, retry }) {
  if (!error) return null
  return (
    <div className="panel center" style={{ borderColor: 'rgba(251,113,133,.4)' }}>
      <p style={{ color: 'var(--red)', margin: '4px 0 10px' }}>{error.message}</p>
      {error.code === 'model_not_ready' && <p className="mute">Ask an admin to train the models (Admin → ML Models).</p>}
      {retry && <button className="btn sm" onClick={retry}>Retry</button>}
    </div>
  )
}

export function Badge({ level, children }) {
  const l = String(level || '')
  return <span className={`badge lv-${slug(l)}`}><i />{children ?? l}</span>
}

export function CountUp({ value, decimals = 0, duration = 1.1 }) {
  const ref = useRef(null)
  const prev = useRef(0)
  useEffect(() => {
    const ctl = animate(prev.current, Number(value) || 0, {
      duration, ease: 'easeOut',
      onUpdate: (v) => { if (ref.current) ref.current.textContent = v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) },
    })
    prev.current = Number(value) || 0
    return () => ctl.stop()
  }, [value, decimals, duration])
  return <span ref={ref}>0</span>
}

export function Panel({ title, icon: Icon, right, children, className = '', delay = 0, flush }) {
  return (
    <motion.section className={`panel ${flush ? 'flush' : ''} ${className}`} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay, ease: 'easeOut' }}>
      {(title || right) && (
        <div className="panel-h" style={flush ? { padding: '18px 18px 0' } : undefined}>
          <h3>{Icon && <Icon />}{title}</h3>
          <div className="row">{right}</div>
        </div>
      )}
      {children}
    </motion.section>
  )
}

export function Kpi({ label, value, unit, sub, icon: Icon, color = 'var(--cyan)', pct, decimals = 0, badge, delay = 0, text }) {
  return (
    <motion.div className="panel kpi" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay }}>
      <div className="k-top"><span>{label}</span>{Icon && <div className="k-ico" style={{ color, background: `${color}1f` }}><Icon /></div>}</div>
      <div className="k-val" style={{ color }}>
        {text ?? <CountUp value={value} decimals={decimals} />}{unit && <small>{unit}</small>}
      </div>
      <div className="k-sub row between"><span>{sub}</span>{badge}</div>
      {pct != null && <div className="k-bar"><motion.i initial={{ width: 0 }} animate={{ width: `${Math.min(100, pct)}%` }} transition={{ duration: 1, delay: delay + 0.2 }} style={{ background: color, boxShadow: `0 0 10px ${color}` }} /></div>}
    </motion.div>
  )
}

export function Gauge({ value = 0, label, color, size = 260 }) {
  // semicircle gauge 0-100
  const r = 100, c = Math.PI * r
  const pct = Math.max(0, Math.min(100, value))
  const col = color || riskColor(pct)
  return (
    <div className="gauge" style={{ maxWidth: size }}>
      <svg viewBox="0 0 240 140" width="100%">
        <defs>
          <linearGradient id="gaugeBg" x1="0" x2="1"><stop offset="0" stopColor="#34d399" /><stop offset=".5" stopColor="#fbbf24" /><stop offset="1" stopColor="#fb7185" /></linearGradient>
        </defs>
        <path d="M20 120 A100 100 0 0 1 220 120" fill="none" stroke="rgba(125,165,255,.12)" strokeWidth="16" strokeLinecap="round" />
        <path d="M20 120 A100 100 0 0 1 220 120" fill="none" stroke="url(#gaugeBg)" strokeWidth="3" strokeLinecap="round" opacity=".35" transform="translate(0,14)" />
        <motion.path d="M20 120 A100 100 0 0 1 220 120" fill="none" stroke={col} strokeWidth="16" strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - pct / 100) }} transition={{ duration: 1.3, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 8px ${col})` }} />
      </svg>
      <div className="g-val"><b style={{ color: col }}><CountUp value={pct} decimals={0} />%</b><span className="mute">{label}</span></div>
    </div>
  )
}

export function RankList({ items, valueKey, colorFn, unit = '', max, onPick, selected, labelKey = 'name', idKey = 'area_id', format }) {
  const m = max ?? Math.max(1, ...items.map((i) => i[valueKey]))
  return (
    <div className="rank">
      {items.map((it, i) => {
        const v = it[valueKey]
        const col = colorFn ? colorFn(v, it) : 'var(--cyan)'
        return (
          <motion.div key={it[idKey] ?? it[labelKey]} className={`rank-row ${selected === it[idKey] ? 'sel' : ''}`} onClick={() => onPick && onPick(it)}
            initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }}>
            <span className="n">{String(i + 1).padStart(2, '0')}</span>
            <span>{it[labelKey]}</span>
            <div className="bar"><motion.i initial={{ width: 0 }} animate={{ width: `${(v / m) * 100}%` }} transition={{ duration: 0.9, delay: i * 0.03 }} style={{ background: col, boxShadow: `0 0 8px ${col}88` }} /></div>
            <span className="val" style={{ color: col }}>{format ? format(v, it) : v}{unit}</span>
          </motion.div>
        )
      })}
    </div>
  )
}

export function AreaSelect({ areas, value, onChange }) {
  return (
    <select className="input sel-area" value={value || ''} onChange={(e) => onChange(Number(e.target.value))}>
      {areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
    </select>
  )
}

export function ModelChip({ model }) {
  if (!model || !model.trained) return null
  const m = model.metrics || {}
  const txt = m.R2 != null ? `R² ${m.R2}  ·  RMSE ${m.RMSE}` : m.Accuracy != null ? `Acc ${(m.Accuracy * 100).toFixed(1)}%  ·  F1 ${(m.F1 * 100).toFixed(1)}%` : ''
  return <span className="model-chip">🧠 <b>{model.algorithm}</b> {txt}</span>
}

// Hour chips: "5 PM → Medium"
export function Strip({ items, valueKey = 'value', levelKey = 'level', unit = '' }) {
  return (
    <div className="strip">
      {items.map((it, i) => (
        <motion.div key={i} className={`chip lv-${slug(it[levelKey])}`} initial={{ opacity: 0, y: 14, scale: 0.92 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ delay: i * 0.05 }}>
          <div className="h">{it.label}</div>
          <div className="v" style={{ color: levelColor(it[levelKey]) }}>{it[valueKey]}{unit}</div>
          <div className="l" style={{ color: levelColor(it[levelKey]) }}>{it[levelKey]}</div>
        </motion.div>
      ))}
    </div>
  )
}

export function Modal({ children, onClose }) {
  return (
    <div className="modal-bg" onClick={onClose}>
      <motion.div className="modal" onClick={(e) => e.stopPropagation()} initial={{ opacity: 0, scale: 0.94, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }}>
        {children}
      </motion.div>
    </div>
  )
}

export const useAreas = () => {
  const { data } = useFetch('/api/city/areas')
  return data?.areas || []
}

export function useAreaState() {
  const { user } = useAuth()
  const areas = useAreas()
  const [area, setArea] = useState(user.area_id || 1)
  return { areas, area, setArea }
}

export function PageHead({ areas, area, setArea, model, children }) {
  return (
    <div className="row between wrap" style={{ marginBottom: 18, gap: 12 }}>
      <div className="row wrap">{areas && <AreaSelect areas={areas} value={area} onChange={setArea} />}{children}</div>
      <ModelChip model={model} />
    </div>
  )
}

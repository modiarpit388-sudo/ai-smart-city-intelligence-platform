import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Brain, ClipboardList, Layers, Send, Sparkles } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Badge, ErrorBox, fmtTime, Loader, Modal, Panel, useFetch } from '../ui'
import { ColorBars } from '../charts'

function Analysis({ a }) {
  if (!a) return null
  return (
    <motion.div className="ai-result stack" style={{ gap: 10 }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="pipe"><span>Complaint</span>→<span>TF-IDF</span>→<span>NLP models</span>→<span>Routing</span></div>
      <div className="grid g2" style={{ gap: 10 }}>
        <div><div className="mute" style={{ fontSize: 11 }}>CATEGORY</div><b>{a.category}</b> <span className="dim mono">{Math.round(a.category_confidence * 100)}%</span></div>
        <div><div className="mute" style={{ fontSize: 11 }}>PRIORITY</div><Badge level={a.priority} /> <span className="dim mono">{Math.round(a.priority_confidence * 100)}%</span></div>
        <div><div className="mute" style={{ fontSize: 11 }}>SENTIMENT</div><Badge level={a.sentiment} /> <span className="dim mono">{a.sentiment_score}</span></div>
        <div><div className="mute" style={{ fontSize: 11 }}>LOCATION</div><b>{a.location ? a.location.name : 'not detected'}</b></div>
      </div>
      <div><div className="mute" style={{ fontSize: 11, marginBottom: 4 }}>KEYWORDS</div>{a.keywords.map((k) => <span className="kw" key={k}>{k}</span>)}</div>
      {a.priority_signals?.length > 0 && <div className="pill-note">Safety signals escalated priority: {a.priority_signals.join(', ')}</div>}
    </motion.div>
  )
}

function Detail({ id, onClose, canManage, onChanged }) {
  const { data, loading, reload } = useFetch(`/api/complaints/${id}`, [id])
  const [status, setStatus] = useState('In Progress')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const c = data?.complaint
  const save = async () => { setBusy(true); try { await api.put(`/api/complaints/${id}/status`, { status, note }); setNote(''); reload(); onChanged() } finally { setBusy(false) } }
  return (
    <Modal onClose={onClose}>
      {loading && !c ? <Loader /> : c && (
        <div className="stack">
          <div className="row between"><h3>Complaint #{c.id}</h3><Badge level={c.status} /></div>
          <div className="row wrap"><Badge level={c.priority}>{c.priority} priority</Badge><Badge level={c.sentiment} /><span className="mute">{c.category_icon} {c.category} → {c.department}</span><span className="mute">📍 {c.area}</span></div>
          <p style={{ margin: 0, lineHeight: 1.6 }}>{c.text}</p>
          <div>{c.keywords.map((k) => <span className="kw" key={k}>{k}</span>)}</div>
          <div className="mute" style={{ fontSize: 11, letterSpacing: '.14em' }}>PROGRESS</div>
          <div className="timeline">{c.updates.map((u, i) => <div className="ev" key={i}><b>{u.status}</b> <span className="mute">· {u.by} · {fmtTime(u.created_at)}</span><div className="mute">{u.note}</div></div>)}</div>
          {canManage && (
            <div className="stack" style={{ gap: 10, paddingTop: 10, borderTop: '1px solid var(--line)' }}>
              <div className="row"><select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>{['In Review', 'In Progress', 'Resolved', 'Rejected'].map((s) => <option key={s}>{s}</option>)}</select>
                <button className="btn primary" disabled={busy} onClick={save}>Update</button></div>
              <input className="input" placeholder="Note visible to the citizen (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

function Citizen() {
  const [text, setText] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [open, setOpen] = useState(null)
  const list = useFetch('/api/complaints')
  useEffect(() => {
    setAnalysis(null)
    if (text.trim().length < 15) return
    const t = setTimeout(() => api.post('/api/complaints/analyze', { text }).then(setAnalysis).catch(() => {}), 600)
    return () => clearTimeout(t)
  }, [text])
  const submit = async () => {
    setBusy(true); setMsg('')
    try { const r = await api.post('/api/complaints', { text }); setMsg(`Complaint #${r.complaint.id} submitted and routed to ${r.complaint.department}.`); setText(''); setAnalysis(null); list.reload() }
    catch (e) { setMsg(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="grid g-main-r">
      <Panel title="Report a problem" icon={Sparkles} glow>
        <div className="stack">
          <textarea className="input" placeholder='e.g. "There has been garbage dumped near our apartment in HSR Layout for the last three days."' value={text} onChange={(e) => setText(e.target.value)} />
          {text.trim().length >= 15 && !analysis && <div className="mute row"><Brain size={16} /> AI is analysing…</div>}
          <Analysis a={analysis} />
          <button className="btn primary" disabled={busy || text.trim().length < 8} onClick={submit}><Send />Submit complaint</button>
          {msg && <div className="pill-note" style={{ color: 'var(--green)' }}>{msg}</div>}
        </div>
      </Panel>
      <Panel title="My complaints" icon={ClipboardList} delay={0.1} flush>
        <div style={{ maxHeight: 620, overflowY: 'auto', padding: '8px 12px 14px' }}>
          {list.loading && !list.data ? <Loader /> : list.data?.complaints.length === 0 ? <div className="empty">No complaints yet.</div> : list.data?.complaints.map((c, i) => (
            <motion.div key={c.id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }} onClick={() => setOpen(c.id)}
              style={{ padding: 12, borderRadius: 12, border: '1px solid var(--line)', marginBottom: 8, cursor: 'pointer' }}>
              <div className="row between"><b>{c.category_icon} #{c.id} · {c.category}</b><Badge level={c.status} /></div>
              <div className="mute" style={{ fontSize: 12.5, margin: '4px 0' }}>{c.text.slice(0, 110)}{c.text.length > 110 ? '…' : ''}</div>
              <div className="row wrap"><Badge level={c.priority} /><span className="dim" style={{ fontSize: 11 }}>{c.area} · {fmtTime(c.created_at)}</span></div>
            </motion.div>))}
        </div>
      </Panel>
      {open && <Detail id={open} onClose={() => setOpen(null)} onChanged={list.reload} />}
    </div>
  )
}

function Staff() {
  const [f, setF] = useState({ status: '', priority: '', category: '' })
  const qs = new URLSearchParams({ sort: 'priority', ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) }).toString()
  const list = useFetch(`/api/complaints?${qs}`, [qs])
  const stats = useFetch('/api/complaints/stats', [list.data])
  const clusters = useFetch('/api/complaints/clusters')
  const [open, setOpen] = useState(null)
  const cats = Object.keys(stats.data?.by_category || {})
  const s = stats.data
  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="grid g-main-r">
        <Panel title="By category" icon={ClipboardList}>
          {s && <ColorBars data={Object.entries(s.by_category).map(([label, value]) => ({ label, value }))} colorFn={() => '#22d3ee'} height={200} name="Complaints" />}
        </Panel>
        <Panel title="AI complaint groups (K-Means)" icon={Layers} delay={0.1} flush>
          <div style={{ padding: '4px 14px 14px', maxHeight: 250, overflowY: 'auto' }}>
            {clusters.data?.clusters.map((c) => (
              <div key={c.id} className="stat-line"><span><b style={{ color: 'var(--text)' }}>{c.label}</b><div className="dim" style={{ fontSize: 11 }}>mostly {c.top_category}</div></span>
                <span className="mono">{c.count} <span className="dim">· {c.pending} open</span></span></div>))}
          </div>
        </Panel>
      </div>
      <Panel title={`Complaints (${list.data?.complaints.length ?? '…'})`} icon={ClipboardList} delay={0.1} flush
        right={<div className="row wrap">
          <select className="input sel-filter" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><option value="">All status</option>{['Submitted', 'In Review', 'In Progress', 'Resolved', 'Rejected'].map((x) => <option key={x}>{x}</option>)}</select>
          <select className="input sel-filter" value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })}><option value="">Any priority</option>{['HIGH', 'MEDIUM', 'LOW'].map((x) => <option key={x}>{x}</option>)}</select>
          <select className="input sel-filter" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}><option value="">All categories</option>{cats.map((x) => <option key={x}>{x}</option>)}</select>
        </div>}>
        {list.error ? <ErrorBox error={list.error} /> : (
          <div className="table-wrap" style={{ padding: 8, maxHeight: 560, overflowY: 'auto' }}>
            <table className="t"><thead><tr><th>#</th><th>Complaint</th><th>Category</th><th>Area</th><th>Priority</th><th>Sentiment</th><th>Status</th><th>Filed</th></tr></thead>
              <tbody>{list.data?.complaints.map((c) => (
                <tr key={c.id} className="click" onClick={() => setOpen(c.id)}>
                  <td className="mono">{c.id}</td><td style={{ maxWidth: 360 }}>{c.text.slice(0, 90)}{c.text.length > 90 ? '…' : ''}</td><td>{c.category_icon} {c.category}</td><td>{c.area}</td>
                  <td><Badge level={c.priority} /></td><td><Badge level={c.sentiment} /></td><td><Badge level={c.status} /></td><td className="mute">{fmtTime(c.created_at)}</td>
                </tr>))}</tbody></table>
          </div>)}
      </Panel>
      {open && <Detail id={open} canManage onClose={() => setOpen(null)} onChanged={() => { list.reload(); clusters.reload() }} />}
    </div>
  )
}

export default function Complaints() {
  const { user } = useAuth()
  return user.role === 'citizen' ? <Citizen /> : <Staff />
}

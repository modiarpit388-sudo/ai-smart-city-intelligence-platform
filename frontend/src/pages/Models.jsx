import { useEffect, useState } from 'react'
import { BrainCircuit, Play, RefreshCw } from 'lucide-react'
import { api } from '../api'
import { Badge, ErrorBox, fmtTime, Loader, Panel, RankList, useFetch } from '../ui'
import { MultiLine } from '../charts'

const GROUP = (m) => (m.startsWith('complaint') ? 'complaints' : m)
const pct = (v) => (v * 100).toFixed(1) + '%'

function Confusion({ classes, cm }) {
  const mx = Math.max(1, ...cm.flat())
  return (
    <div className="table-wrap"><table className="t" style={{ textAlign: 'center' }}>
      <thead><tr><th>actual ↓ / pred →</th>{classes.map((c) => <th key={c} className="center">{c}</th>)}</tr></thead>
      <tbody>{cm.map((row, i) => <tr key={i}><td className="mute">{classes[i]}</td>{row.map((v, j) => <td key={j} className="mono" style={{ background: `rgba(34,211,238,${(v / mx) * (i === j ? 0.55 : 0.4)})`, color: i === j ? '#fff' : 'var(--text)' }}>{v}</td>)}</tr>)}</tbody>
    </table></div>
  )
}

export default function Models() {
  const { data, error, loading, reload } = useFetch('/api/admin/models')
  const [sel, setSel] = useState('traffic')
  const [status, setStatus] = useState(null)
  const running = status?.running || data?.status?.running

  useEffect(() => {
    if (!running) return
    const id = setInterval(async () => { const s = await api.get('/api/admin/models/status'); setStatus(s); if (!s.running) reload() }, 1500)
    return () => clearInterval(id)
  }, [running]) // eslint-disable-line

  const retrain = async (groups) => {
    try { await api.post('/api/admin/models/retrain', { groups }); setStatus({ running: true, log: [], current: groups[0] }) } catch (e) { alert(e.message) }
  }
  if (error) return <ErrorBox error={error} retry={reload} />
  if (loading && !data) return <Loader />
  const m = data.models.find((x) => x.module === sel)
  const isReg = m?.task === 'regression'
  const main = isReg ? ['RMSE', 'MAE', 'R2'] : m?.task === 'classification' ? ['Accuracy', 'Precision', 'Recall', 'F1'] : Object.keys(m?.metrics || {})
  const log = status?.log || data.status.log || []

  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="grid g3">
        {data.models.map((x) => (
          <div key={x.module} className="panel" onClick={() => setSel(x.module)} style={{ cursor: 'pointer', borderColor: sel === x.module ? 'var(--cyan)' : undefined, padding: 14 }}>
            <div className="row between"><b>{x.title}</b>{x.trained ? <Badge level="normal">trained</Badge> : <Badge level="high">missing</Badge>}</div>
            {x.trained && <div className="mute" style={{ fontSize: 12, marginTop: 6 }}>{x.algorithm} · v{x.version} · {x.task === 'regression' ? `R² ${x.metrics.R2}` : x.task === 'classification' ? `F1 ${pct(x.metrics.F1)}` : `silhouette ${x.metrics.Silhouette}`}</div>}
          </div>))}
      </div>

      <Panel title="Training control" icon={BrainCircuit} right={<div className="row">
        <button className="btn sm" disabled={running} onClick={() => retrain([GROUP(sel)])}><RefreshCw />Retrain {GROUP(sel)}</button>
        <button className="btn primary sm" disabled={running} onClick={() => retrain(['traffic', 'accident', 'aqi', 'electricity', 'water', 'waste', 'complaints'])}><Play />Retrain all</button></div>}>
        {running && <div className="row" style={{ marginBottom: 10 }}><div className="radar" style={{ width: 28, height: 28 }} /><span>Training <b>{status?.current || data.status.current}</b>… models compare several algorithms on a time-based split.</span></div>}
        <pre className="mono" style={{ margin: 0, maxHeight: 130, overflow: 'auto', fontSize: 11.5, color: 'var(--mute)', background: 'rgba(4,9,22,.6)', padding: 10, borderRadius: 10 }}>{log.length ? log.join('\n') : 'No training run in this session. Click "Retrain" to start.'}</pre>
      </Panel>

      {m?.trained && (
        <>
          <div className="grid g-main-r">
            <Panel title={`${m.title} — active model`} icon={BrainCircuit} glow delay={0.05}>
              <div className="stack" style={{ gap: 6 }}>
                <div className="stat-line"><span>Algorithm</span><b>{m.algorithm}</b></div>
                <div className="stat-line"><span>Version / trained</span><span>v{m.version} · {fmtTime(m.trained_at)}</span></div>
                <div className="stat-line"><span>Train / test rows</span><span className="mono">{m.train_rows?.toLocaleString()} / {m.test_rows?.toLocaleString()}</span></div>
                {main.map((k) => <div className="stat-line" key={k}><span>{k}</span><b className="mono" style={{ color: 'var(--cyan)' }}>{['Accuracy', 'Precision', 'Recall', 'F1'].includes(k) ? pct(m.metrics[k]) : m.metrics[k]}</b></div>)}
              </div>
              <div className="pill-note" style={{ marginTop: 12 }}>{isReg ? 'Time-based split: oldest data trains, the most recent days test — no future leakage.' : m.task === 'classification' ? 'Weighted precision/recall/F1. NLP models are tested on complaint templates never seen in training.' : 'Unsupervised model – evaluated with silhouette score.'}</div>
            </Panel>
            <Panel title="Algorithm comparison" delay={0.1} flush>
              <div className="table-wrap" style={{ padding: 8 }}>
                <table className="t"><thead><tr><th>Algorithm</th>{main.map((k) => <th key={k} className="right">{k}</th>)}<th className="right">Train s</th><th /></tr></thead>
                  <tbody>{m.candidates.map((c) => (
                    <tr key={c.algorithm} style={c.active ? { background: 'rgba(34,211,238,.08)' } : undefined}><td><b>{c.algorithm}</b></td>
                      {main.map((k) => <td key={k} className="num">{['Accuracy', 'Precision', 'Recall', 'F1'].includes(k) ? pct(c.metrics[k]) : c.metrics[k]}</td>)}
                      <td className="num">{c.seconds}</td><td>{c.active && <Badge level="normal">selected</Badge>}</td></tr>))}</tbody></table>
              </div>
            </Panel>
          </div>
          <div className="grid g2">
            {isReg && m.sample?.actual && (
              <Panel title="Actual vs predicted (test set)" delay={0.15}>
                <MultiLine data={m.sample.actual.map((a, i) => ({ i, actual: a, predicted: m.sample.predicted[i] }))} xKey="i" lines={[{ key: 'actual', label: 'Actual', color: '#94a3d8' }, { key: 'predicted', label: 'Predicted', color: '#22d3ee' }]} />
              </Panel>)}
            {m.task === 'classification' && m.sample?.confusion_matrix && <Panel title="Confusion matrix" delay={0.15}><Confusion classes={m.sample.classes} cm={m.sample.confusion_matrix} /></Panel>}
            {m.task === 'clustering' && <Panel title="Discovered complaint groups" delay={0.15}>{m.sample.labels.map((l, i) => <div key={i} className="stat-line"><span>Group {i}</span><b>{l}</b></div>)}</Panel>}
            {Object.keys(m.importance).length > 0 && (
              <Panel title={m.module.startsWith('complaint') ? 'Most influential words' : 'Feature importance'} delay={0.2}>
                <RankList items={Object.entries(m.importance).slice(0, 9).map(([name, v]) => ({ name, v: +(v * 100).toFixed(1) }))} valueKey="v" idKey="name" unit="%" colorFn={() => '#a78bfa'} />
              </Panel>)}
          </div>
        </>
      )}
    </div>
  )
}

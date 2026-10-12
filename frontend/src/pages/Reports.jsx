import { useState } from 'react'
import { Download, FileBarChart, Printer } from 'lucide-react'
import { api } from '../api'
import { ErrorBox, Loader, Panel, useFetch } from '../ui'
import { MultiLine } from '../charts'

const KINDS = [['traffic', 'Traffic'], ['aqi', 'Air Quality'], ['accident', 'Accident'], ['electricity', 'Electricity'], ['water', 'Water'], ['waste', 'Waste'], ['complaints', 'Complaints'], ['models', 'Model accuracy']]
const COLORS = ['#22d3ee', '#a78bfa', '#fbbf24', '#fb7185']
const cell = (v) => (v == null ? '—' : typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : v)

function Table({ cols, rows }) {
  return (
    <div className="table-wrap" style={{ maxHeight: 420, overflowY: 'auto' }}>
      <table className="t"><thead><tr>{cols.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c.key} className={typeof r[c.key] === 'number' ? 'num' : ''}>{cell(r[c.key])}</td>)}</tr>)}</tbody></table>
    </div>
  )
}

export default function Reports() {
  const [kind, setKind] = useState('traffic')
  const [period, setPeriod] = useState('daily')
  const { data, error, loading, reload } = useFetch(`/api/reports/${kind}?period=${period}`, [kind, period])
  const csv = () => api.download(`/api/reports/${kind}?period=${period}&format=csv`, `${kind}_${period}_report.csv`)
  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="row between wrap">
        <div className="tabs">{KINDS.map(([k, l]) => <button key={k} className={`tab ${kind === k ? 'on' : ''}`} onClick={() => setKind(k)}>{l}</button>)}</div>
        <div className="row">
          {kind !== 'models' && <div className="tabs">{['daily', 'weekly', 'monthly', 'yearly'].map((p) => <button key={p} className={`tab ${period === p ? 'on' : ''}`} onClick={() => setPeriod(p)}>{p}</button>)}</div>}
          <button className="btn sm" onClick={csv}><Download />CSV</button><button className="btn sm" onClick={() => window.print()}><Printer />Print</button>
        </div>
      </div>
      {error ? <ErrorBox error={error} retry={reload} /> : loading && !data ? <Loader /> : (
        <>
          {data.chart?.length > 0 && data.rows.length > 1 && (
            <Panel title={`${data.title} · ${period}`} icon={FileBarChart}>
              <MultiLine data={data.rows} lines={data.chart.map((k, i) => ({ key: k, label: data.columns.find((c) => c.key === k)?.label || k, color: COLORS[i % 4] }))} />
            </Panel>
          )}
          <Panel title={`${data.title}${data.kind === 'models' ? '' : ' — by ' + period.replace('ly', '').replace('dai', 'day')}`} flush>
            <div style={{ padding: 8 }}><Table cols={data.columns} rows={data.rows} /></div>
          </Panel>
          {data.by_area?.length > 0 && (
            <Panel title={data.kind === 'complaints' ? 'By category & department' : 'Area comparison'} flush>
              <div style={{ padding: 8 }}><Table cols={data.area_columns} rows={data.by_area} /></div>
            </Panel>
          )}
        </>
      )}
    </div>
  )
}

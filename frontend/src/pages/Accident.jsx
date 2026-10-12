import { useEffect, useState } from 'react'
import { ShieldAlert, SlidersHorizontal, Siren, BarChart3 } from 'lucide-react'
import { api } from '../api'
import { Badge, ErrorBox, Gauge, Loader, PageHead, Panel, RankList, riskColor, useAreaState, useFetch } from '../ui'
import { ColorBars } from '../charts'

function WhatIf({ area, base }) {
  const [p, setP] = useState({ hour: 18, traffic_index: 70, rain_mm: 0, visibility_km: 10 })
  const [res, setRes] = useState(null)
  useEffect(() => {
    if (base && base.area === area) setP({ hour: new Date().getHours(), traffic_index: Math.round(base.inputs.traffic_index), rain_mm: base.inputs.rain_mm, visibility_km: base.inputs.visibility_km })
  }, [area]) // eslint-disable-line
  useEffect(() => {
    const t = setTimeout(() => api.post('/api/predict/accident/custom', { area_id: area, ...p }).then(setRes).catch(() => {}), 250)
    return () => clearTimeout(t)
  }, [p, area])
  const S = ({ k, label, min, max, step = 1, unit }) => (
    <div className="field"><label>{label}: <b className="mono" style={{ color: 'var(--cyan)' }}>{p[k]}{unit}</b></label>
      <input type="range" min={min} max={max} step={step} value={p[k]} onChange={(e) => setP({ ...p, [k]: Number(e.target.value) })} /></div>
  )
  return (
    <div className="stack">
      <S k="hour" label="Hour of day" min={0} max={23} unit=":00" />
      <S k="traffic_index" label="Traffic density" min={0} max={100} unit="/100" />
      <S k="rain_mm" label="Rainfall" min={0} max={15} step={0.5} unit=" mm" />
      <S k="visibility_km" label="Visibility" min={1} max={10} step={0.5} unit=" km" />
      {res && (
        <div className="row between" style={{ padding: 14, borderRadius: 14, border: `1px solid ${riskColor(res.risk_pct)}55`, background: `${riskColor(res.risk_pct)}12` }}>
          <div><div className="mute" style={{ fontSize: 11, letterSpacing: '.14em' }}>SIMULATED RISK</div><span className="big-num" style={{ color: riskColor(res.risk_pct) }}>{res.risk_pct}%</span></div>
          <div className="right"><Badge level={res.level} /><div className="mute" style={{ fontSize: 12, marginTop: 6 }}>{res.factors.join(' · ')}</div></div>
        </div>
      )}
    </div>
  )
}

export default function Accident() {
  const { areas, area, setArea } = useAreaState()
  const { data, error, loading, reload } = useFetch(`/api/predict/accident?area_id=${area}`, [area])
  if (error) return <ErrorBox error={error} retry={reload} />
  return (
    <>
      <PageHead areas={areas} area={area} setArea={setArea} model={data?.model} />
      {loading && !data ? <Loader /> : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="grid g-main-r">
            <Panel title={`Accident risk · ${data.area.name}`} icon={Siren} glow>
              <Gauge value={data.current.risk_pct} label="predicted accident risk" />
              <div className="center" style={{ marginTop: 6 }}><Badge level={data.current.level}>Risk level: {data.current.level}</Badge></div>
              <div style={{ marginTop: 16 }}>
                <div className="mute" style={{ fontSize: 11, letterSpacing: '.14em', textTransform: 'uppercase', marginBottom: 6 }}>Main factors</div>
                {data.current.factors.map((f) => <span key={f} className="factor">• {f}</span>)}
              </div>
              <div className="pill-note" style={{ marginTop: 12 }}>Classification model → LOW / MEDIUM / HIGH. The gauge shows the probability-weighted risk score.</div>
            </Panel>
            <div className="stack">
              <Panel title="Risk forecast · next 12 hours" icon={ShieldAlert} delay={0.1}>
                <ColorBars data={data.forecast} dataKey="risk_pct" colorFn={riskColor} unit="%" name="Risk" height={230} />
              </Panel>
              <Panel title="What-if simulator" icon={SlidersHorizontal} delay={0.15}><WhatIf area={area} base={{ area, inputs: data.current.inputs }} /></Panel>
            </div>
          </div>
          <div className="grid g2">
            <Panel title="Highest-risk localities now" delay={0.1}><RankList items={data.ranking.slice(0, 10)} valueKey="risk_pct" max={100} unit="%" colorFn={riskColor} selected={area} onPick={(r) => setArea(r.area_id)} /></Panel>
            <Panel title="What the model looks at" icon={BarChart3} delay={0.15}>
              <RankList items={Object.entries(data.importance).slice(0, 8).map(([name, v]) => ({ name: name.replace(/_/g, ' '), v: +(v * 100).toFixed(1) }))} valueKey="v" idKey="name" unit="%" colorFn={() => '#a78bfa'} />
              <div className="pill-note" style={{ marginTop: 12 }}>Permutation importance measured on the held-out test set.</div>
            </Panel>
          </div>
        </div>
      )}
    </>
  )
}

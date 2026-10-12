import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { AlertTriangle, ClipboardList, Car, Droplets, Layers, Trash2, Wind, Zap, Radio } from 'lucide-react'
import { ErrorBox, Kpi, Loader, Panel, RankList, Badge, aqiColor, levelColor, riskColor, trafficColor, useFetch } from '../ui'
import { SimpleArea } from '../charts'
import CityMap, { LAYERS } from '../components/CityMap'
import AreaPanel from '../components/AreaPanel'

export function LayerTabs({ layer, setLayer }) {
  return <div className="tabs">{Object.entries(LAYERS).map(([k, v]) => <button key={k} className={`tab ${layer === k ? 'on' : ''}`} onClick={() => setLayer(k)}>{v.label}</button>)}</div>
}

export function AlertList({ alerts, limit = 5 }) {
  if (!alerts?.length) return <div className="empty">No active alerts 🎉</div>
  return alerts.slice(0, limit).map((a) => (
    <div key={a.id} className={`alert-card ${a.severity}`}>
      <AlertTriangle /><div><b>{a.title}</b><p>{a.message}</p></div>
    </div>
  ))
}

export default function Dashboard() {
  const { data, error, loading, reload } = useFetch('/api/city/overview', [], { interval: 60000 })
  const alerts = useFetch('/api/alerts')
  const [layer, setLayer] = useState('traffic')
  const [sel, setSel] = useState(null)
  useEffect(() => { if (data && !sel) setSel([...data.areas].sort((a, b) => b.traffic.value - a.traffic.value)[0].id) }, [data]) // eslint-disable-line

  if (loading && !data) return <Loader />
  if (error) return <ErrorBox error={error} retry={reload} />
  const k = data.kpis, A = data.areas
  return (
    <div className="stack" style={{ gap: 18 }}>
      <div className="grid g6">
        <Kpi delay={0} label="Traffic" icon={Car} text={k.traffic.level} sub={`Avg index ${k.traffic.value}/100 · ${k.traffic.high_areas} hot zones`} color={trafficColor(k.traffic.value)} pct={k.traffic.value} />
        <Kpi delay={0.05} label="Air quality" icon={Wind} value={k.aqi.value} sub={k.aqi.category} badge={<Badge level={k.aqi.category} />} color={aqiColor(k.aqi.value)} pct={k.aqi.value / 3} />
        <Kpi delay={0.1} label="Waste today" icon={Trash2} value={k.waste.total_tons} decimals={1} unit="tons" sub={`Tomorrow ≈ ${k.waste.tomorrow_tons} t`} badge={<Badge level={k.waste.status} />} color="#a78bfa" pct={60} />
        <Kpi delay={0.15} label="Water today" icon={Droplets} value={k.water.total_ml} decimals={1} unit="ML" sub={`Tomorrow ≈ ${k.water.tomorrow_ml} ML`} badge={<Badge level={k.water.status} />} color="#3b82f6" pct={55} />
        <Kpi delay={0.2} label="Electricity" icon={Zap} value={k.electricity.now_mw} unit="MW" sub={`Peak ${k.electricity.peak_mw.toFixed(0)} MW @ ${k.electricity.peak_time}`} color="#fbbf24" pct={(k.electricity.now_mw / k.electricity.peak_mw) * 100} />
        <Kpi delay={0.25} label="Open complaints" icon={ClipboardList} value={k.complaints.open} sub={`${k.complaints.high_priority} high priority · ${k.alerts} alerts`} color="#f472b6" pct={Math.min(100, k.complaints.open)} />
      </div>

      <div className="grid g-main">
        <Panel title="City Map" icon={Layers} right={<LayerTabs layer={layer} setLayer={setLayer} />} delay={0.1}>
          <CityMap areas={A} layer={layer} selectedId={sel} onSelect={(a) => setSel(a.id)} height={470} />
        </Panel>
        <div className="stack">
          <Panel title="Selected locality" icon={Radio} delay={0.15}><AreaPanel areaId={sel} /></Panel>
        </div>
      </div>

      <div className="grid g-main-r">
        <Panel title="AI Alerts" icon={AlertTriangle} delay={0.1} right={<Link to="/alerts">View all</Link>}><AlertList alerts={alerts.data?.alerts} limit={4} /></Panel>
        <div className="grid g2">
          <Panel title="Traffic forecast · city avg" icon={Car} delay={0.15}><SimpleArea data={data.city_traffic_24h} color="#fb923c" name="Congestion" height={210} /></Panel>
          <Panel title="AQI forecast · city avg" icon={Wind} delay={0.2}><SimpleArea data={data.city_aqi_24h} color="#a78bfa" name="AQI" height={210} /></Panel>
        </div>
      </div>

      <div className="grid g3">
        <Panel title="Traffic hotspots (next 6h)" icon={Car} delay={0.1}>
          <RankList items={[...A].sort((a, b) => b.traffic.peak_next6 - a.traffic.peak_next6).slice(0, 6).map((a) => ({ ...a, v: a.traffic.peak_next6 }))} valueKey="v" idKey="id" max={100} colorFn={trafficColor} onPick={(a) => setSel(a.id)} selected={sel} />
        </Panel>
        <Panel title="Accident risk now" icon={AlertTriangle} delay={0.15}>
          <RankList items={[...A].sort((a, b) => b.accident.risk_pct - a.accident.risk_pct).slice(0, 6).map((a) => ({ ...a, v: a.accident.risk_pct }))} valueKey="v" idKey="id" max={100} unit="%" colorFn={riskColor} onPick={(a) => setSel(a.id)} selected={sel} />
        </Panel>
        <Panel title="Waste hotspots · tomorrow" icon={Trash2} delay={0.2}>
          <RankList items={[...A].sort((a, b) => b.waste.tomorrow - a.waste.tomorrow).slice(0, 6).map((a) => ({ ...a, v: a.waste.tomorrow }))} valueKey="v" idKey="id" unit=" t" colorFn={() => '#a78bfa'} onPick={(a) => setSel(a.id)} selected={sel} />
        </Panel>
      </div>
    </div>
  )
}

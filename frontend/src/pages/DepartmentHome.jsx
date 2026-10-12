import { useState } from 'react'
import { AlertTriangle, ClipboardList, Car, Droplets, Siren, Trash2, Wind, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { Badge, ErrorBox, Kpi, Loader, Panel, RankList, Strip, aqiColor, riskColor, trafficColor, useFetch } from '../ui'
import { ForecastChart } from '../charts'
import { AlertList } from './Dashboard'

export default function DepartmentHome() {
  const { user } = useAuth()
  const [dept, setDept] = useState('traffic')
  const q = user.role === 'admin' ? `?dept=${dept}` : ''
  const { data, error, loading, reload } = useFetch(`/api/department/dashboard${q}`, [dept], { interval: 60000 })
  if (error) return <ErrorBox error={error} retry={reload} />
  if (loading && !data) return <Loader />
  const slug = data.department.slug, k = data.kpis, c = data.complaints, D = data.data
  const complaintsKpi = <Kpi label="Pending complaints" icon={ClipboardList} value={c.pending} sub={`${c.high} high priority · ${c.resolved} resolved`} color="#f472b6" pct={Math.min(100, c.pending * 4)} delay={0.2} />

  return (
    <div className="stack" style={{ gap: 18 }}>
      {user.role === 'admin' && <div className="tabs" style={{ alignSelf: 'flex-start' }}>{['traffic', 'pollution', 'water', 'electricity', 'waste'].map((d) => <button key={d} className={`tab ${dept === d ? 'on' : ''}`} onClick={() => setDept(d)}>{d}</button>)}</div>}
      <div className="row"><span style={{ fontSize: 28 }}>{data.department.icon}</span><h2>{data.department.name}</h2></div>

      {slug === 'traffic' && <>
        <div className="grid g4">
          <Kpi label="City traffic" icon={Car} text={k.traffic.level} sub={`Avg ${k.traffic.value}/100`} color={trafficColor(k.traffic.value)} pct={k.traffic.value} />
          <Kpi label="Hot zones" icon={Car} value={k.traffic.high_areas} sub="areas with HIGH traffic" color="#fb923c" delay={0.05} />
          <Kpi label="High accident risk" icon={Siren} value={k.accident.high_risk_areas} sub="localities right now" color="#fb7185" delay={0.1} />
          {complaintsKpi}
        </div>
        <div className="grid g-main-r">
          <Panel title="Traffic hotspots (peak next 12h)"><RankList items={D.traffic.ranking.slice(0, 8)} valueKey="peak" max={100} colorFn={trafficColor} format={(v, r) => `${v} · ${r.peak_time}`} /></Panel>
          <Panel title={`Forecast · ${D.traffic.area.name}`} icon={Car} delay={0.1}><Strip items={D.traffic.forecast.slice(0, 6)} /><div style={{ marginTop: 14 }}><ForecastChart history={D.traffic.history} forecast={D.traffic.forecast} color="#fb923c" dotColor={trafficColor} domain={[0, 100]} height={210} name="congestion" /></div></Panel>
        </div>
        <Panel title="Accident-risk watchlist" icon={Siren} delay={0.15}><RankList items={D.accident.ranking.slice(0, 8)} valueKey="risk_pct" max={100} unit="%" colorFn={riskColor} format={(v, r) => `${v}% · peak ${r.peak_risk}% @ ${r.peak_time}`} /></Panel>
      </>}

      {slug === 'pollution' && <>
        <div className="grid g4">
          <Kpi label="City AQI" icon={Wind} value={k.aqi.value} sub={k.aqi.category} badge={<Badge level={k.aqi.category} />} color={aqiColor(k.aqi.value)} pct={k.aqi.value / 3} />
          <Kpi label="Worst area" icon={Wind} text={k.aqi.worst_area} sub="highest AQI now" color="#fb923c" delay={0.05} />
          <Kpi label="Peak forecast" icon={Wind} value={Math.max(...D.aqi.forecast.map((f) => f.value))} sub={`in ${D.aqi.area.name}, next 24h`} color="#a78bfa" delay={0.1} />
          {complaintsKpi}
        </div>
        <div className="grid g-main-r">
          <Panel title="Most polluted localities"><RankList items={D.aqi.ranking.slice(0, 8)} valueKey="now" max={300} colorFn={aqiColor} format={(v, r) => `${v} · ${r.category}`} /></Panel>
          <Panel title={`AQI forecast · ${D.aqi.area.name}`} icon={Wind} delay={0.1}><ForecastChart history={D.aqi.history} forecast={D.aqi.forecast} color="#a78bfa" dotColor={aqiColor} name="AQI" /></Panel>
        </div>
      </>}

      {slug === 'water' && <>
        <div className="grid g4">
          <Kpi label="City water today" icon={Droplets} value={k.water.total_ml} decimals={1} unit="ML" sub={`Tomorrow ≈ ${k.water.tomorrow_ml} ML`} badge={<Badge level={k.water.status} />} color="#3b82f6" />
          <Kpi label="Highest demand" icon={Droplets} text={D.water.areas[0].name} sub={`${D.water.areas[0].today} ML today`} color="#22d3ee" delay={0.05} />
          <Kpi label="Rising tomorrow" icon={Droplets} value={D.water.areas.filter((a) => a.change_pct > 5).length} sub="areas > +5%" color="#fb923c" delay={0.1} />
          {complaintsKpi}
        </div>
        <div className="grid g-main-r">
          <Panel title="Highest demand today"><RankList items={D.water.areas.slice(0, 8)} valueKey="today" unit=" ML" colorFn={() => '#3b82f6'} /></Panel>
          <Panel title={`Forecast · ${D.water.area.name}`} icon={Droplets} delay={0.1}><ForecastChart history={D.water.history} forecast={D.water.forecast} color="#3b82f6" unit=" ML" name="water" /></Panel>
        </div>
      </>}

      {slug === 'electricity' && <>
        <div className="grid g4">
          <Kpi label="Demand now" icon={Zap} value={D.electricity.current.mw} unit="MW" sub="grid load" color="#fbbf24" pct={(D.electricity.current.mw / D.electricity.peak.mw) * 100} />
          <Kpi label="Tomorrow avg" icon={Zap} value={D.electricity.tomorrow_avg} unit="MW" sub={`${D.electricity.change_pct}% vs today`} color="#22d3ee" delay={0.05} />
          <Kpi label="Peak demand" icon={Zap} value={D.electricity.peak.mw} unit="MW" sub={`Tomorrow ${D.electricity.peak.time}`} color="#fb7185" delay={0.1} />
          {complaintsKpi}
        </div>
        <Panel title="Load forecast" icon={Zap} delay={0.1}><ForecastChart history={D.electricity.history} forecast={D.electricity.forecast} color="#fbbf24" unit=" MW" name="demand" height={280} /></Panel>
      </>}

      {slug === 'waste' && <>
        <div className="grid g4">
          <Kpi label="Today's waste" icon={Trash2} value={k.waste.total_tons} decimals={1} unit="tons" sub="city-wide" color="#a78bfa" />
          <Kpi label="Predicted tomorrow" icon={Trash2} value={k.waste.tomorrow_tons} decimals={1} unit="tons" sub="model forecast" color="#22d3ee" delay={0.05} />
          <Kpi label="High-waste zones" icon={Trash2} value={D.waste.high_zones.length} sub="need extra pickup" color="#fb923c" delay={0.1} />
          {complaintsKpi}
        </div>
        <div className="grid g2">
          <Panel title="High waste zones" icon={Trash2}><RankList items={D.waste.high_zones} valueKey="tomorrow" unit=" t" colorFn={() => '#fb923c'} format={(v, r) => `${v} · ${r.trucks} 🚛`} /></Panel>
          <Panel title={`Forecast · ${D.waste.area.name}`} delay={0.1}><ForecastChart history={D.waste.history} forecast={D.waste.forecast} color="#a78bfa" unit=" t" name="waste" height={230} /></Panel>
        </div>
      </>}

      <div className="grid g2">
        <Panel title="Department alerts" icon={AlertTriangle} right={<Link to="/alerts">All</Link>}><AlertList alerts={data.alerts} limit={4} /></Panel>
        <Panel title="Work queue" icon={ClipboardList} delay={0.1}>
          <p className="mute" style={{ marginTop: 0 }}>{c.pending} complaints are waiting for your department, {c.high} of them flagged HIGH priority by the NLP engine.</p>
          <Link to="/complaints" className="btn primary">Open complaint queue</Link>
        </Panel>
      </div>
    </div>
  )
}

import { motion } from 'framer-motion'
import { AlertTriangle, Car, Droplets, Siren, Trash2, Wind } from 'lucide-react'
import { Badge, Strip, aqiColor, levelColor, riskColor, trafficColor } from '../ui'

/** One-locality snapshot: Traffic / AQI / Water / Waste / Accident risk (+ 8h traffic strip + alerts). */
export default function AreaCard({ d, compact }) {
  const rows = [
    { icon: Car, label: 'Traffic', main: d.traffic.level, sub: `${d.traffic.value}/100 · ${d.traffic.speed} km/h`, color: trafficColor(d.traffic.value) },
    { icon: Wind, label: 'Air quality', main: d.aqi.category, sub: `AQI ${d.aqi.value} · peak ${d.aqi.peak_next24} in 24h`, color: aqiColor(d.aqi.value) },
    { icon: Droplets, label: 'Water', main: d.water.status, sub: `${d.water.today} ML today · tomorrow ${d.water.change_pct > 0 ? '+' : ''}${d.water.change_pct}%`, color: levelColor(d.water.status) },
    { icon: Trash2, label: 'Waste', main: d.waste.status, sub: `${d.waste.today} t today · tomorrow ${d.waste.tomorrow} t`, color: d.waste.status === 'HIGH' ? '#fb923c' : '#34d399' },
    { icon: Siren, label: 'Accident risk', main: d.accident.level, sub: `${d.accident.risk_pct}% · ${d.accident.factors.slice(0, 2).join(', ')}`, color: riskColor(d.accident.risk_pct) },
  ]
  return (
    <div className="stack">
      <div className="row between">
        <div><h3 style={{ fontSize: 20 }}>📍 {d.name}</h3><span className="mute">{d.area_type} · {d.population_k}k residents</span></div>
      </div>
      <div className="stack" style={{ gap: 8 }}>
        {rows.map((r, i) => (
          <motion.div key={r.label} initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 12, border: `1px solid ${r.color}33`, background: `${r.color}0d` }}>
            <r.icon size={18} color={r.color} />
            <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase' }} className="mute">{r.label}</div><div className="mute" style={{ fontSize: 12 }}>{r.sub}</div></div>
            <Badge level={r.main} />
          </motion.div>
        ))}
      </div>
      {!compact && d.traffic_forecast && (<><div className="mute" style={{ fontSize: 11, letterSpacing: '.14em', textTransform: 'uppercase' }}>Traffic next hours</div><Strip items={d.traffic_forecast.slice(0, 6)} /></>)}
      {!compact && d.alerts?.length > 0 && (
        <div>
          <div className="mute" style={{ fontSize: 11, letterSpacing: '.14em', textTransform: 'uppercase', marginBottom: 8 }}>Alerts for this area</div>
          {d.alerts.slice(0, 3).map((a) => (
            <div key={a.id} className={`alert-card ${a.severity}`} style={{ padding: '9px 12px', marginBottom: 6 }}><AlertTriangle /><div><b>{a.title}</b><p>{a.message}</p></div></div>
          ))}
        </div>
      )}
    </div>
  )
}

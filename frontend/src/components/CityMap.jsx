import { useEffect } from 'react'
import { MapContainer, Marker, TileLayer, Tooltip as LTooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { aqiColor, riskColor, trafficColor } from '../ui'

export const LAYERS = {
  traffic: { label: 'Traffic', color: (a) => trafficColor(a.traffic.value), val: (a) => Math.round(a.traffic.value), hot: (a) => a.traffic.value >= 80,
    legend: [['#34d399', 'Low'], ['#fbbf24', 'Medium'], ['#fb923c', 'High'], ['#fb7185', 'Very high']], text: (a) => `${a.traffic.level} · ${a.traffic.value}/100` },
  aqi: { label: 'Air quality', color: (a) => aqiColor(a.aqi.value), val: (a) => a.aqi.value, hot: (a) => a.aqi.value > 200,
    legend: [['#34d399', 'Good'], ['#a3e635', 'Satisfactory'], ['#fbbf24', 'Moderate'], ['#fb923c', 'Poor'], ['#fb7185', 'Very poor']], text: (a) => `AQI ${a.aqi.value} · ${a.aqi.category}` },
  accident: { label: 'Accident risk', color: (a) => riskColor(a.accident.risk_pct), val: (a) => Math.round(a.accident.risk_pct), hot: (a) => a.accident.level === 'HIGH',
    legend: [['#34d399', 'Low'], ['#fbbf24', 'Medium'], ['#fb923c', 'High']], text: (a) => `${a.accident.level} · ${a.accident.risk_pct}%` },
  water: { label: 'Water', color: (a) => ({ HIGH: '#fb923c', LOW: '#3b82f6', NORMAL: '#34d399' }[a.water.status]), val: (a) => a.water.today.toFixed(0), hot: (a) => a.water.status === 'HIGH',
    legend: [['#34d399', 'Normal'], ['#fb923c', 'High'], ['#3b82f6', 'Low']], text: (a) => `${a.water.today} ML · ${a.water.status}` },
  waste: { label: 'Waste', color: (a) => ({ HIGH: '#fb923c', LOW: '#3b82f6', NORMAL: '#34d399' }[a.waste.status]), val: (a) => a.waste.today.toFixed(0), hot: (a) => a.waste.status === 'HIGH',
    legend: [['#34d399', 'Normal'], ['#fb923c', 'High'], ['#3b82f6', 'Low']], text: (a) => `${a.waste.today} t · ${a.waste.status}` },
}

function pinIcon(color, val, hot, selected) {
  return L.divIcon({
    className: '', iconSize: [34, 34], iconAnchor: [17, 17],
    html: `<div class="pin ${hot ? 'hot' : ''}"><div class="ring" style="background:${color}"></div><div class="core" style="background:${color};box-shadow:0 0 ${selected ? 22 : 12}px ${color};transform:scale(${selected ? 1.25 : 1})">${val}</div></div>`,
  })
}

function Fly({ target }) {
  const map = useMap()
  useEffect(() => { if (target) map.flyTo([target.lat, target.lng], Math.max(map.getZoom(), 12), { duration: 0.8 }) }, [target, map])
  return null
}

export default function CityMap({ areas, layer = 'traffic', onSelect, selectedId, height = 480 }) {
  const cfg = LAYERS[layer]
  const sel = areas.find((a) => a.id === selectedId)
  return (
    <div className="map-box" style={{ height }}>
      <MapContainer center={[12.9716, 77.6146]} zoom={11} style={{ height: '100%', width: '100%' }} scrollWheelZoom>
        <TileLayer attribution='&copy; OpenStreetMap &copy; CARTO' url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
        {sel && <Fly target={sel} />}
        {areas.map((a) => (
          <Marker key={a.id} position={[a.lat, a.lng]} icon={pinIcon(cfg.color(a), cfg.val(a), cfg.hot(a), a.id === selectedId)} eventHandlers={{ click: () => onSelect && onSelect(a) }}>
            <LTooltip direction="top" offset={[0, -16]} opacity={1}><b>{a.name}</b><br />{cfg.text(a)}</LTooltip>
          </Marker>
        ))}
      </MapContainer>
      <div className="map-legend"><b style={{ color: 'var(--mute)' }}>{cfg.label}</b>{cfg.legend.map(([c, l]) => <span key={l}><i style={{ background: c }} />{l}</span>)}</div>
    </div>
  )
}

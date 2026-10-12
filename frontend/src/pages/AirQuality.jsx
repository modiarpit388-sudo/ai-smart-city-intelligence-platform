import { Wind, Thermometer, Droplets, CloudSun, Sunrise } from 'lucide-react'
import { motion } from 'framer-motion'
import { Badge, ErrorBox, Kpi, Loader, PageHead, Panel, RankList, Strip, aqiColor, useAreaState, useFetch } from '../ui'
import { ForecastChart } from '../charts'

const POL = { pm25: ['PM2.5', 'µg/m³'], pm10: ['PM10', 'µg/m³'], no2: ['NO₂', 'µg/m³'], so2: ['SO₂', 'µg/m³'], co: ['CO', 'mg/m³'], o3: ['O₃', 'µg/m³'] }

export default function AirQuality() {
  const { areas, area, setArea } = useAreaState()
  const { data, error, loading, reload } = useFetch(`/api/predict/aqi?area_id=${area}`, [area])
  if (error) return <ErrorBox error={error} retry={reload} />
  return (
    <>
      <PageHead areas={areas} area={area} setArea={setArea} model={data?.model} />
      {loading && !data ? <Loader /> : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="grid g4">
            <Kpi label={`AQI · ${data.area.name}`} icon={Wind} value={data.current.aqi} sub={`Main pollutant ${POL[data.current.dominant]?.[0]}`} badge={<Badge level={data.current.category} />} color={aqiColor(data.current.aqi)} pct={data.current.aqi / 3} />
            <Kpi label="City average" icon={CloudSun} value={data.city_avg} sub={data.city_category} color={aqiColor(data.city_avg)} pct={data.city_avg / 3} delay={0.05} />
            <Kpi label="Temperature" icon={Thermometer} value={data.current.temperature} decimals={1} unit="°C" sub={`Humidity ${data.current.humidity}%`} color="#fb923c" delay={0.1} />
            <Kpi label="Wind" icon={Droplets} value={data.current.wind} decimals={1} unit="km/h" sub="disperses pollutants" color="#22d3ee" delay={0.15} />
          </div>
          <div className="grid g-main">
            <Panel title="AQI forecast · next 24 hours" icon={Wind} delay={0.1}>
              <ForecastChart history={data.history} forecast={data.forecast} color="#a78bfa" name="AQI" dotColor={aqiColor} refLine={{ y: 200, label: 'Poor > 200', color: '#fb923c' }} />
            </Panel>
            <Panel title="Tomorrow" icon={Sunrise} delay={0.15}>
              <Strip items={data.tomorrow.map((t) => ({ label: t.name, value: t.value, level: t.category }))} />
              <div className="pill-note" style={{ marginTop: 14 }}>AQI = highest sub-index of PM2.5, PM10, NO₂, SO₂, CO and O₃ (Indian CPCB scale). The forecast uses the traffic forecast, weather and the previous hour's AQI.</div>
            </Panel>
          </div>
          <div className="grid g-main-r">
            <Panel title="Current pollutants" delay={0.1}>
              <div className="grid g3" style={{ gap: 10 }}>
                {Object.entries(POL).map(([k, [n, u]], i) => (
                  <motion.div key={k} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.06 }}
                    style={{ padding: 12, borderRadius: 12, border: `1px solid ${data.current.dominant === k ? aqiColor(data.current.aqi) : 'var(--line)'}`, background: 'rgba(125,165,255,.05)' }}>
                    <div className="mute" style={{ fontSize: 11 }}>{n}</div><div className="mono" style={{ fontSize: 20, fontWeight: 600 }}>{data.current.pollutants[k]}</div><div className="dim" style={{ fontSize: 10 }}>{u}</div>
                  </motion.div>
                ))}
              </div>
            </Panel>
            <Panel title="Air quality by locality" delay={0.15}>
              <RankList items={data.ranking} valueKey="now" max={300} colorFn={aqiColor} selected={area} onPick={(r) => setArea(r.area_id)} format={(v, r) => `${v} · ${r.category}`} />
            </Panel>
          </div>
        </div>
      )}
    </>
  )
}

import { Car, Gauge as GaugeIcon, Route, TrendingUp, Cloud } from 'lucide-react'
import { ErrorBox, Kpi, Loader, PageHead, Panel, RankList, Badge, Strip, trafficColor, useAreaState, useFetch } from '../ui'
import { ForecastChart, SimpleArea } from '../charts'

export default function Traffic() {
  const { areas, area, setArea } = useAreaState()
  const { data, error, loading, reload } = useFetch(`/api/predict/traffic?area_id=${area}`, [area])
  if (error) return <ErrorBox error={error} retry={reload} />
  return (
    <>
      <PageHead areas={areas} area={area} setArea={setArea} model={data?.model} />
      {loading && !data ? <Loader /> : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="grid g4">
            <Kpi label="Current traffic" icon={Car} text={data.current.level} sub={`${data.area.name} · index ${data.current.value}/100`} color={trafficColor(data.current.value)} pct={data.current.value} />
            <Kpi label="Average speed" icon={GaugeIcon} value={data.current.speed} decimals={1} unit="km/h" sub={`${data.area.road_type} road`} color="#22d3ee" pct={data.current.speed * 1.4} delay={0.05} />
            <Kpi label="Vehicles / hour" icon={Route} value={data.current.vehicles} sub="counted by road sensors" color="#8b5cf6" pct={data.current.vehicles / 40} delay={0.1} />
            <Kpi label="Weather" icon={Cloud} text={data.current.weather} sub="from the weather service" color="#60a5fa" delay={0.15} />
          </div>
          <Panel title={`Predicted traffic · ${data.area.name}`} icon={TrendingUp} delay={0.1} right={<Badge level={data.current.level}>Now: {data.current.level}</Badge>}>
            <Strip items={data.forecast.slice(0, 8)} />
            <div style={{ marginTop: 16 }}>
              <ForecastChart history={data.history} forecast={data.forecast} color="#fb923c" name="congestion" dotColor={trafficColor} refLine={{ y: 80, label: 'Very high' }} domain={[0, 100]} />
            </div>
            <div className="pill-note" style={{ marginTop: 10 }}>Recursive forecast: each hour's prediction becomes the "previous traffic" input of the next hour, with the weather service supplying rain and temperature.</div>
          </Panel>
          <div className="grid g-main-r">
            <Panel title="Hotspots · next 12 hours" delay={0.15}>
              <RankList items={data.ranking} valueKey="peak" max={100} colorFn={trafficColor} selected={area} onPick={(r) => setArea(r.area_id)} format={(v, r) => `${v} · ${r.peak_time}`} />
            </Panel>
            <Panel title="City-wide congestion · next 24h" delay={0.2}><SimpleArea data={data.city_24h} color="#22d3ee" name="City avg" height={300} /></Panel>
          </div>
        </div>
      )}
    </>
  )
}

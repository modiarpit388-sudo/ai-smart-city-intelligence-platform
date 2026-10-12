import { Trash2, Truck, TrendingUp, ListOrdered } from 'lucide-react'
import { Badge, ErrorBox, Kpi, Loader, PageHead, Panel, RankList, useAreaState, useFetch } from '../ui'
import { Donut, ForecastChart } from '../charts'

export default function Waste() {
  const { areas, area, setArea } = useAreaState()
  const { data, error, loading, reload } = useFetch(`/api/predict/waste?area_id=${area}`, [area])
  if (error) return <ErrorBox error={error} retry={reload} />
  return (
    <>
      <PageHead areas={areas} area={area} setArea={setArea} model={data?.model} />
      {loading && !data ? <Loader /> : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="grid g4">
            <Kpi label={`Today · ${data.area.name}`} icon={Trash2} value={data.today} decimals={1} unit="tons" sub="generated" color="#a78bfa" pct={60} />
            <Kpi label="Expected tomorrow" icon={TrendingUp} value={data.tomorrow} decimals={1} unit="tons" sub={`Normal: ${data.baseline} t`} badge={<Badge level={data.status} />} color="#22d3ee" delay={0.05} pct={65} />
            <Kpi label="City today" icon={Trash2} value={data.city_total_today} decimals={1} unit="tons" sub="all 20 localities" color="#fbbf24" delay={0.1} />
            <Kpi label="City tomorrow" icon={Truck} value={data.city_total_tomorrow} decimals={1} unit="tons" sub="forecast" color="#34d399" delay={0.15} />
          </div>
          <div className="grid g-main-r">
            <Panel title={`Expected waste tomorrow · ${data.area.name}`} icon={Trash2} delay={0.1}>
              <Donut data={Object.entries(data.breakdown).map(([name, value]) => ({ name, value }))} unit="tons" />
              <div className="stack" style={{ gap: 0, marginTop: 6 }}>{Object.entries(data.breakdown).map(([k, v]) => <div key={k} className="stat-line"><span>{k}</span><span className="mono">{v} tons</span></div>)}</div>
            </Panel>
            <Panel title="Generation · last 14 days + 7-day forecast" icon={TrendingUp} delay={0.15}>
              <ForecastChart history={data.history} forecast={data.forecast} color="#a78bfa" unit=" t" name="waste" height={300} />
            </Panel>
          </div>
          <div className="grid g-main-r">
            <Panel title="High waste areas" icon={ListOrdered} delay={0.1}>
              <RankList items={data.high_zones} valueKey="tomorrow" unit=" t" colorFn={() => '#fb923c'} selected={area} onPick={(r) => setArea(r.area_id)} format={(v, r) => `${v} · +${r.vs_normal_pct}%`} />
            </Panel>
            <Panel title="Recommended collection schedule" icon={Truck} delay={0.15} flush>
              <div className="table-wrap" style={{ padding: 8, maxHeight: 380, overflowY: 'auto' }}>
                <table className="t"><thead><tr><th>Area</th><th className="right">Tomorrow</th><th className="right">Trucks</th><th>Action</th></tr></thead>
                  <tbody>{data.areas.map((r) => (
                    <tr key={r.area_id} className={`click ${r.area_id === area ? 'sel' : ''}`} onClick={() => setArea(r.area_id)}>
                      <td>{r.name}</td><td className="num">{r.tomorrow} t</td><td className="num">🚛 {r.trucks}</td><td><Badge level={r.status === 'HIGH' ? 'HIGH' : 'NORMAL'}>{r.action}</Badge></td>
                    </tr>))}</tbody></table>
              </div>
            </Panel>
          </div>
        </div>
      )}
    </>
  )
}

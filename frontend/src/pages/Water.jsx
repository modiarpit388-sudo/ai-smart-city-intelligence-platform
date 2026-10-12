import { Droplets, TrendingUp, Activity } from 'lucide-react'
import { Badge, ErrorBox, Kpi, Loader, PageHead, Panel, useAreaState, useFetch } from '../ui'
import { ForecastChart } from '../charts'

export default function Water() {
  const { areas, area, setArea } = useAreaState()
  const { data, error, loading, reload } = useFetch(`/api/predict/water?area_id=${area}`, [area])
  if (error) return <ErrorBox error={error} retry={reload} />
  return (
    <>
      <PageHead areas={areas} area={area} setArea={setArea} model={data?.model} />
      {loading && !data ? <Loader /> : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="grid g4">
            <Kpi label={`Today · ${data.area.name}`} icon={Droplets} value={data.today} decimals={2} unit="ML" sub="million litres" color="#3b82f6" badge={<Badge level={data.status} />} pct={60} />
            <Kpi label="Tomorrow" icon={TrendingUp} value={data.tomorrow} decimals={2} unit="ML" sub="model forecast" color="#22d3ee" delay={0.05} pct={62} />
            <Kpi label="Expected change" icon={Activity} text={`${data.change_pct > 0 ? '+' : ''}${data.change_pct}%`} sub={`Normal: ${data.baseline} ML/day`} color={data.change_pct > 5 ? '#fb923c' : '#34d399'} delay={0.1} />
            <Kpi label="City total today" icon={Droplets} value={data.city_total_today} decimals={1} unit="ML" sub={`Tomorrow ≈ ${data.city_total_tomorrow} ML`} color="#a78bfa" delay={0.15} />
          </div>
          <Panel title="Consumption · last 14 days + 7-day forecast" icon={Droplets} delay={0.1}>
            <ForecastChart history={data.history} forecast={data.forecast} color="#3b82f6" unit=" ML" name="water" height={280} />
          </Panel>
          <Panel title="Area-wise water dashboard" delay={0.15} flush>
            <div className="table-wrap" style={{ padding: 8 }}>
              <table className="t"><thead><tr><th>Area</th><th className="right">Today (ML)</th><th className="right">Tomorrow (ML)</th><th className="right">Change</th><th>Status</th></tr></thead>
                <tbody>{data.areas.map((r) => (
                  <tr key={r.area_id} className={`click ${r.area_id === area ? 'sel' : ''}`} onClick={() => setArea(r.area_id)}>
                    <td>{r.name}</td><td className="num">{r.today}</td><td className="num">{r.tomorrow}</td>
                    <td className="num" style={{ color: r.change_pct > 0 ? 'var(--orange)' : 'var(--green)' }}>{r.change_pct > 0 ? '+' : ''}{r.change_pct}%</td><td><Badge level={r.status} /></td>
                  </tr>))}</tbody></table>
            </div>
          </Panel>
        </div>
      )}
    </>
  )
}

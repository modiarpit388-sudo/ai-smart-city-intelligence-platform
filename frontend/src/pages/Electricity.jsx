import { Zap, TrendingUp, Clock, Building } from 'lucide-react'
import { ErrorBox, Kpi, Loader, PageHead, Panel, RankList, useFetch } from '../ui'
import { ForecastChart } from '../charts'

export default function Electricity() {
  const { data, error, loading, reload } = useFetch('/api/predict/electricity')
  if (error) return <ErrorBox error={error} retry={reload} />
  if (loading && !data) return <Loader />
  return (
    <>
      <PageHead model={data.model} />
      <div className="stack" style={{ gap: 18 }}>
        <div className="grid g4">
          <Kpi label="Demand now" icon={Zap} value={data.current.mw} unit="MW" sub="live grid load" color="#fbbf24" pct={(data.current.mw / data.peak.mw) * 100} />
          <Kpi label="Today (avg)" icon={TrendingUp} value={data.today_avg} unit="MW" sub="actual + forecast" color="#22d3ee" delay={0.05} pct={70} />
          <Kpi label="Tomorrow (avg)" icon={TrendingUp} value={data.tomorrow_avg} unit="MW" sub={`${data.change_pct > 0 ? '+' : ''}${data.change_pct}% vs today`} color="#8b5cf6" delay={0.1} pct={78} />
          <Kpi label="Peak demand" icon={Clock} value={data.peak.mw} unit="MW" sub={`Tomorrow at ${data.peak.time}`} color="#fb7185" delay={0.15} pct={92} />
        </div>
        <Panel title="City demand · last 24h + forecast 48h" icon={Zap} delay={0.1}>
          <ForecastChart history={data.history} forecast={data.forecast} color="#fbbf24" unit=" MW" name="demand" height={300} refLine={{ y: data.peak.mw, label: 'Predicted peak', color: '#fb7185' }} />
          <div className="pill-note" style={{ marginTop: 10 }}>Time-series regression using hour, day, month, holiday, temperature, humidity, demand 1 h ago and demand 24 h ago.</div>
        </Panel>
        <Panel title="Estimated load by locality" icon={Building} delay={0.15}>
          <RankList items={data.areas} valueKey="mw" unit=" MW" colorFn={() => '#fbbf24'} idKey="area_id" format={(v, r) => `${v} · ${r.share_pct}%`} />
        </Panel>
      </div>
    </>
  )
}

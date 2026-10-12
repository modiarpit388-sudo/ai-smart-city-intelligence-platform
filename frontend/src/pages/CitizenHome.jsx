import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ClipboardList, MapPin } from 'lucide-react'
import { motion } from 'framer-motion'
import { AreaSelect, ErrorBox, Kpi, Loader, Panel, useAreas, useFetch } from '../ui'
import { api } from '../api'
import { useAuth } from '../auth'
import AreaCard from '../components/AreaCard'
import { AlertList } from './Dashboard'

export default function CitizenHome() {
  const { user, refresh } = useAuth()
  const areas = useAreas()
  const [area, setArea] = useState(user.area_id)
  const detail = useFetch(area ? `/api/city/area/${area}` : null, [area], { interval: 60000 })
  const stats = useFetch('/api/complaints/stats')
  const alerts = useFetch('/api/alerts')

  const change = async (id) => { setArea(id); await api.put('/api/auth/me', { area_id: id }); refresh() }
  if (!area) return <div className="panel center"><h3>Choose your locality</h3><p className="mute">Pick your home area to see live conditions.</p><AreaSelect areas={areas} value={area} onChange={change} /></div>
  const s = stats.data
  return (
    <div className="grid g-main-r">
      <div className="stack">
        <Panel title="My Area" icon={MapPin} delay={0} right={<AreaSelect areas={areas} value={area} onChange={change} />}>
          {detail.loading && !detail.data ? <Loader /> : detail.error ? <ErrorBox error={detail.error} /> : <AreaCard d={detail.data} />}
        </Panel>
      </div>
      <div className="stack">
        <motion.div className="grid g3" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Kpi label="My complaints" icon={ClipboardList} value={s?.total || 0} color="#f472b6" sub="filed so far" />
          <Kpi label="Resolved" value={s?.resolved || 0} color="#34d399" sub="closed by authorities" />
          <Kpi label="Pending" value={s?.pending || 0} color="#fbbf24" sub="being worked on" />
        </motion.div>
        <Panel title="Alerts for my area" icon={AlertTriangle} delay={0.1} right={<Link to="/alerts">All alerts</Link>}><AlertList alerts={alerts.data?.alerts} limit={4} /></Panel>
        <Panel title="Need something fixed?" icon={ClipboardList} delay={0.15}>
          <p className="mute" style={{ marginTop: 0 }}>Describe the problem in your own words. Our NLP engine detects the category, priority, sentiment and location and routes it to the right department automatically.</p>
          <Link to="/complaints" className="btn primary">Report a problem</Link>
        </Panel>
      </div>
    </div>
  )
}

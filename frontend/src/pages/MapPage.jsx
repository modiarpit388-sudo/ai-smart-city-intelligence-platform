import { useEffect, useState } from 'react'
import { Layers, MapPin } from 'lucide-react'
import { ErrorBox, Loader, Panel, useFetch } from '../ui'
import CityMap from '../components/CityMap'
import AreaPanel from '../components/AreaPanel'
import { LayerTabs } from './Dashboard'
import { useAuth } from '../auth'

export default function MapPage() {
  const { user } = useAuth()
  const { data, error, loading, reload } = useFetch('/api/city/overview', [], { interval: 60000 })
  const [layer, setLayer] = useState('traffic')
  const [sel, setSel] = useState(user.area_id || null)
  useEffect(() => { if (data && !sel) setSel(data.areas[0].id) }, [data]) // eslint-disable-line
  if (loading && !data) return <Loader />
  if (error) return <ErrorBox error={error} retry={reload} />
  return (
    <div className="grid g-main">
      <Panel title="Smart City Map" icon={Layers} right={<LayerTabs layer={layer} setLayer={setLayer} />}>
        <CityMap areas={data.areas} layer={layer} selectedId={sel} onSelect={(a) => setSel(a.id)} height={640} />
      </Panel>
      <Panel title="Locality details" icon={MapPin} delay={0.1}><AreaPanel areaId={sel} /></Panel>
    </div>
  )
}

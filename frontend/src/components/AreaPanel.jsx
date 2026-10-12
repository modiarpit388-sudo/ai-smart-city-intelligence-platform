import { useFetch, Loader } from '../ui'
import AreaCard from './AreaCard'

export default function AreaPanel({ areaId }) {
  const { data, loading } = useFetch(areaId ? `/api/city/area/${areaId}` : null, [areaId])
  if (!areaId) return <div className="empty">Click a marker on the map to see live + predicted conditions.</div>
  if (loading && !data) return <Loader />
  return data ? <AreaCard d={data} /> : null
}

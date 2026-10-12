import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import { Loader } from './ui'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import MapPage from './pages/MapPage'
import CitizenHome from './pages/CitizenHome'
import DepartmentHome from './pages/DepartmentHome'
import Traffic from './pages/Traffic'
import Accident from './pages/Accident'
import AirQuality from './pages/AirQuality'
import Electricity from './pages/Electricity'
import Water from './pages/Water'
import Waste from './pages/Waste'
import Complaints from './pages/Complaints'
import Alerts from './pages/Alerts'
import Reports from './pages/Reports'
import Users from './pages/Users'
import Datasets from './pages/Datasets'
import Models from './pages/Models'

const HOME = { citizen: '/home', authority: '/department', admin: '/dashboard' }

function Guard({ roles, children }) {
  const { user } = useAuth()
  return roles.includes(user.role) ? children : <Navigate to={HOME[user.role]} replace />
}

export default function App() {
  const { user, ready } = useAuth()
  if (!ready) return <Loader text="Booting city systems…" />
  if (!user) return <Routes><Route path="*" element={<Login />} /></Routes>
  const all = ['citizen', 'authority', 'admin']
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to={HOME[user.role]} replace />} />
        <Route path="/login" element={<Navigate to={HOME[user.role]} replace />} />
        <Route path="/home" element={<Guard roles={['citizen']}><CitizenHome /></Guard>} />
        <Route path="/department" element={<Guard roles={['authority']}><DepartmentHome /></Guard>} />
        <Route path="/dashboard" element={<Guard roles={['admin']}><Dashboard /></Guard>} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/traffic" element={<Traffic />} />
        <Route path="/accident" element={<Accident />} />
        <Route path="/aqi" element={<AirQuality />} />
        <Route path="/electricity" element={<Electricity />} />
        <Route path="/water" element={<Water />} />
        <Route path="/waste" element={<Waste />} />
        <Route path="/complaints" element={<Complaints />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/reports" element={<Guard roles={['authority', 'admin']}><Reports /></Guard>} />
        <Route path="/admin/users" element={<Guard roles={['admin']}><Users /></Guard>} />
        <Route path="/admin/datasets" element={<Guard roles={['admin']}><Datasets /></Guard>} />
        <Route path="/admin/models" element={<Guard roles={['admin']}><Models /></Guard>} />
        <Route path="*" element={<Navigate to={HOME[user.role]} replace />} />
      </Route>
    </Routes>
  )
}

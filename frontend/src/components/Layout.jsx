import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Bell, BrainCircuit, Building2, ClipboardList, Database, Droplets, FileBarChart, Home, LayoutDashboard, LogOut, Map as MapIcon, Menu, Siren, Trash2, Users, Wind, X, Zap, Car } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Ambient } from './CityBackdrop'
import Assistant from './Assistant'
import { fmtTime, Badge } from '../ui'
import Credit from './Credit'

const NAV = [
  { group: 'Overview' },
  { to: '/home', label: 'My Area', icon: Home, roles: ['citizen'] },
  { to: '/department', label: 'Department', icon: Building2, roles: ['authority'] },
  { to: '/dashboard', label: 'Command Center', icon: LayoutDashboard, roles: ['admin'] },
  { to: '/map', label: 'City Map', icon: MapIcon, roles: ['citizen', 'authority', 'admin'] },
  { group: 'AI Predictions' },
  { to: '/traffic', label: 'Traffic', icon: Car, roles: ['citizen', 'authority', 'admin'] },
  { to: '/accident', label: 'Accident Risk', icon: Siren, roles: ['citizen', 'authority', 'admin'] },
  { to: '/aqi', label: 'Air Quality', icon: Wind, roles: ['citizen', 'authority', 'admin'] },
  { to: '/electricity', label: 'Electricity', icon: Zap, roles: ['citizen', 'authority', 'admin'] },
  { to: '/water', label: 'Water', icon: Droplets, roles: ['citizen', 'authority', 'admin'] },
  { to: '/waste', label: 'Waste', icon: Trash2, roles: ['citizen', 'authority', 'admin'] },
  { group: 'Citizen Services' },
  { to: '/complaints', label: 'Complaints', icon: ClipboardList, roles: ['citizen', 'authority', 'admin'] },
  { to: '/alerts', label: 'AI Alerts', icon: AlertTriangle, roles: ['citizen', 'authority', 'admin'] },
  { group: 'Administration' },
  { to: '/reports', label: 'Reports', icon: FileBarChart, roles: ['authority', 'admin'] },
  { to: '/admin/users', label: 'Users', icon: Users, roles: ['admin'] },
  { to: '/admin/datasets', label: 'Datasets', icon: Database, roles: ['admin'] },
  { to: '/admin/models', label: 'ML Models', icon: BrainCircuit, roles: ['admin'] },
]
const TITLES = {
  '/home': ['My Area', 'Live conditions where you live'], '/department': ['Department Portal', 'Your department at a glance'],
  '/dashboard': ['Command Center', 'City-wide intelligence at a glance'], '/map': ['Interactive City Map', 'Click any locality for live + predicted conditions'],
  '/traffic': ['Traffic Prediction', 'Hour-by-hour congestion forecast'], '/accident': ['Accident Risk', 'AI risk classification per locality'],
  '/aqi': ['Air Quality', 'CPCB AQI now and tomorrow'], '/electricity': ['Electricity Demand', 'City load forecast'],
  '/water': ['Water Consumption', 'Area-wise demand forecast'], '/waste': ['Waste Generation', 'Forecast + collection planning'],
  '/complaints': ['Citizen Complaints', 'NLP-powered categorisation and routing'], '/alerts': ['AI Alert Center', 'Predictions turned into action'],
  '/reports': ['Analytics & Reports', 'Daily · weekly · monthly · yearly'], '/admin/users': ['User Management', 'Roles and departments'],
  '/admin/datasets': ['Dataset Management', 'Import, export and ingest city data'], '/admin/models': ['ML Model Management', 'Train, compare and monitor models'],
}

function Bell_() {
  const [open, setOpen] = useState(false)
  const [data, setData] = useState({ notifications: [], unread: 0 })
  const ref = useRef(null)
  const load = () => api.get('/api/notifications').then(setData).catch(() => {})
  useEffect(() => { load(); const id = setInterval(load, 60000); return () => clearInterval(id) }, [])
  useEffect(() => {
    const h = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h)
  }, [])
  const toggle = () => { setOpen(!open); if (!open && data.unread) api.post('/api/notifications/read').then(() => setTimeout(load, 1500)) }
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button className="icon-btn" onClick={toggle}><Bell />{data.unread > 0 && <span className="dot">{data.unread}</span>}</button>
      <AnimatePresence>
        {open && (
          <motion.div className="drop" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--line)' }}><b>Notifications</b></div>
            <div style={{ maxHeight: 360, overflowY: 'auto' }}>
              {data.notifications.length === 0 && <div className="empty">You're all caught up ✨</div>}
              {data.notifications.map((n) => (
                <div key={n.id} className={`item ${n.is_read ? '' : 'unread'}`}>
                  <b>{n.title}</b><span className="mute">{n.message}</span><div className="dim" style={{ fontSize: 11, marginTop: 3 }}>{fmtTime(n.created_at)}</div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Ticker() {
  const [items, setItems] = useState([])
  useEffect(() => {
    const load = () => api.get('/api/alerts').then((r) => setItems(r.alerts.filter((a) => a.severity !== 'info').slice(0, 8))).catch(() => {})
    load(); const id = setInterval(load, 90000); return () => clearInterval(id)
  }, [])
  if (!items.length) return null
  const row = [...items, ...items]
  return (
    <div className="ticker"><div className="ticker-track">
      {row.map((a, i) => <span key={i} className={`ticker-item ${a.severity}`}>⚠ <b>{a.area}</b> {a.message}</span>)}
    </div></div>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const [menu, setMenu] = useState(false)
  const loc = useLocation()
  const nav = useNavigate()
  useEffect(() => setMenu(false), [loc.pathname])
  const [title, sub] = TITLES[loc.pathname] || ['Smart City', '']
  const items = NAV.filter((n) => n.group || n.roles.includes(user.role))
  // hide group headers that have no visible children
  const shown = items.filter((n, i) => !n.group || (items[i + 1] && !items[i + 1].group))

  return (
    <>
      <Ambient />
      <div className="shell">
        {menu && <div className="sidebar-backdrop" onClick={() => setMenu(false)} />}
        <aside className={`sidebar ${menu ? 'open' : ''}`}>
          <div className="brand">
            <div className="brand-mark">🏙️</div>
            <div><b>SMART CITY AI</b><span>Bengaluru</span></div>
            <button className="icon-btn sidebar-close" onClick={() => setMenu(false)}><X /></button>
          </div>
          {shown.map((n, i) => n.group
            ? <div key={i} className="nav-group">{n.group}</div>
            : <NavLink key={n.to} to={n.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><n.icon />{n.label}</NavLink>)}
          <div className="grow" />
          <div className="userbox">
            <div className="avatar">{user.name[0]}</div>
            <div className="who"><b>{user.name}</b><small>{user.role === 'authority' ? user.department?.name : user.role}</small></div>
            <button className="icon-btn" title="Sign out" onClick={() => { logout(); nav('/login', { replace: true }) }}><LogOut /></button>
          </div>
          <Credit />
        </aside>
        <div className="main">
          <div className="topbar">
            <button className="icon-btn menu-btn" onClick={() => setMenu(!menu)}><Menu /></button>
            <div className="title"><h1>{title}</h1><div className="sub">{sub}</div></div>
            <span className="live"><i />Live</span>
            <Bell_ />
          </div>
          <Ticker />
          <div className="content">
            <AnimatePresence mode="wait">
              <motion.div key={loc.pathname} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
      <Assistant />
    </>
  )
}

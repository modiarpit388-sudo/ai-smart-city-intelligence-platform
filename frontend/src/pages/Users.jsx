import { useState } from 'react'
import { UserPlus, Users as UsersIcon } from 'lucide-react'
import { api } from '../api'
import { Badge, ErrorBox, Loader, Modal, Panel, useAreas, useFetch } from '../ui'

export default function Users() {
  const { data, error, loading, reload } = useFetch('/api/admin/users')
  const areas = useAreas()
  const [show, setShow] = useState(false)
  const [f, setF] = useState({ name: '', email: '', password: '', role: 'authority', department_id: '' })
  const [err, setErr] = useState('')
  const [q, setQ] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const create = async () => {
    setErr('')
    try { await api.post('/api/admin/users', { ...f, department_id: f.department_id ? Number(f.department_id) : null }); setShow(false); setF({ name: '', email: '', password: '', role: 'authority', department_id: '' }); reload() }
    catch (e) { setErr(e.message) }
  }
  const toggle = async (u) => { await api.put(`/api/admin/users/${u.id}`, { is_active: !u.is_active }).catch((e) => alert(e.message)); reload() }
  if (error) return <ErrorBox error={error} retry={reload} />
  if (loading && !data) return <Loader />
  const users = data.users.filter((u) => (u.name + u.email + u.role).toLowerCase().includes(q.toLowerCase()))
  return (
    <>
      <Panel title={`Users (${data.users.length})`} icon={UsersIcon} flush right={<div className="row"><input className="input inp-search" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} /><button className="btn primary sm" onClick={() => setShow(true)}><UserPlus />Add user</button></div>}>
        <div className="table-wrap" style={{ padding: 8, maxHeight: 640, overflowY: 'auto' }}>
          <table className="t"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Department / Area</th><th>Status</th><th /></tr></thead>
            <tbody>{users.map((u) => (
              <tr key={u.id}><td>{u.name}</td><td className="mute">{u.email}</td>
                <td><Badge level={u.role === 'admin' ? 'critical' : u.role === 'authority' ? 'warning' : 'info'}>{u.role}</Badge></td>
                <td>{u.department?.name || u.area_name || '—'}</td><td><Badge level={u.is_active ? 'normal' : 'rejected'}>{u.is_active ? 'active' : 'disabled'}</Badge></td>
                <td className="right"><button className="btn sm" onClick={() => toggle(u)}>{u.is_active ? 'Disable' : 'Enable'}</button></td></tr>))}</tbody></table>
        </div>
      </Panel>
      {show && (
        <Modal onClose={() => setShow(false)}>
          <div className="stack">
            <h3>Add user</h3>
            <div className="field"><label>Name</label><input className="input" value={f.name} onChange={set('name')} /></div>
            <div className="field"><label>Email</label><input className="input" value={f.email} onChange={set('email')} /></div>
            <div className="field"><label>Password</label><input className="input" type="password" value={f.password} onChange={set('password')} />
              <span className="mute" style={{ fontSize: 12 }}>Min 8 characters with uppercase, lowercase, a digit and a special character.</span></div>
            <div className="grid g2"><div className="field"><label>Role</label><select className="input" value={f.role} onChange={set('role')}><option>authority</option><option>citizen</option><option>admin</option></select></div>
              {f.role === 'authority' && <div className="field"><label>Department</label><select className="input" value={f.department_id} onChange={set('department_id')}><option value="">Select…</option>{data.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>}</div>
            {err && <div className="err">{err}</div>}
            <div className="row"><button className="btn primary" onClick={create}>Create</button><button className="btn" onClick={() => setShow(false)}>Cancel</button></div>
          </div>
        </Modal>)}
    </>
  )
}

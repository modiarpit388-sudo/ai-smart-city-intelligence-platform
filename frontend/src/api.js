// Tiny fetch wrapper: adds the JWT, parses JSON, throws readable errors.
const KEY = 'scai_token'
export const getToken = () => localStorage.getItem(KEY)
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY))

async function request(method, path, body) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const res = await fetch(path, { method, headers, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined })
  if (res.status === 401 && token) {
    setToken(null)
    window.dispatchEvent(new Event('scai-logout'))
  }
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) {
    const err = new Error((data && data.error) || `Request failed (${res.status})`)
    err.status = res.status
    err.code = data && data.code
    throw err
  }
  return data
}

export const api = {
  get: (p) => request('GET', p),
  post: (p, b) => request('POST', p, b ?? {}),
  put: (p, b) => request('PUT', p, b ?? {}),
  // download a protected file (CSV) using the auth header
  async download(path, filename) {
    const res = await fetch(path, { headers: { Authorization: `Bearer ${getToken()}` } })
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  },
}

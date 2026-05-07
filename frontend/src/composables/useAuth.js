import { reactive, ref } from 'vue'

const token = ref(localStorage.getItem('token') || '')
const user = reactive(JSON.parse(localStorage.getItem('user') || 'null') || { username: '', email: '' })

async function api(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  if (token.value) headers['Authorization'] = 'Bearer ' + token.value
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (!res.ok) {
    const e = await res.json().catch(() => ({}))
    throw new Error(e.detail || '请求失败')
  }
  return res.json()
}

async function login(email, password) {
  const r = await api('POST', '/api/token', { email, password })
  token.value = r.access_token
  localStorage.setItem('token', token.value)
  const me = await api('GET', '/api/users/me')
  Object.assign(user, me)
  localStorage.setItem('user', JSON.stringify(user))
}

async function register(username, email, password) {
  await api('POST', '/api/register', { username, email, password })
}

function logout() {
  token.value = ''
  Object.keys(user).forEach(k => delete user[k])
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export function useAuth() {
  return { token, user, api, login, register, logout }
}

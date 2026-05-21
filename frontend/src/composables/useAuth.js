import { ref, computed } from 'vue'

// 模块级共享状态 — 全局唯一
const _TOKEN_KEY = 'lingxi_token'
const _USER_KEY = 'lingxi_user'

const token = ref(localStorage.getItem(_TOKEN_KEY) || '')
const user = ref(JSON.parse(localStorage.getItem(_USER_KEY) || 'null'))

async function sha256(text) {
  const buf = new TextEncoder().encode(text)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

function _persist() {
  if (token.value) localStorage.setItem(_TOKEN_KEY, token.value)
  else localStorage.removeItem(_TOKEN_KEY)
  if (user.value) localStorage.setItem(_USER_KEY, JSON.stringify(user.value))
  else localStorage.removeItem(_USER_KEY)
}

export function useAuth() {
  const isAuthed = computed(() => !!token.value && !!user.value)

  async function login(email, password) {
    const hashed = await sha256(password)
    const res = await fetch('/api/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: hashed }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '邮箱或密码错误')
    }
    const { access_token } = await res.json()
    token.value = access_token

    // 拉取用户信息
    const meRes = await fetch('/api/users/me', {
      headers: { Authorization: `Bearer ${access_token}` },
    })
    if (!meRes.ok) {
      token.value = ''
      throw new Error('登录失败：无法获取用户信息')
    }
    user.value = await meRes.json()
    _persist()

    // 恢复最近一条对话的 thread_id 到 localStorage,让 useChat 能继续上次对话
    try {
      const latestRes = await fetch('/api/conversations/latest', {
        headers: { Authorization: `Bearer ${access_token}` },
      })
      if (latestRes.ok) {
        const latest = await latestRes.json()
        if (latest.thread_id) {
          localStorage.setItem('lingxi_conversation_id', latest.thread_id)
          localStorage.setItem('lingxi_conversation_ts', String(Date.now()))
        }
      }
    } catch {
      // 静默失败 — 登录本身已成功,会话恢复失败可以下次再说
    }
  }

  async function register(username, email, password) {
    const hashed = await sha256(password)
    const res = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password: hashed }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '注册失败')
    }
    // 注册成功后自动登录
    await login(email, password)
  }

  function logout() {
    token.value = ''
    user.value = null
    _persist()
    // 顺带清理对话残留
    localStorage.removeItem('lingxi_conversation_id')
    localStorage.removeItem('lingxi_conversation_ts')
  }

  async function validate() {
    if (!token.value) return false
    try {
      const res = await fetch('/api/validate-token', {
        headers: { Authorization: `Bearer ${token.value}` },
      })
      if (!res.ok) {
        logout()
        return false
      }
      const data = await res.json()
      if (data.valid && data.user) {
        user.value = data.user
        _persist()
      }
      return data.valid === true
    } catch {
      return false
    }
  }

  return { token, user, isAuthed, login, register, logout, validate }
}

import { ref } from 'vue'
import { useAuth } from '@/composables/useAuth.js'

// Module-level shared state — survives page switches
const messages = ref([])
const isLoading = ref(false)
const statusText = ref('')
const _CONV_KEY = 'lingxi_conversation_id'
const _CONV_TS_KEY = 'lingxi_conversation_ts'
const _TTL_MS = 24 * 60 * 60 * 1000  // 24 小时无活动后自动开新会话

const _lastTs = localStorage.getItem(_CONV_TS_KEY)
let conversationId = (_lastTs && Date.now() - Number(_lastTs) < _TTL_MS)
  ? localStorage.getItem(_CONV_KEY)
  : null
if (!conversationId) {
  localStorage.removeItem(_CONV_KEY)
  localStorage.removeItem(_CONV_TS_KEY)
}

export function useChat() {
  const { user, token } = useAuth()

  function addMessage(role, content) {
    messages.value.push({ role, content, id: Date.now() + Math.random() })
  }

  async function sendMessage(query) {
    if (!query.trim() || isLoading.value) return
    const userId = user.value?.id
    if (!userId) {
      addMessage('assistant', '请先登录后再发起对话～')
      return
    }
    addMessage('user', query)
    isLoading.value = true
    statusText.value = ''

    const formData = new FormData()
    formData.append('query', query)
    formData.append('user_id', userId)
    if (conversationId) formData.append('conversation_id', conversationId)

    try {
      const headers = token.value ? { Authorization: `Bearer ${token.value}` } : {}
      const response = await fetch('/api/langgraph/query', { method: 'POST', body: formData, headers })
      const newConvId = response.headers.get('X-Conversation-ID')
      if (newConvId) {
        conversationId = newConvId
        localStorage.setItem(_CONV_KEY, newConvId)
        localStorage.setItem(_CONV_TS_KEY, String(Date.now()))
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let assistantMessage = ''

      addMessage('assistant', '')
      const msgIndex = messages.value.length - 1

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)
            if (typeof parsed === 'string') {
              assistantMessage += parsed
              messages.value[msgIndex].content = assistantMessage
            } else if (parsed.status === 'progress') {
              statusText.value = parsed.msg
            } else if (parsed.status === 'done') {
              statusText.value = ''
            }
          } catch {
            assistantMessage += data
            messages.value[msgIndex].content = assistantMessage
          }
        }
      }
    } catch {
      addMessage('assistant', '抱歉，系统暂时无法响应，请稍后再试～')
    } finally {
      isLoading.value = false
      statusText.value = ''
    }
  }

  function clearMessages() {
    messages.value = []
    conversationId = null
    localStorage.removeItem(_CONV_KEY)
    localStorage.removeItem(_CONV_TS_KEY)
  }

  async function loadHistory() {
    // 从 localStorage 拿 thread_id,从后端拉消息回填 messages
    const tid = localStorage.getItem(_CONV_KEY)
    if (!tid || !token.value) return
    try {
      const res = await fetch(`/api/conversations/by-thread/${tid}/messages`, {
        headers: { Authorization: `Bearer ${token.value}` },
      })
      if (!res.ok) {
        // 404: 这条 thread 在后端已经不存在了 (DB 被清等),清掉 localStorage
        if (res.status === 404) {
          localStorage.removeItem(_CONV_KEY)
          localStorage.removeItem(_CONV_TS_KEY)
          conversationId = null
        }
        return
      }
      const rows = await res.json()
      conversationId = tid  // 与 localStorage 同步
      messages.value = rows.map(r => ({
        role: r.sender === 'user' ? 'user' : 'assistant',
        content: r.content,
        id: r.id,
      }))
    } catch {
      // 网络错误等,静默
    }
  }

  async function listConversations() {
    // 拉当前用户的所有历史会话
    if (!token.value) return []
    try {
      const res = await fetch('/api/conversations/mine', {
        headers: { Authorization: `Bearer ${token.value}` },
      })
      if (!res.ok) return []
      return await res.json()
    } catch {
      return []
    }
  }

  async function switchTo(threadId) {
    // 切换到指定 thread_id 并拉历史消息
    if (!threadId || !token.value || isLoading.value) return
    try {
      const res = await fetch(`/api/conversations/by-thread/${threadId}/messages`, {
        headers: { Authorization: `Bearer ${token.value}` },
      })
      if (!res.ok) return
      const rows = await res.json()
      conversationId = threadId
      localStorage.setItem(_CONV_KEY, threadId)
      localStorage.setItem(_CONV_TS_KEY, String(Date.now()))
      messages.value = rows.map(r => ({
        role: r.sender === 'user' ? 'user' : 'assistant',
        content: r.content,
        id: r.id,
      }))
    } catch {
      // 静默
    }
  }

  async function deleteConversation(threadId) {
    // 删除指定 thread_id 的会话。如果删的是当前会话,顺手 clearMessages。
    if (!threadId || !token.value) return false
    try {
      const res = await fetch(`/api/conversations/by-thread/${threadId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token.value}` },
      })
      if (!res.ok) return false
      if (threadId === conversationId) {
        clearMessages()
      }
      return true
    } catch {
      return false
    }
  }

  return {
    messages, isLoading, statusText,
    sendMessage, clearMessages, loadHistory,
    listConversations, switchTo, deleteConversation,
  }
}

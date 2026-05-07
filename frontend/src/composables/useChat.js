import { ref, reactive } from 'vue'

const messages = ref([])
const streaming = ref(false)
const conversationId = ref(null)
const chatInput = ref(null)

function fmt(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function esc(text) {
  return (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

async function sendMessage(query, userId, imageFile) {
  if (!query || streaming.value) return
  streaming.value = true

  const displayText = imageFile ? `[图片] ${query}` : query
  messages.value.push({ role: 'user', content: displayText, hasImage: !!imageFile })

  const aiMsg = reactive({ role: 'assistant', content: '', typing: true })
  messages.value.push(aiMsg)

  try {
    const fd = new FormData()
    fd.append('query', query)
    fd.append('user_id', userId || 1)
    if (conversationId.value) fd.append('conversation_id', conversationId.value)
    if (imageFile) fd.append('image', imageFile)

    const res = await fetch('/api/langgraph/query', { method: 'POST', body: fd })
    conversationId.value = res.headers.get('X-Conversation-ID') || conversationId.value

    if (!res.ok) {
      const errText = await res.text()
      throw new Error(`HTTP ${res.status}: ${errText}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = '', raw = ''
    // 保持 typing 状态直到有实际内容
    aiMsg.typing = true
    aiMsg.content = '对方正在输入...'

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() || ''
      for (const l of lines) {
        if (!l.startsWith('data: ')) continue
        const d = l.slice(6).trim()
        if (!d) continue
        try {
          const p = JSON.parse(d)
          // 状态事件：显示思考中提示
          if (typeof p === 'object' && p.status === 'thinking') {
            aiMsg.content = p.msg || '对方正在输入...'
            continue
          }
          if (typeof p === 'string') {
            if (!raw) aiMsg.typing = false  // 第一个字符到，关闭打字动画
            raw += p
            aiMsg.content = fmt(raw)
          }
        } catch {
          if (!raw) aiMsg.typing = false
          raw += d.replace(/^"|"$/g, '')
          aiMsg.content = fmt(raw)
        }
      }
    }
    aiMsg.typing = false
    if (!raw.trim()) {
      aiMsg.content = '收到空回复，请重试。'
    }
  } catch (e) {
    console.error('[sendMessage] error:', e)
    aiMsg.content = '抱歉，出了点问题，请重试。'
    aiMsg.typing = false
  }

  streaming.value = false
}

function closeChat() {
  conversationId.value = null
  messages.value = []
}

export function useChat() {
  return { messages, streaming, conversationId, chatInput, sendMessage, closeChat, fmt, esc }
}

import { ref } from 'vue'

export function useChat() {
  const messages = ref([])
  const isLoading = ref(false)
  const statusText = ref('')
  let conversationId = null

  function addMessage(role, content) {
    messages.value.push({ role, content, id: Date.now() + Math.random() })
  }

  async function sendMessage(query, userId = 1) {
    if (!query.trim() || isLoading.value) return
    addMessage('user', query)
    isLoading.value = true
    statusText.value = ''

    const formData = new FormData()
    formData.append('query', query)
    formData.append('user_id', userId)
    if (conversationId) formData.append('conversation_id', conversationId)

    try {
      const response = await fetch('/api/langgraph/query', { method: 'POST', body: formData })
      conversationId = response.headers.get('X-Conversation-ID') || conversationId

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
  }

  return { messages, isLoading, statusText, sendMessage, clearMessages }
}

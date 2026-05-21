<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useChat } from '@/composables/useChat.js'
import { useAuth } from '@/composables/useAuth.js'

const router  = useRouter()
const route   = useRoute()
const {
  messages, isLoading, statusText,
  sendMessage, clearMessages, loadHistory,
  listConversations, switchTo, deleteConversation,
} = useChat()
const { user, logout } = useAuth()
const inputText  = ref('')
const chatBody   = ref(null)
const historyOpen = ref(false)
const historyList = ref([])
const historyLoading = ref(false)

function goBack() { router.push('/') }
function handleLogout() {
  logout()
  router.push({ name: 'login' })
}
function handleNewChat() {
  if (isLoading.value) return
  clearMessages()
  historyOpen.value = false
}

async function openHistory() {
  historyOpen.value = true
  historyLoading.value = true
  historyList.value = await listConversations()
  historyLoading.value = false
}

async function pickHistory(item) {
  if (isLoading.value) return
  await switchTo(item.thread_id)
  historyOpen.value = false
  await nextTick()
  scrollBottom()
}

async function removeHistory(item, e) {
  e.stopPropagation()
  if (!confirm(`删除「${item.title}」?\n该会话的所有消息将一并删除。`)) return
  const ok = await deleteConversation(item.thread_id)
  if (ok) historyList.value = historyList.value.filter(x => x.thread_id !== item.thread_id)
}

function formatHistoryTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) {
    return d.toTimeString().slice(0, 5)
  }
  const sameYear = d.getFullYear() === now.getFullYear()
  return sameYear
    ? `${d.getMonth() + 1}月${d.getDate()}日`
    : `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
}

async function handleSend() {
  if (!inputText.value.trim() || isLoading.value) return
  const text = inputText.value
  inputText.value = ''
  await sendMessage(text)
  await nextTick()
  scrollBottom()
}

function scrollBottom() {
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
}

function formatContent(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<span class="md-li">• $1</span>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>')
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
}

onMounted(async () => {
  // 如果当前页面没有消息,但 localStorage 有 conversation_id,先回填历史
  if (messages.value.length === 0) {
    await loadHistory()
    await nextTick()
    scrollBottom()
  }

  const q = route.query.q
  if (q && typeof q === 'string' && q.trim()) {
    inputText.value = q.trim()
    nextTick(handleSend)
  }
})

watch(messages, () => nextTick(scrollBottom), { deep: true })
</script>

<template>
  <div class="chat-page">
    <!-- Header -->
    <div class="chat-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5m7-7-7 7 7 7"/>
        </svg>
        商城
      </button>

      <div class="header-center">
        <span class="brand-mark">
          <span class="brand-dot" />
        </span>
        <div class="header-meta">
          <div class="header-title">灵犀客服</div>
          <div class="header-sub">
            <span class="status-dot" />
            AI · 在线
          </div>
        </div>
      </div>

      <div class="header-right">
        <button class="icon-btn" @click="openHistory" title="历史会话">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        </button>
        <button class="icon-btn" @click="handleNewChat" title="新对话" :disabled="isLoading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
          </svg>
        </button>
        <span v-if="user" class="user-chip" :title="user.email">
          {{ user.username }}
        </span>
        <button class="icon-btn" @click="handleLogout" title="退出登录">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- History drawer -->
    <transition name="drawer">
      <div v-if="historyOpen" class="history-overlay" @click="historyOpen = false">
        <aside class="history-drawer" @click.stop>
          <div class="history-head">
            <div class="history-title">历史会话</div>
            <button class="icon-btn" @click="historyOpen = false" title="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <div class="history-body">
            <div v-if="historyLoading" class="history-empty">加载中…</div>
            <div v-else-if="historyList.length === 0" class="history-empty">
              <div class="history-empty-icon">○</div>
              <div>还没有历史会话</div>
              <div class="history-empty-sub">发个消息试试</div>
            </div>
            <button
              v-for="item in historyList"
              :key="item.thread_id"
              class="history-item"
              @click="pickHistory(item)"
            >
              <div class="history-item-main">
                <div class="history-item-title">{{ item.title }}</div>
                <div class="history-item-preview">{{ item.preview }}</div>
              </div>
              <div class="history-item-side">
                <span class="history-item-time">{{ formatHistoryTime(item.updated_at) }}</span>
                <span class="history-del" @click="(e) => removeHistory(item, e)" title="删除">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </span>
              </div>
            </button>
          </div>
        </aside>
      </div>
    </transition>

    <!-- Messages -->
    <div class="chat-body" ref="chatBody">
      <div class="chat-inner">

        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-orb">
            <div class="orb-core">◎</div>
            <div class="orb-ring" />
          </div>
          <h3 class="welcome-title font-display">你好，我是灵犀</h3>
          <p class="welcome-sub">可以帮你找产品 · 比价格 · 查库存 · 解决售后</p>
          <div class="welcome-tips">
            <span
              v-for="tip in ['推荐旗舰手机', '查询我的订单', '退货政策', '5000以内笔记本']"
              :key="tip"
              class="welcome-tip"
              @click="() => { inputText = tip; handleSend() }"
            >{{ tip }}</span>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
          <div class="msg-avatar">
            <template v-if="msg.role === 'assistant'">
              <span class="ai-mark">◎</span>
            </template>
            <template v-else>我</template>
          </div>
          <div class="msg-bubble">
            <template v-if="!msg.content && msg.role === 'assistant'">
              <span class="thinking"><i /><i /><i /></span>
            </template>
            <div v-else v-html="formatContent(msg.content)" />
          </div>
        </div>

        <div v-if="statusText" class="status-text">
          <span class="status-spinner" />
          {{ statusText }}
        </div>
      </div>
    </div>

    <!-- Input bar -->
    <div class="input-bar">
      <div class="input-inner">
        <input
          type="text"
          v-model="inputText"
          placeholder="请输入您要咨询的问题..."
          @keydown="onKeydown"
          :disabled="isLoading"
        />
        <button
          class="send-btn"
          :class="{ active: inputText.trim() && !isLoading }"
          @click="handleSend"
          :disabled="isLoading || !inputText.trim()"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.font-display { font-family: var(--display); font-variation-settings: 'opsz' 72; letter-spacing: -0.03em; }

.chat-page {
  position: fixed; inset: 0; z-index: 100;
  background: #000;
  display: flex; flex-direction: column;
}

/* Header */
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 64px;
  background: rgba(0, 0, 0, 0.75);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(20px);
  flex-shrink: 0;
}
.back-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 13px; border-radius: 999px;
  font-size: 13px; font-weight: 500; color: var(--text-mute);
  transition: all 0.2s;
}
.back-btn:hover { color: var(--text-soft); background: rgba(255,255,255,0.04); }
.back-btn svg { width: 14px; height: 14px; }

.header-center {
  display: flex; align-items: center; gap: 12px;
}
.brand-mark {
  width: 36px; height: 36px; border-radius: 11px;
  background: linear-gradient(135deg, #18181B 0%, #2A2A2E 100%);
  border: 1px solid rgba(232, 180, 168, 0.4);
  display: grid; place-items: center;
  box-shadow: inset 0 0 12px rgba(232, 180, 168, 0.25);
}
.brand-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  animation: dot-pulse 2s ease-out infinite;
}
.header-meta { display: flex; flex-direction: column; }
.header-title {
  font-family: var(--display);
  font-size: 15px; font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
}
.header-sub {
  font-size: 11px; color: var(--coral);
  font-weight: 500;
  display: flex; align-items: center; gap: 5px;
}
.status-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #34D399;
  box-shadow: 0 0 6px #34D399;
}
.header-right {
  display: flex; align-items: center; gap: 8px;
  min-width: 120px; justify-content: flex-end;
}
.user-chip {
  font-size: 12px; font-weight: 600;
  color: var(--text-soft);
  padding: 6px 12px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 999px;
  max-width: 120px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap;
}
.icon-btn {
  display: grid; place-items: center;
  width: 32px; height: 32px; border-radius: 10px;
  color: var(--text-mute);
  transition: all 0.2s;
}
.icon-btn:hover:not(:disabled) {
  color: var(--coral);
  background: rgba(232, 180, 168, 0.08);
}
.icon-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.icon-btn svg { width: 16px; height: 16px; }

/* Messages */
.chat-body { flex: 1; overflow-y: auto; }
.chat-inner { max-width: 760px; margin: 0 auto; padding: 32px 24px; }

.welcome {
  text-align: center;
  padding: 80px 20px 60px;
  animation: rise 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.welcome-orb {
  position: relative;
  width: 80px; height: 80px;
  margin: 0 auto 24px;
}
.orb-core {
  position: relative;
  z-index: 2;
  width: 100%; height: 100%;
  border-radius: 22px;
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  display: grid; place-items: center;
  color: #000;
  font-family: var(--display);
  font-size: 38px;
  font-weight: 800;
  box-shadow: 0 16px 40px rgba(232,180,168,0.35), inset 0 1px 0 rgba(255,255,255,0.2);
}
.orb-ring {
  position: absolute;
  inset: -8px;
  border-radius: 28px;
  border: 1.5px solid rgba(232, 180, 168, 0.4);
  animation: dot-pulse 2.5s ease-out infinite;
}
.welcome-title {
  font-size: 28px; font-weight: 700;
  color: var(--text);
  margin-bottom: 10px;
}
.welcome-sub {
  font-size: 14px; color: var(--text-mute);
  line-height: 1.7;
  margin-bottom: 28px;
}
.welcome-tips { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
.welcome-tip {
  padding: 7px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-hi);
  border-radius: 999px;
  font-size: 12px; font-weight: 500;
  color: var(--text-soft);
  cursor: pointer; transition: all 0.2s;
}
.welcome-tip:hover {
  background: rgba(232, 180, 168, 0.10);
  border-color: rgba(232, 180, 168, 0.4);
  color: var(--coral);
}

.msg {
  display: flex; gap: 12px; margin-bottom: 18px;
  animation: rise 0.4s ease forwards;
}
.msg.user { flex-direction: row-reverse; }

.msg-avatar {
  width: 36px; height: 36px; border-radius: 11px; flex-shrink: 0;
  display: grid; place-items: center;
  font-size: 13px; font-weight: 700;
}
.msg.assistant .msg-avatar {
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  color: #000;
  box-shadow: 0 4px 12px rgba(232,180,168,0.3);
}
.msg.assistant .ai-mark {
  font-family: var(--display);
  font-size: 18px; font-weight: 800;
}
.msg.user .msg-avatar {
  background: rgba(255,255,255,0.05);
  color: var(--text-mute);
  border: 1px solid var(--border);
}

.msg-bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.msg.assistant .msg-bubble {
  background: linear-gradient(135deg, rgba(20,20,22,0.7), rgba(14,14,16,0.5));
  border: 1px solid var(--border-hi);
  color: var(--text-soft);
}
.msg.user .msg-bubble {
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border-hi);
  color: var(--text);
}

.thinking {
  display: inline-flex; gap: 4px; align-items: center; height: 20px;
}
.thinking i {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--coral); animation: dot-cycle 1.4s infinite;
}
.thinking i:nth-child(2) { animation-delay: .2s; }
.thinking i:nth-child(3) { animation-delay: .4s; }
@keyframes dot-cycle {
  0%,60%,100% { opacity: .2; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

.status-text {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-mute);
  padding: 4px 0;
  font-family: var(--mono);
}
.status-spinner {
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid rgba(232,180,168,0.2);
  border-top-color: var(--coral);
  animation: spin 0.8s linear infinite;
}

/* Input */
.input-bar {
  padding: 16px 24px 24px;
  background: rgba(0, 0, 0, 0.75);
  border-top: 1px solid var(--border);
  backdrop-filter: blur(20px);
  flex-shrink: 0;
}
.input-inner {
  max-width: 760px; margin: 0 auto;
  display: flex; gap: 10px; align-items: center;
}
.input-inner input {
  flex: 1; height: 50px; padding: 0 20px;
  background: rgba(255,255,255,0.035);
  border: 1px solid var(--border-hi);
  border-radius: 999px;
  color: var(--text); font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-inner input:focus {
  outline: none;
  border-color: rgba(232, 180, 168, 0.55);
  box-shadow: 0 0 0 4px rgba(232, 180, 168, 0.10);
}
.input-inner input::placeholder { color: var(--text-faint); }
.input-inner input:disabled { opacity: 0.5; }

.send-btn {
  width: 50px; height: 50px; border-radius: 50%; flex-shrink: 0;
  display: grid; place-items: center;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border-hi);
  transition: all 0.2s;
}
.send-btn svg { width: 18px; height: 18px; color: var(--text-mute); transition: color 0.2s; }
.send-btn.active {
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  border-color: transparent;
  box-shadow: 0 8px 24px rgba(232,180,168,0.4);
}
.send-btn.active svg { color: #000; }
.send-btn.active:hover { transform: translateY(-2px); }
.send-btn:disabled { cursor: not-allowed; }

/* History drawer */
.history-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
}
.history-drawer {
  width: 360px; max-width: 88vw;
  height: 100%;
  background: linear-gradient(180deg, #0c0c0e 0%, #050505 100%);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  box-shadow: 4px 0 32px rgba(0, 0, 0, 0.6);
}
.history-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
}
.history-title {
  font-family: var(--display);
  font-size: 16px; font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
}
.history-body {
  flex: 1; overflow-y: auto;
  padding: 8px 12px 16px;
}
.history-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-mute);
  font-size: 13px;
}
.history-empty-icon {
  font-size: 36px; color: var(--coral);
  opacity: 0.4; margin-bottom: 14px;
}
.history-empty-sub {
  font-size: 11px;
  color: var(--text-faint);
  margin-top: 6px;
}
.history-item {
  display: flex; align-items: flex-start; gap: 10px;
  width: 100%;
  padding: 12px 12px;
  border-radius: 12px;
  background: transparent;
  border: 1px solid transparent;
  margin-bottom: 4px;
  text-align: left;
  cursor: pointer;
  transition: all 0.18s;
}
.history-item:hover {
  background: rgba(232, 180, 168, 0.06);
  border-color: rgba(232, 180, 168, 0.18);
}
.history-item-main {
  flex: 1; min-width: 0;
}
.history-item-title {
  font-size: 13px; font-weight: 600;
  color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 4px;
}
.history-item-preview {
  font-size: 11.5px; color: var(--text-mute);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  line-height: 1.5;
}
.history-item-side {
  display: flex; flex-direction: column; align-items: flex-end; gap: 6px;
  flex-shrink: 0;
}
.history-item-time {
  font-size: 10.5px;
  color: var(--text-faint);
  font-family: var(--mono);
}
.history-del {
  display: grid; place-items: center;
  width: 24px; height: 24px; border-radius: 7px;
  color: var(--text-faint);
  opacity: 0; transition: all 0.18s;
}
.history-item:hover .history-del { opacity: 1; }
.history-del:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}
.history-del svg { width: 13px; height: 13px; }

.drawer-enter-from .history-drawer,
.drawer-leave-to   .history-drawer {
  transform: translateX(-100%);
}
.drawer-enter-from,
.drawer-leave-to {
  background: rgba(0, 0, 0, 0);
  backdrop-filter: blur(0);
}
.history-drawer { transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1); }
.history-overlay { transition: background 0.28s, backdrop-filter 0.28s; }

:deep(.md-li) { display: block; margin: 4px 0; }
:deep(strong) { font-weight: 700; color: var(--text); }
</style>

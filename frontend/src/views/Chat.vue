<script setup>
import { ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useChat } from '@/composables/useChat.js'
import { Motion, AnimatePresence } from 'motion-v'

const router = useRouter()
const { messages, isLoading, statusText, sendMessage, clearMessages } = useChat()
const inputText = ref('')
const msgContainer = ref(null)

function goBack() { router.push('/') }

async function handleSend() {
  if (!inputText.value.trim() || isLoading.value) return
  const text = inputText.value
  inputText.value = ''
  await sendMessage(text)
  await nextTick()
  scrollDown()
}

function scrollDown() {
  if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
}

watch(messages, () => nextTick(scrollDown), { deep: true })

const suggestions = [
  { emoji: '💻', text: '推荐一款适合办公的笔记本' },
  { emoji: '🎧', text: '2000元以内最好的耳机' },
  { emoji: '📱', text: 'iPhone 和华为怎么选' },
  { emoji: '🔧', text: '怎么申请售后服务' },
]
</script>

<template>
  <div class="flex h-screen flex-col bg-[#050508]">
    <!-- Header -->
    <header class="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4 shrink-0">
      <button
        @click="goBack"
        class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-neutral-400 hover:bg-white/[0.05] hover:text-white transition"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        商城
      </button>

      <div class="flex-1 text-center">
        <h1 class="text-sm font-semibold">灵犀智购 · AI 客服</h1>
      </div>

      <div class="flex items-center gap-2">
        <span class="relative flex h-2 w-2">
          <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span class="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
        </span>
        <span class="text-xs text-neutral-500">在线</span>
      </div>
    </header>

    <!-- Messages -->
    <div ref="msgContainer" class="flex-1 overflow-y-auto px-5 py-6">
      <div v-if="messages.length === 0" class="flex h-full flex-col items-center justify-center">
        <div class="mb-6 text-center">
          <div class="mb-4 flex justify-center">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-purple-500/20">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-purple-400">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
          </div>
          <h2 class="mb-2 text-lg font-semibold">您好，欢迎咨询</h2>
          <p class="text-sm text-neutral-500">我是灵犀智购 AI 助手，可以帮您选购电子产品、查询订单、处理售后</p>
        </div>

        <div class="grid w-full max-w-md grid-cols-1 gap-2">
          <button
            v-for="s in suggestions" :key="s.text"
            class="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 text-left text-sm text-neutral-400 hover:bg-white/[0.05] hover:text-white hover:border-white/[0.12] transition"
            @click="inputText = s.text; handleSend()"
          >
            <span class="mr-2">{{ s.emoji }}</span>{{ s.text }}
          </button>
        </div>
      </div>

      <div v-else class="mx-auto max-w-2xl space-y-6">
        <div v-for="msg in messages" :key="msg.id">
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="max-w-[75%] rounded-2xl rounded-br-md bg-purple-600/20 px-4 py-3 text-sm text-white border border-purple-500/20">
              {{ msg.content }}
            </div>
          </div>
          <div v-else class="flex gap-3">
            <div class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-blue-600 text-[11px] font-semibold">AI</div>
            <div class="max-w-[75%]">
              <div v-if="msg.content" class="rounded-2xl rounded-bl-md bg-white/[0.03] px-4 py-3 text-sm leading-relaxed text-neutral-200 border border-white/[0.04]">
                {{ msg.content }}
              </div>
              <div v-else class="flex gap-1.5 px-4 py-3">
                <span class="h-2 w-2 animate-bounce rounded-full bg-purple-500/60" />
                <span class="h-2 w-2 animate-bounce rounded-full bg-purple-500/60" style="animation-delay:0.15s" />
                <span class="h-2 w-2 animate-bounce rounded-full bg-purple-500/60" style="animation-delay:0.3s" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="border-t border-white/[0.06] px-5 py-4 shrink-0">
      <div class="mx-auto flex max-w-2xl items-end gap-2">
        <textarea
          v-model="inputText"
          :disabled="isLoading"
          placeholder="输入您的问题..."
          rows="1"
          class="flex-1 resize-none rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white placeholder:text-neutral-600 focus:border-purple-500/40 focus:outline-none focus:ring-1 focus:ring-purple-500/20 disabled:opacity-50"
          @keydown="onKeydown"
        />
        <button
          :disabled="isLoading || !inputText.trim()"
          class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 text-white transition hover:shadow-[0_0_20px_rgba(108,92,231,0.4)] active:scale-95 disabled:opacity-40 disabled:shadow-none"
          @click="handleSend"
        >
          <svg v-if="!isLoading" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          <svg v-else class="animate-spin" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

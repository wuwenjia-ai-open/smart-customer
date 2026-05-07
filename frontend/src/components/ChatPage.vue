<template>
  <div :class="['chat-page', { open: show }]">
    <div class="chat-top">
      <button class="back-btn" @click="$emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5m7-7l-7 7 7 7"/>
        </svg>
        返回商城
      </button>
      <div class="chat-logo"><span class="live-dot"></span>灵犀客服</div>
    </div>
    <div class="chat-body" ref="chatBody">
      <div class="chat-body-inner">
        <div v-if="messages.length === 0" class="chat-welcome">
          <div class="cw-icon">🛍️</div>
          <h3>你好，我是灵犀客服</h3>
          <p>可以帮你找产品、比价格、查库存、解决售后问题。随便问～</p>
        </div>
        <ChatMessage
          v-for="(msg, i) in messages" :key="i"
          :msg="msg" :userInitial="userInitial"
        />
      </div>
    </div>
    <div class="chat-input-bar">
      <div class="chat-input-inner">
        <label class="img-upload-btn" title="上传图片分析">
          <input type="file" accept="image/*" @change="onImagePick" :disabled="streaming" hidden>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
        </label>
        <input
          ref="chatInputRef"
          type="text"
          v-model="inputText"
          placeholder="请输入您要咨询的问题"
          @keydown.enter="handleSend"
          :disabled="streaming"
        >
        <button @click="handleSend" :disabled="streaming || (!inputText.trim() && !pickedImage)" :class="{ 'has-img': pickedImage }">发送</button>
      </div>
      <div v-if="pickedImage" class="img-preview">
        <img :src="pickedImage.src" :alt="pickedImage.name">
        <button class="img-clear" @click="pickedImage = null">&times;</button>
        <span class="img-name">{{ pickedImage.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'
import { useChat } from '../composables/useChat.js'
import { useAuth } from '../composables/useAuth.js'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['close'])

const { messages, streaming, chatInput, sendMessage, closeChat } = useChat()
const { user } = useAuth()

const inputText = ref('')
const pickedImage = ref(null)
const chatInputRef = ref(null)
const chatBody = ref(null)

const userInitial = computed(() => (user.username || user.email || '?').charAt(0).toUpperCase())

function onImagePick(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    pickedImage.value = { file, src: ev.target.result, name: file.name }
  }
  reader.readAsDataURL(file)
}

async function handleSend() {
  const q = inputText.value.trim()
  const img = pickedImage.value
  if ((!q && !img) || streaming.value) return
  inputText.value = ''
  pickedImage.value = null
  await sendMessage(q || '请分析这张图片', user.id || 1, img?.file)
  await nextTick()
  scrollBottom()
}

function scrollBottom() {
  if (chatBody.value) {
    chatBody.value.scrollTop = chatBody.value.scrollHeight
  }
}

function handleClose() {
  closeChat()
  emit('close')
}

watch(() => props.show, (v) => {
  if (v) {
    nextTick(() => chatInputRef.value?.focus())
  }
})

watch(() => messages.value.length, () => {
  nextTick(() => scrollBottom())
})
</script>

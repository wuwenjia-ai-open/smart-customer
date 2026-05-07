<template>
  <LoginPage v-if="currentView === 'login'" @loginSuccess="onLoginSuccess" />
  <template v-else>
    <AppShell @openChat="showChat = true" />
    <ChatPage :show="showChat" @close="showChat = false" />
  </template>
  <div :class="['toast', { show: toastShow }]">{{ toastMsg }}</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LoginPage from './components/LoginPage.vue'
import AppShell from './components/AppShell.vue'
import ChatPage from './components/ChatPage.vue'
import { useAuth } from './composables/useAuth.js'

const { token, api } = useAuth()

const currentView = ref('login')
const showChat = ref(false)
const toastMsg = ref('')
const toastShow = ref(false)

function showToast(msg) {
  toastMsg.value = msg
  toastShow.value = true
  setTimeout(() => { toastShow.value = false }, 3000)
}

async function onLoginSuccess() {
  currentView.value = 'app'
}

async function checkToken() {
  if (!token.value) return
  try {
    await api('GET', '/api/validate-token')
    currentView.value = 'app'
  } catch {
    token.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }
}

onMounted(() => checkToken())
</script>

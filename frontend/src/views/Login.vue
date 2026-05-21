<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth.js'

const router = useRouter()
const route = useRoute()
const { login, register } = useAuth()

const mode = ref('login')  // 'login' | 'register'
const username = ref('')
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMsg = ref('')

const title = computed(() => mode.value === 'login' ? 'Welcome back' : 'Create account')
const subtitle = computed(() =>
  mode.value === 'login'
    ? '欢迎回到灵犀智购 · 你的智能购物助手'
    : '加入灵犀智购 · 让购物更聪明'
)
const submitLabel = computed(() => isLoading.value ? '请稍等...' : (mode.value === 'login' ? '登录' : '注册并登录'))

async function handleSubmit() {
  if (isLoading.value) return
  errorMsg.value = ''

  if (!email.value || !password.value) {
    errorMsg.value = '请填写邮箱和密码'
    return
  }
  if (mode.value === 'register' && !username.value) {
    errorMsg.value = '请填写用户名'
    return
  }

  isLoading.value = true
  try {
    if (mode.value === 'login') {
      await login(email.value, password.value)
    } else {
      await register(username.value, email.value, password.value)
    }
    const redirect = (route.query.redirect && typeof route.query.redirect === 'string') ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (e) {
    errorMsg.value = e?.message || '操作失败，请稍后再试'
  } finally {
    isLoading.value = false
  }
}

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  errorMsg.value = ''
}

function onKeydown(e) {
  if (e.key === 'Enter') { e.preventDefault(); handleSubmit() }
}
</script>

<template>
  <div class="login-page">
    <!-- Ambient background blobs -->
    <div class="bg-blob blob-1" />
    <div class="bg-blob blob-2" />

    <div class="login-shell">
      <!-- Brand mark -->
      <div class="brand">
        <span class="brand-orb">
          <span class="orb-core">◎</span>
          <span class="orb-ring" />
        </span>
        <span class="brand-name font-display">灵犀智购</span>
      </div>

      <!-- Hero -->
      <div class="hero">
        <h1 class="welcome font-display">{{ title }}</h1>
        <p class="welcome-sub">{{ subtitle }}</p>
      </div>

      <!-- Form -->
      <form class="form" @submit.prevent="handleSubmit">
        <div v-if="mode === 'register'" class="field">
          <label>用户名</label>
          <input
            type="text"
            v-model="username"
            placeholder="为你的账号起个名字"
            :disabled="isLoading"
            @keydown="onKeydown"
            autocomplete="username"
          />
        </div>

        <div class="field">
          <label>邮箱</label>
          <input
            type="email"
            v-model="email"
            placeholder="you@example.com"
            :disabled="isLoading"
            @keydown="onKeydown"
            autocomplete="email"
          />
        </div>

        <div class="field">
          <label>密码</label>
          <input
            type="password"
            v-model="password"
            :placeholder="mode === 'register' ? '至少 6 位' : '输入密码'"
            :disabled="isLoading"
            @keydown="onKeydown"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          />
        </div>

        <div v-if="errorMsg" class="error">{{ errorMsg }}</div>

        <button class="submit-btn" type="submit" :disabled="isLoading">
          <span v-if="!isLoading">{{ submitLabel }}</span>
          <span v-else class="thinking"><i /><i /><i /></span>
        </button>
      </form>

      <!-- Mode toggle -->
      <div class="switch">
        <span v-if="mode === 'login'">还没有账号？</span>
        <span v-else>已经有账号了？</span>
        <button class="switch-btn" type="button" @click="switchMode" :disabled="isLoading">
          {{ mode === 'login' ? '立即注册' : '返回登录' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.font-display {
  font-family: var(--display);
  font-variation-settings: 'opsz' 96;
  letter-spacing: -0.035em;
}

.login-page {
  position: fixed; inset: 0;
  background: #000;
  display: grid; place-items: center;
  padding: 24px;
  overflow: hidden;
}

/* Ambient drifting blobs — same vibe as shop hero */
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  pointer-events: none;
  animation: drift-slow 14s var(--ease-in-out-cubic) infinite;
}
.blob-1 {
  width: 460px; height: 460px;
  background: radial-gradient(circle, var(--coral) 0%, transparent 70%);
  top: -120px; left: -100px;
}
.blob-2 {
  width: 520px; height: 520px;
  background: radial-gradient(circle, var(--lavender) 0%, transparent 70%);
  bottom: -160px; right: -120px;
  animation-delay: -6s;
}

/* Shell card */
.login-shell {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  background: linear-gradient(180deg, rgba(20,20,22,0.85), rgba(10,10,12,0.7));
  border: 1px solid var(--border-hi);
  border-radius: 24px;
  padding: 44px 40px 36px;
  backdrop-filter: blur(28px);
  box-shadow:
    0 32px 80px rgba(0,0,0,0.6),
    inset 0 1px 0 rgba(255,255,255,0.06);
  animation: rise 0.8s var(--ease-out-expo) forwards;
}

/* Brand */
.brand {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 32px;
}
.brand-orb {
  position: relative;
  width: 32px; height: 32px;
}
.orb-core {
  position: relative; z-index: 2;
  display: grid; place-items: center;
  width: 100%; height: 100%;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  color: #000;
  font-family: var(--display);
  font-size: 16px;
  font-weight: 800;
  box-shadow: 0 6px 16px rgba(232,180,168,0.35);
}
.orb-ring {
  position: absolute;
  inset: -5px;
  border-radius: 14px;
  border: 1.5px solid rgba(232, 180, 168, 0.4);
  animation: dot-pulse 2.5s ease-out infinite;
}
.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
}

/* Hero */
.hero {
  margin-bottom: 32px;
}
.welcome {
  font-size: 56px;
  font-weight: 700;
  line-height: 1.05;
  background: linear-gradient(120deg, #FFFFFF 0%, var(--coral) 40%, var(--lavender) 80%, #FFFFFF 100%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shimmer 6s linear infinite;
  margin-bottom: 14px;
}
.welcome-sub {
  font-size: 14px;
  color: var(--text-mute);
  line-height: 1.6;
}

/* Form */
.form { display: flex; flex-direction: column; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 7px; }
.field label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-mute);
}
.field input {
  height: 48px;
  padding: 0 18px;
  background: rgba(255,255,255,0.035);
  border: 1px solid var(--border-hi);
  border-radius: 14px;
  color: var(--text);
  font-size: 14px;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
.field input:focus {
  outline: none;
  background: rgba(255,255,255,0.05);
  border-color: rgba(232, 180, 168, 0.55);
  box-shadow: 0 0 0 4px rgba(232, 180, 168, 0.10);
}
.field input::placeholder { color: var(--text-faint); }
.field input:disabled { opacity: 0.5; }

.error {
  font-size: 12px;
  color: var(--coral);
  background: rgba(232, 180, 168, 0.08);
  border: 1px solid rgba(232, 180, 168, 0.25);
  border-radius: 10px;
  padding: 10px 14px;
}

.submit-btn {
  margin-top: 8px;
  height: 50px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  color: #000;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.02em;
  box-shadow: 0 12px 32px rgba(232,180,168,0.35);
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  display: grid; place-items: center;
}
.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px rgba(232,180,168,0.45);
}
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.thinking { display: inline-flex; gap: 5px; align-items: center; height: 14px; }
.thinking i {
  width: 6px; height: 6px; border-radius: 50%;
  background: #000; animation: dot-cycle 1.4s infinite;
}
.thinking i:nth-child(2) { animation-delay: .2s; }
.thinking i:nth-child(3) { animation-delay: .4s; }

/* Mode switch */
.switch {
  margin-top: 22px;
  text-align: center;
  font-size: 13px;
  color: var(--text-mute);
}
.switch-btn {
  margin-left: 6px;
  font-weight: 600;
  color: var(--coral);
  transition: color 0.15s;
}
.switch-btn:hover:not(:disabled) { color: var(--lavender); }
.switch-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Responsive: shrink hero font on narrow screens */
@media (max-width: 480px) {
  .login-shell { padding: 36px 28px 28px; }
  .welcome { font-size: 44px; }
}
</style>

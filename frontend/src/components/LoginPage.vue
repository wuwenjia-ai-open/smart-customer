<template>
  <div class="login-wrap">
    <div class="login-card">
      <h1>{{ isRegister ? '创建账号' : '欢迎回来' }}</h1>
      <p class="sub">{{ isRegister ? '注册灵犀智购' : '登录灵犀智购' }}</p>
      <div class="fg" v-if="isRegister">
        <label>用户名</label>
        <input type="text" v-model="regUsername" placeholder="给自己取个名字">
      </div>
      <div class="fg">
        <label>邮箱</label>
        <input type="email" v-model="email" placeholder="your@email.com">
      </div>
      <div class="fg">
        <label>密码</label>
        <input type="password" v-model="password" placeholder="输入密码" @keydown.enter="handleAuth">
      </div>
      <div :class="['err', { show: errorMsg }]">{{ errorMsg }}</div>
      <button class="btn btn-p" @click="handleAuth" :disabled="loading">
        {{ loading ? '处理中...' : (isRegister ? '注册' : '登录') }}
      </button>
      <button class="btn btn-s" @click="toggleMode">
        {{ isRegister ? '已有账号？立即登录' : '还没有账号？立即注册' }}
      </button>
      <div class="ff">
        <label style="font-size:12px;color:var(--t3);cursor:pointer">
          <input type="checkbox" v-model="agreed" style="width:auto"> 同意用户协议与隐私政策
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth.js'

const emit = defineEmits(['loginSuccess'])
const { login, register } = useAuth()

const isRegister = ref(false)
const email = ref('')
const password = ref('')
const regUsername = ref('')
const agreed = ref(true)
const errorMsg = ref('')
const loading = ref(false)

function toggleMode() {
  isRegister.value = !isRegister.value
  errorMsg.value = ''
}

async function handleAuth() {
  errorMsg.value = ''
  if (!email.value || !password.value) {
    errorMsg.value = '请填写邮箱和密码'
    return
  }
  if (!agreed.value) {
    errorMsg.value = '请同意用户协议'
    return
  }
  loading.value = true
  try {
    if (isRegister.value) {
      if (!regUsername.value) {
        errorMsg.value = '请输入用户名'
        loading.value = false
        return
      }
      await register(regUsername.value, email.value, password.value)
      isRegister.value = false
      errorMsg.value = '注册成功，请登录'
      loading.value = false
      return
    }
    await login(email.value, password.value)
    emit('loginSuccess')
  } catch (e) {
    errorMsg.value = e.message || '操作失败'
  }
  loading.value = false
}
</script>

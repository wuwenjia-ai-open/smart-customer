<template>
  <div class="app active">
    <header class="topbar">
      <div class="brand"><div class="dot"></div>灵犀智购</div>
      <div class="nav-r">
        <div class="user-chip">
          <div class="user-av">{{ userInitial }}</div>
          <span>{{ userDisplayName }}</span>
        </div>
      </div>
    </header>
    <div class="main-content">
      <ProductGrid />
    </div>
    <div class="cs-float">
      <button class="cs-btn" @click="$emit('openChat')">
        <span class="cs-dot"></span>咨询 AI 客服<span class="cs-arr">→</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ProductGrid from './ProductGrid.vue'
import { useAuth } from '../composables/useAuth.js'

defineEmits(['openChat'])
const { user } = useAuth()

const userInitial = computed(() => (user.username || user.email || '?').charAt(0).toUpperCase())
const userDisplayName = computed(() => user.username || user.email || '未登录')
</script>

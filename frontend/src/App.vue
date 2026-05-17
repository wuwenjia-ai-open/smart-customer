<script setup>
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const router = useRouter()
const isChat = computed(() => route.name === 'chat')

function toggleView() {
  router.push(isChat.value ? '/' : '/chat')
}
</script>

<template>
  <div class="relative min-h-screen bg-[#050508]">
    <div class="relative z-10">
      <button
        @click="toggleView"
        class="fixed top-5 left-5 z-50 flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] backdrop-blur-xl px-3.5 py-2 text-sm text-neutral-300 transition-all hover:bg-white/[0.08] hover:border-white/[0.16] hover:text-white hover:shadow-[0_0_25px_rgba(108,92,231,0.25)] active:scale-95"
      >
        <span class="text-base">{{ isChat ? '🛍️' : '💬' }}</span>
        <span>{{ isChat ? '商城' : '客服' }}</span>
      </button>

      <router-view />
    </div>
  </div>
</template>

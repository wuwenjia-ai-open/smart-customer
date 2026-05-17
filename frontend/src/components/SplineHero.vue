<script setup>
import { ref } from 'vue'

const SCENE_URL = 'https://my.spline.design/pushathreadscomminigame-nz4gQlEzd934bk7d1b4eaUJx/'
const loaded = ref(false)
const emit = defineEmits(['scroll-down'])
</script>

<template>
  <section class="relative h-screen w-full overflow-hidden">
    <!-- Spline iframe -->
    <div class="absolute inset-0">
      <iframe
        :src="SCENE_URL"
        class="h-full w-full border-0"
        allow="autoplay; fullscreen"
        @load="loaded = true"
      />
    </div>

    <!-- Loading -->
    <div v-if="!loaded" class="absolute inset-0 z-20 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div class="h-10 w-10 animate-spin rounded-full border-2 border-transparent border-t-purple-500" />
    </div>

    <!-- Overlay content -->
    <div class="absolute inset-0 z-10 flex flex-col items-center justify-end pb-12 pointer-events-none">
      <div class="mb-6 text-center pointer-events-auto">
        <h1 class="mb-3 text-6xl font-bold tracking-tight md:text-8xl"
          style="background: linear-gradient(to bottom, #fff 0%, rgba(255,255,255,0.5) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
          灵犀智购
        </h1>
        <p class="text-sm text-neutral-400 md:text-base">AI 驱动的智能电子产品选购平台</p>
      </div>

      <div class="flex flex-col items-center gap-5 pointer-events-auto">
        <button
          @click="$emit('scroll-down')"
          class="rounded-full bg-white/10 px-8 py-3 text-sm font-medium text-white backdrop-blur-md transition-all hover:bg-white/20 hover:shadow-[0_0_30px_rgba(108,92,231,0.3)] active:scale-95"
        >
          开始选购
        </button>
        <div class="flex animate-bounce flex-col items-center gap-1 opacity-40 pointer-events-none">
          <span class="text-xs text-neutral-500">向下滚动</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
      </div>
    </div>

    <!-- Bottom fade to black -->
    <div class="pointer-events-none absolute bottom-0 left-0 right-0 z-10 h-40 bg-gradient-to-b from-transparent to-black/80" />
  </section>
</template>

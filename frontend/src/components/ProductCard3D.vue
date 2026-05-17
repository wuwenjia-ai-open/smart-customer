<script setup>
import { ref, computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  product: { type: Object, required: true },
  class: { type: String, default: '' },
})

const cardRef = ref(null)
const rotateX = ref(0)
const rotateY = ref(0)
const glowX = ref(50)
const glowY = ref(50)

function onMouseMove(e) {
  if (!cardRef.value) return
  const rect = cardRef.value.getBoundingClientRect()
  const x = (e.clientX - rect.left) / rect.width
  const y = (e.clientY - rect.top) / rect.height
  rotateY.value = (x - 0.5) * 20
  rotateX.value = (y - 0.5) * -20
  glowX.value = x * 100
  glowY.value = y * 100
}

function onMouseLeave() {
  rotateX.value = 0
  rotateY.value = 0
  glowX.value = 50
  glowY.value = 50
}

const transform = computed(() =>
  `perspective(1000px) rotateX(${rotateX.value}deg) rotateY(${rotateY.value}deg)`
)
</script>

<template>
  <div
    ref="cardRef"
    :class="cn('group relative cursor-default', props.class)"
    :style="{ transform }"
    @mousemove="onMouseMove"
    @mouseleave="onMouseLeave"
  >
    <!-- Glow effect -->
    <div
      class="pointer-events-none absolute -inset-10 z-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
      :style="{
        background: `radial-gradient(circle at ${glowX}% ${glowY}%, rgba(108,92,231,0.15) 0%, transparent 50%)`,
      }"
    />

    <!-- Card body -->
    <div class="relative z-10 overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-xl transition-all duration-300 group-hover:border-white/[0.12] group-hover:shadow-[0_20px_80px_rgba(0,0,0,0.5)]">
      <slot />
    </div>
  </div>
</template>

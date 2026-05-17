<script setup>
import { ref, onMounted } from 'vue'
import ProductCard3D from './ProductCard3D.vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  product: { type: Object, required: true },
  index: { type: Number, default: 0 },
  image: { type: String, default: '' },
})

const sectionRef = ref(null)
const visible = ref(false)

onMounted(() => {
  const observer = new IntersectionObserver(
    ([entry]) => { if (entry.isIntersecting) visible.value = true },
    { threshold: 0.2 }
  )
  if (sectionRef.value) observer.observe(sectionRef.value)
})

const isEven = props.index % 2 === 0
</script>

<template>
  <section
    ref="sectionRef"
    class="relative flex w-full items-center justify-center px-4 py-12 md:py-16"
  >
    <div class="absolute inset-0 opacity-[0.02]"
      style="background-image: radial-gradient(circle, rgba(108,92,231,0.5) 1px, transparent 1px); background-size: 40px 40px;" />

    <ProductCard3D
      :product="product"
      class="w-full max-w-6xl"
      :class="cn(
        visible ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0',
        'transition-all duration-700 ease-out'
      )"
    >
      <div :class="cn(
        'flex flex-col items-center gap-6 p-6 md:flex-row md:gap-10 md:p-10',
        isEven ? '' : 'md:flex-row-reverse'
      )">
        <!-- Product Image -->
        <div class="flex-shrink-0 overflow-hidden rounded-xl md:w-1/2">
          <img
            v-if="image"
            :src="image"
            :alt="product.name"
            class="h-72 w-72 object-contain md:h-[420px] md:w-full"
          />
          <div v-else class="flex h-72 w-72 items-center justify-center rounded-xl bg-white/[0.03] md:h-[420px] md:w-full">
            <span class="text-7xl">📦</span>
          </div>
        </div>

        <!-- Product Info -->
        <div class="flex flex-col gap-3 md:w-1/2 md:gap-5">
          <div class="flex items-center gap-3">
            <span class="rounded-full bg-purple-500/10 px-3 py-1 text-xs font-medium text-purple-400 border border-purple-500/20">
              {{ product.category }}
            </span>
            <span class="text-xs text-neutral-500">{{ product.brand }}</span>
          </div>

          <h2 class="text-2xl font-bold tracking-tight md:text-4xl">{{ product.name }}</h2>

          <p class="text-sm leading-relaxed text-neutral-400 md:text-base">{{ product.description }}</p>

          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="f in product.features"
              :key="f"
              class="rounded-md bg-white/[0.04] px-2.5 py-1 text-xs text-neutral-400 border border-white/[0.06]"
            >
              {{ f }}
            </span>
          </div>

          <div class="flex items-center gap-5">
            <span class="text-2xl font-bold md:text-3xl" style="background: linear-gradient(135deg, #a78bfa, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              ¥{{ product.price.toLocaleString() }}
            </span>
            <div class="flex items-center gap-1.5 text-sm text-neutral-400">
              <span class="text-yellow-500">★</span>
              <span>{{ product.rating }}</span>
              <span class="text-neutral-600">({{ product.reviews }})</span>
            </div>
          </div>
        </div>
      </div>
    </ProductCard3D>
  </section>
</template>

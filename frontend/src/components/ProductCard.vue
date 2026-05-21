<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const props = defineProps({
  product: { type: Object, required: true },
  index:   { type: Number, default: 0 },
})

function askAI() {
  router.push({ name: 'chat', query: { q: `介绍一下${props.product.name}` } })
}

function specPoints(specs) {
  return (specs || '').split(/[·•]/).map(s => s.trim()).filter(Boolean)
}
</script>

<template>
  <article
    class="product-card"
    data-reveal
    :style="{
      '--accent': product.accent,
      '--reveal-delay': `${index * 0.12}s`
    }"
  >
    <!-- Left: media -->
    <div class="card-media">
      <div
        v-if="product.image"
        class="media-image"
        :style="{
          backgroundImage: `url(${product.image})`,
          backgroundPosition: product.imagePos || 'center',
        }"
      />
      <div v-else class="media-fallback" :style="{ background: product.gradient }">
        <span class="fallback-emoji">{{ product.icon }}</span>
      </div>

      <!-- Floating chips -->
      <span class="float-mark mark-rate mono">★ {{ product.rating }}</span>
      <span class="float-mark mark-rev mono">{{ product.reviews.toLocaleString() }} 评价</span>

      <!-- Subtle accent glow tied to product color -->
      <div
        class="media-glow"
        :style="{ background: `radial-gradient(circle, ${product.accent}30, transparent 65%)` }"
      />
    </div>

    <!-- Right: content -->
    <div class="card-body">
      <div class="cat-row">
        <span class="cat-dot" :style="{ background: product.accent }" />
        <span class="cat-label">{{ product.category }}</span>
        <span v-if="product.badge" class="cat-badge">{{ product.badge }}</span>
      </div>

      <h3 class="prod-name font-display">{{ product.name }}</h3>
      <p v-if="product.tagline" class="prod-tagline">{{ product.tagline }}</p>

      <ul class="spec-list">
        <li v-for="(s, i) in specPoints(product.specs).slice(0, 4)" :key="i">
          <span class="spec-bullet" />
          {{ s }}
        </li>
      </ul>

      <div class="card-foot">
        <div class="price-block">
          <span class="price-cur mono">¥</span>
          <span class="price-num mono">{{ product.price.toLocaleString() }}</span>
          <span v-if="product.originalPrice" class="price-old mono">
            ¥{{ product.originalPrice.toLocaleString() }}
          </span>
        </div>

        <button class="ai-btn" @click.stop="askAI">
          AI 咨询
          <span class="ai-arrow">→</span>
        </button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.product-card {
  position: relative;
  display: grid;
  grid-template-columns: 0.85fr 1.15fr;
  gap: 0;
  min-height: 320px;
  border-radius: 22px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  overflow: hidden;
  transition:
    transform 0.5s var(--ease-out-expo),
    border-color 0.5s var(--ease-out-expo),
    box-shadow 0.5s var(--ease-out-expo);
  transition-delay: var(--reveal-delay, 0s);
}

.product-card:hover {
  transform: translateY(-4px);
  border-color: rgba(232, 180, 168, 0.45);
  box-shadow:
    0 18px 42px rgba(0,0,0,0.6),
    0 0 0 1px rgba(232,180,168,0.18),
    0 0 60px rgba(232,180,168,0.10);
}

/* ── Media (left) ─────────────────────────────────────── */
.card-media {
  position: relative;
  overflow: hidden;
  background: #050505;
}
.media-image {
  position: absolute; inset: 0;
  background-size: cover;
  background-repeat: no-repeat;
  transition: transform 0.7s var(--ease-out-expo);
}
.product-card:hover .media-image {
  transform: scale(1.06) translateY(-4px);
}
.media-fallback {
  position: absolute; inset: 0;
  display: grid; place-items: center;
  transition: transform 0.7s var(--ease-out-expo);
}
.product-card:hover .media-fallback {
  transform: scale(1.06);
}
.fallback-emoji {
  font-size: 120px;
  filter: grayscale(0.3) drop-shadow(0 14px 30px rgba(0,0,0,0.6));
}

.media-glow {
  position: absolute;
  top: 50%; left: 50%;
  width: 380px; height: 380px;
  transform: translate(-50%, -50%);
  filter: blur(60px) saturate(0.7);
  opacity: 0.5;
  pointer-events: none;
  transition: opacity 0.6s;
}
.product-card:hover .media-glow {
  opacity: 0.85;
}

/* Right edge fade into card-body */
.card-media::after {
  content: '';
  position: absolute;
  top: 0; bottom: 0; right: 0;
  width: 80px;
  background: linear-gradient(90deg, transparent, var(--bg-card));
  pointer-events: none;
}

.float-mark {
  position: absolute;
  z-index: 4;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  color: #fff;
  background: rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(255,255,255,0.08);
  backdrop-filter: blur(8px);
  letter-spacing: 0.04em;
}
.mark-rate {
  top: 18px; left: 18px;
  color: #F5C97A;
  border-color: rgba(245,201,122,0.25);
  background: rgba(40,30,12,0.55);
}
.mark-rev { bottom: 18px; left: 18px; }

/* ── Body (right) ─────────────────────────────────────── */
.card-body {
  position: relative;
  z-index: 2;
  padding: 30px 32px 28px;
  display: flex; flex-direction: column;
}

.cat-row {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 14px;
}
.cat-dot {
  width: 6px; height: 6px; border-radius: 50%;
  filter: saturate(0.45) brightness(1.25);
  box-shadow: 0 0 8px currentColor;
}
.cat-label {
  font-size: 11px; font-weight: 600;
  color: var(--text-mute);
  letter-spacing: 0.22em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.cat-badge {
  margin-left: auto;
  padding: 4px 11px;
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.12em;
  color: #000;
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  border-radius: 999px;
}

.prod-name {
  font-size: 30px;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.025em;
  color: var(--text);
  margin-bottom: 6px;
  font-variation-settings: 'opsz' 48;
}
.prod-tagline {
  font-size: 13px;
  color: var(--coral);
  margin-bottom: 14px;
  letter-spacing: 0.02em;
  opacity: 0.85;
}

.spec-list {
  list-style: none;
  display: flex; flex-direction: column; gap: 5px;
  margin-bottom: 16px;
  flex: 1;
}
.spec-list li {
  display: flex; align-items: center; gap: 10px;
  font-size: 12.5px;
  color: var(--text-soft);
  line-height: 1.45;
}
.spec-bullet {
  width: 4px; height: 4px;
  background: var(--text-mute);
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 0.3s;
}
.product-card:hover .spec-bullet { background: var(--coral); }

.card-foot {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px;
  margin-top: auto;
}

.price-block { display: flex; align-items: baseline; gap: 4px; }
.price-cur {
  font-size: 16px; color: var(--text-soft); font-weight: 500;
}
.price-num {
  font-size: 28px; font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}
.price-old {
  margin-left: 8px;
  font-size: 13px;
  color: var(--text-mute);
  text-decoration: line-through;
}

.ai-btn {
  position: relative;
  display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 22px;
  border-radius: 999px;
  font-size: 13px; font-weight: 700;
  color: #000;
  background: linear-gradient(110deg, #ffffff 0%, #f6e8e2 30%, #ffffff 60%, #ece6f3 90%, #ffffff 100%);
  background-size: 200% 100%;
  box-shadow: 0 6px 18px rgba(255,255,255,0.10), inset 0 -2px 0 rgba(0,0,0,0.08);
  transition: transform 0.2s var(--ease-out-expo), box-shadow 0.3s;
}
.product-card:hover .ai-btn {
  animation: shine-sweep 2.5s linear infinite;
}
.ai-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(232,180,168,0.40), inset 0 -2px 0 rgba(0,0,0,0.08);
}
.ai-arrow { font-size: 14px; transition: transform 0.2s; }
.ai-btn:hover .ai-arrow { transform: translateX(3px); }

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 760px) {
  .product-card {
    grid-template-columns: 1fr;
    grid-template-rows: 200px auto;
    min-height: auto;
  }
  .card-media::after { display: none; }
  .card-body { padding: 24px 22px 24px; }
  .prod-name { font-size: 24px; }
}
</style>

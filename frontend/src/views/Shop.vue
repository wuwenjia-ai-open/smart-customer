<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import ProductCard from '@/components/ProductCard.vue'
import PhoneDashboard from '@/components/PhoneDashboard.vue'
import { PRODUCTS } from '@/data/products.js'
import { useScrollReveal } from '@/composables/useScrollReveal.js'

const router   = useRouter()
const scrolled = ref(false)
const scrollY  = ref(0)
const email    = ref('')

const heroRef    = ref(null)
const phoneRef   = ref(null)
const leftWordRef  = ref(null)
const rightWordRef = ref(null)

const FEATURED = [
  PRODUCTS.find(p => p.id === 1),
  PRODUCTS.find(p => p.id === 21),
  PRODUCTS.find(p => p.id === 7),
  PRODUCTS.find(p => p.id === 10),
]

const BRANDS = ['Apple', 'Samsung', 'HUAWEI', 'Xiaomi', 'SONY', 'ROG', 'DELL', 'Microsoft']

useScrollReveal()

function goChat(q = '') {
  router.push(q ? { name: 'chat', query: { q } } : { name: 'chat' })
}

function onSubscribe() {
  const q = email.value.trim()
    ? `请联系我，我的邮箱：${email.value.trim()}`
    : '请帮我推荐一款产品'
  goChat(q)
}

/* ── Scroll handlers ────────────────────────────────────── */
let rafId = null
function onScroll() {
  scrollY.value = window.scrollY
  scrolled.value = window.scrollY > 30

  if (rafId) return
  rafId = requestAnimationFrame(() => {
    const y = scrollY.value
    if (phoneRef.value) {
      const sc = Math.max(0.7, 1 - y * 0.0006)
      phoneRef.value.style.transform = `translate3d(0, ${y * 0.25}px, 0) scale(${sc})`
    }
    if (leftWordRef.value)
      leftWordRef.value.style.transform = `translate3d(${-y * 0.18}px, ${y * 0.10}px, 0)`
    if (rightWordRef.value)
      rightWordRef.value.style.transform = `translate3d(${y * 0.18}px, ${y * 0.10}px, 0)`
    rafId = null
  })
}

/* ── Pointer-tracking in hero ───────────────────────────── */
let pTilt = { rx: 0, ry: 0 }
function onHeroPointer(e) {
  if (!heroRef.value) return
  const r = heroRef.value.getBoundingClientRect()
  const mx = e.clientX - r.left
  const my = e.clientY - r.top
  heroRef.value.style.setProperty('--mx', `${mx}px`)
  heroRef.value.style.setProperty('--my', `${my}px`)

  // phone tilt (subtle ±6deg)
  const cx = r.width / 2
  const cy = r.height / 2
  pTilt.ry = ((mx - cx) / cx) * 6
  pTilt.rx = -((my - cy) / cy) * 6
  if (phoneRef.value) {
    phoneRef.value.style.setProperty('--rx', `${pTilt.rx}deg`)
    phoneRef.value.style.setProperty('--ry', `${pTilt.ry}deg`)
  }
}
function onHeroLeave() {
  if (phoneRef.value) {
    phoneRef.value.style.setProperty('--rx', `0deg`)
    phoneRef.value.style.setProperty('--ry', `0deg`)
  }
}

/* ── Magnetic CTAs ──────────────────────────────────────── */
function magneticMove(e) {
  const btn = e.currentTarget
  const r = btn.getBoundingClientRect()
  const x = e.clientX - r.left - r.width / 2
  const y = e.clientY - r.top - r.height / 2
  btn.style.transform = `translate(${x * 0.18}px, ${y * 0.25}px)`
}
function magneticLeave(e) {
  e.currentTarget.style.transform = ''
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  nextTick(onScroll)
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  if (rafId) cancelAnimationFrame(rafId)
})
</script>

<template>
  <!-- ══════════════════════════════════════════════════
       NAV
       ══════════════════════════════════════════════════ -->
  <nav :class="['top-nav', { solid: scrolled }]">
    <div class="nav-row">
      <div class="brand">
        <span class="brand-mark"><span class="brand-dot" /></span>
        <span class="brand-name">灵犀™</span>
      </div>

      <div class="nav-pill-group">
        <button class="nav-pill active">
          <span class="pill-dot" />
          商城
        </button>
        <button class="nav-pill">手机</button>
        <button class="nav-pill">笔记本</button>
        <button class="nav-pill">音频</button>
        <button class="nav-pill">关于</button>
      </div>

      <button
        class="nav-cta"
        @click="goChat()"
        @mousemove="magneticMove"
        @mouseleave="magneticLeave"
      >
        立即体验
      </button>
    </div>
  </nav>

  <!-- ══════════════════════════════════════════════════
       HERO
       ══════════════════════════════════════════════════ -->
  <section
    class="hero"
    ref="heroRef"
    @mousemove="onHeroPointer"
    @mouseleave="onHeroLeave"
  >
    <!-- Ambient blobs -->
    <div class="amb amb-coral" />
    <div class="amb amb-lav" />
    <div class="amb-grid" />
    <div class="amb-noise" />

    <!-- Eyebrow -->
    <div class="hero-eyebrow" data-reveal>
      <span class="eb-thin">灵犀</span>
      <span class="eb-bold">智购</span>
    </div>

    <!-- Giant headline · 3-column grid where center column has the phone -->
    <div class="hero-stage">
      <div class="head-word head-left" ref="leftWordRef" data-reveal data-reveal-delay="1">
        Meet
      </div>

      <div class="phone-wrap" ref="phoneRef" data-reveal data-reveal-delay="2">
        <div class="phone-halo" />
        <div class="phone">
          <div class="phone-frame">
            <div class="phone-screen">
              <div class="phone-island" />
              <PhoneDashboard />
              <div class="phone-glass" />
            </div>
            <div class="phone-rim" />
          </div>
          <div class="phone-floor" />
        </div>
      </div>

      <div class="head-word head-right" ref="rightWordRef" data-reveal data-reveal-delay="3">
        Lingxi
      </div>
    </div>

    <!-- Subtitle -->
    <p class="hero-sub" data-reveal data-reveal-delay="4">
      AI-powered recommendations for premium consumer electronics.
      <span class="sub-faint">Smart. Personal. Real-time.</span>
    </p>

    <!-- Email CTA -->
    <form class="hero-cta-form" @submit.prevent="onSubscribe" data-reveal data-reveal-delay="5">
      <input
        v-model="email"
        type="email"
        placeholder="留下邮箱，AI 客服即刻联系"
        class="hero-email"
      />
      <button
        type="submit"
        class="hero-trial"
        @mousemove="magneticMove"
        @mouseleave="magneticLeave"
      >
        立即体验
        <span class="trial-arrow">→</span>
      </button>
    </form>

    <!-- Brand wall -->
    <div class="brand-wall" data-reveal>
      <div class="brand-row">
        <span v-for="(b, i) in BRANDS" :key="b" class="bw-item" :style="`--bw-i:${i}`">
          {{ b }}
        </span>
      </div>
      <p class="brand-caption">Trusted by Top-tier consumer electronics brands</p>
    </div>
  </section>

  <!-- ══════════════════════════════════════════════════
       FEATURED PRODUCTS
       ══════════════════════════════════════════════════ -->
  <section class="featured-section">
    <header class="featured-head" data-reveal>
      <div class="featured-eyebrow">
        <span class="eyebrow-line" />
        FEATURED
        <span class="eyebrow-line" />
      </div>
      <h2 class="featured-title font-display">
        本月 <span class="featured-accent">精选好物</span>
      </h2>
      <p class="featured-sub">极简 · 黑金 · 让产品自己说话</p>
    </header>

    <div class="featured-stack">
      <ProductCard
        v-for="(p, i) in FEATURED"
        :key="p.id"
        :product="p"
        :index="i"
      />
    </div>
  </section>

  <!-- ══════════════════════════════════════════════════
       FOOTER
       ══════════════════════════════════════════════════ -->
  <footer class="foot">
    <div class="foot-row">
      <div class="brand foot-brand">
        <span class="brand-mark"><span class="brand-dot" /></span>
        灵犀智购
      </div>
      <div class="foot-mid">AI 驱动的消费电子智能选购</div>
      <div class="foot-end mono">© 2026 LINGXI</div>
    </div>
  </footer>

  <!-- Floating chat FAB -->
  <button class="fab" @click="goChat()" aria-label="AI 客服">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    </svg>
    <span class="fab-pulse" />
  </button>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   NAV
   ═══════════════════════════════════════════════════════════ */
.top-nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 90;
  padding: 18px 0;
  transition: padding 0.3s, background 0.3s, border-color 0.3s, backdrop-filter 0.3s;
}
.top-nav.solid {
  padding: 12px 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
  border-bottom: 1px solid var(--border);
}
.nav-row {
  max-width: 1280px; margin: 0 auto;
  padding: 0 40px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 32px;
}

.brand {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--display);
  font-weight: 700; font-size: 18px;
  letter-spacing: -0.02em;
  color: var(--text);
}
.brand-mark {
  width: 30px; height: 30px; border-radius: 9px;
  background: linear-gradient(135deg, #18181B 0%, #2A2A2E 100%);
  border: 1px solid rgba(232, 180, 168, 0.35);
  display: grid; place-items: center;
  box-shadow: inset 0 0 12px rgba(232, 180, 168, 0.18);
}
.brand-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--coral);
  animation: dot-pulse 2.4s ease-out infinite;
}
.brand-name { font-feature-settings: 'ss01'; }

/* Pill nav */
.nav-pill-group {
  justify-self: center;
  display: flex; align-items: center; gap: 4px;
  padding: 5px; border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  backdrop-filter: blur(12px);
}
.nav-pill {
  padding: 8px 18px;
  border-radius: 999px;
  font-size: 13px; font-weight: 500;
  color: var(--text-mute);
  transition: color 0.2s, background 0.2s;
  display: inline-flex; align-items: center; gap: 8px;
}
.nav-pill:hover { color: var(--text-soft); }
.nav-pill.active {
  color: var(--text);
  background: rgba(255,255,255,0.07);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
.pill-dot {
  width: 12px; height: 12px; border-radius: 4px;
  background: linear-gradient(135deg, var(--coral), var(--lavender));
}

/* CTA */
.nav-cta {
  position: relative;
  display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 22px;
  border-radius: 999px;
  font-size: 13px; font-weight: 600;
  color: #000;
  background: linear-gradient(110deg, #ffffff 0%, #f6e8e2 30%, #ffffff 60%, #ece6f3 90%, #ffffff 100%);
  background-size: 200% 100%;
  animation: shine-sweep 4.5s linear infinite;
  box-shadow: 0 4px 18px rgba(255,255,255,0.12), inset 0 -2px 0 rgba(0,0,0,0.08);
  transition: box-shadow 0.25s, transform 0.18s var(--ease-out-expo);
}
.nav-cta:hover {
  box-shadow: 0 8px 28px rgba(232,180,168,0.35), inset 0 -2px 0 rgba(0,0,0,0.08);
}

/* ═══════════════════════════════════════════════════════════
   HERO
   ═══════════════════════════════════════════════════════════ */
.hero {
  position: relative;
  min-height: 100vh;
  padding: 140px 40px 60px;
  display: flex; flex-direction: column;
  align-items: center;
  overflow: hidden;
  isolation: isolate;
}

/* Pointer-tracking glow */
.hero::before {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(420px circle at var(--mx, 50%) var(--my, 40%),
    rgba(232,180,168,0.16), transparent 70%);
  pointer-events: none;
  mix-blend-mode: screen;
  transition: background 0.12s linear;
  z-index: 0;
}

/* Ambient blobs */
.amb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  pointer-events: none;
  z-index: 0;
  animation: drift-slow 22s ease-in-out infinite;
}
.amb-coral {
  width: 620px; height: 620px;
  top: -160px; left: -120px;
  background: radial-gradient(circle, rgba(232,180,168,0.35), transparent 70%);
}
.amb-lav {
  width: 540px; height: 540px;
  bottom: -120px; right: -120px;
  background: radial-gradient(circle, rgba(200,197,224,0.28), transparent 70%);
  animation-delay: -9s;
}
.amb-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 80px 80px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
  pointer-events: none;
  z-index: 0;
}
.amb-noise {
  position: absolute; inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85'/></filter><rect width='200' height='200' filter='url(%23n)' opacity='0.5'/></svg>");
  opacity: 0.05;
  mix-blend-mode: overlay;
  pointer-events: none;
  z-index: 0;
}

/* Eyebrow */
.hero-eyebrow {
  position: relative; z-index: 2;
  display: inline-flex; align-items: baseline; gap: 6px;
  font-family: var(--display);
  font-size: 14px;
  color: var(--text-mute);
  letter-spacing: 0.04em;
  margin-bottom: 8px;
}
.eb-thin { font-weight: 300; font-style: italic; opacity: 0.6; }
.eb-bold { font-weight: 600; color: var(--text-soft); }

/* Stage: 3-column grid for "Meet [Phone] Lingxi" */
.hero-stage {
  position: relative; z-index: 2;
  width: 100%;
  max-width: 1380px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  justify-items: center;
  gap: 0;
  margin: 0 auto;
  min-height: 520px;
}

.head-word {
  font-family: var(--display);
  font-weight: 600;
  font-size: clamp(80px, 14vw, 200px);
  line-height: 1;
  letter-spacing: -0.045em;
  font-variation-settings: 'opsz' 96;
  position: relative;
  z-index: 1;
  will-change: transform;
  transition: transform 0.6s var(--ease-out-expo);
}
.head-left {
  color: var(--coral);
  text-shadow: 0 8px 60px rgba(232,180,168,0.15);
  justify-self: end;
  margin-right: -30px;
  font-style: italic;
}
.head-right {
  background: linear-gradient(110deg, var(--lavender) 0%, var(--lavender-deep) 60%, var(--lavender) 100%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: shimmer 8s linear infinite;
  text-shadow: 0 8px 60px rgba(200,197,224,0.15);
  justify-self: start;
  margin-left: -30px;
}

/* Phone wrap (center column, above text) */
.phone-wrap {
  position: relative;
  z-index: 3;
  width: 280px; height: 580px;
  perspective: 1400px;
  --rx: 0deg;
  --ry: 0deg;
  transition: transform 0.6s var(--ease-out-expo);
  will-change: transform;
}
.phone-halo {
  position: absolute;
  top: 50%; left: 50%;
  width: 460px; height: 460px;
  background: radial-gradient(circle,
    rgba(232,180,168,0.45) 0%,
    rgba(200,197,224,0.30) 35%,
    transparent 65%);
  filter: blur(50px);
  z-index: -1;
  pointer-events: none;
  animation: orbit-glow 7s ease-in-out infinite;
}

.phone {
  position: relative;
  width: 100%; height: 100%;
  transform: rotateX(var(--rx)) rotateY(var(--ry));
  transition: transform 0.4s var(--ease-out-expo);
  transform-style: preserve-3d;
}
.phone-frame {
  position: relative;
  width: 100%; height: 100%;
  padding: 9px;
  border-radius: 50px;
  background:
    linear-gradient(105deg,
      #1A1A1E 0%,
      #45454A 8%,
      #1A1A1E 24%,
      #2A2A2E 50%,
      #1A1A1E 76%,
      #45454A 92%,
      #1A1A1E 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.20),
    inset 0 -1px 0 rgba(0, 0, 0, 0.5),
    0 38px 80px rgba(0, 0, 0, 0.70),
    0 0 70px rgba(232,180,168,0.18),
    0 0 140px rgba(200,197,224,0.12);
}
.phone-rim {
  position: absolute;
  inset: 0;
  border-radius: 50px;
  pointer-events: none;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.10) 0%, transparent 6%, transparent 94%, rgba(255,255,255,0.06) 100%),
    linear-gradient(95deg, transparent 92%, rgba(255,255,255,0.35) 96%, transparent 100%);
  mix-blend-mode: overlay;
}
.phone-screen {
  position: relative;
  width: 100%; height: 100%;
  border-radius: 42px;
  overflow: hidden;
  background: #000;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.8);
}
.phone-island {
  position: absolute;
  top: 12px; left: 50%; transform: translateX(-50%);
  width: 95px; height: 28px;
  background: #000;
  border-radius: 14px;
  z-index: 6;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.04);
}
.phone-glass {
  position: absolute;
  inset: 0;
  z-index: 7;
  pointer-events: none;
  border-radius: 42px;
  background:
    linear-gradient(125deg, rgba(255,255,255,0.10) 0%, transparent 22%, transparent 78%, rgba(255,255,255,0.04) 100%);
}
.phone-floor {
  position: absolute;
  bottom: -40px; left: 15%; right: 15%;
  height: 60px;
  background: radial-gradient(ellipse,
    rgba(232,180,168,0.35) 0%,
    rgba(200,197,224,0.20) 50%,
    transparent 80%);
  filter: blur(25px);
  z-index: -2;
}

/* Subtitle */
.hero-sub {
  position: relative; z-index: 2;
  margin: 40px auto 0;
  max-width: 580px;
  text-align: center;
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-soft);
  letter-spacing: 0.01em;
}
.sub-faint { color: var(--text-mute); display: block; margin-top: 4px; }

/* Email CTA */
.hero-cta-form {
  position: relative; z-index: 2;
  margin-top: 32px;
  display: flex; align-items: center;
  gap: 6px;
  padding: 6px;
  border-radius: 999px;
  background: rgba(20,20,22,0.7);
  border: 1px solid var(--border-hi);
  backdrop-filter: blur(14px);
  max-width: 520px; width: 100%;
}
.hero-email {
  flex: 1;
  padding: 12px 18px;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 13px;
}
.hero-email::placeholder { color: var(--text-mute); }
.hero-trial {
  position: relative;
  padding: 12px 22px;
  border-radius: 999px;
  font-size: 13px; font-weight: 600;
  color: #000;
  background: linear-gradient(110deg, #ffffff 0%, #f6e8e2 30%, #ffffff 60%, #ece6f3 90%, #ffffff 100%);
  background-size: 200% 100%;
  animation: shine-sweep 4.5s linear infinite;
  display: inline-flex; align-items: center; gap: 8px;
  box-shadow: 0 6px 18px rgba(255,255,255,0.10), inset 0 -2px 0 rgba(0,0,0,0.08);
  transition: box-shadow 0.25s, transform 0.18s var(--ease-out-expo);
}
.hero-trial:hover {
  box-shadow: 0 10px 28px rgba(232,180,168,0.35), inset 0 -2px 0 rgba(0,0,0,0.08);
}
.trial-arrow { font-size: 14px; transition: transform 0.2s; }
.hero-trial:hover .trial-arrow { transform: translateX(3px); }

/* Brand wall */
.brand-wall {
  position: relative; z-index: 2;
  margin-top: 80px;
  width: 100%;
  max-width: 1100px;
}
.brand-row {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  align-items: center;
  gap: 24px;
}
.bw-item {
  font-family: var(--display);
  font-weight: 500;
  font-size: 18px;
  letter-spacing: -0.01em;
  text-align: center;
  color: rgba(255,255,255,0.45);
  opacity: 0;
  transition: color 0.3s, transform 0.3s var(--ease-out-expo), opacity 0.3s, letter-spacing 0.3s;
  animation: wordmark-pop 0.9s var(--ease-out-expo) forwards;
  animation-delay: calc(var(--bw-i) * 0.07s + 0.2s);
  cursor: default;
}
.bw-item:hover {
  color: #fff;
  transform: translateY(-2px) scale(1.06);
  letter-spacing: 0.02em;
}
.brand-caption {
  margin-top: 22px;
  text-align: center;
  font-size: 12px;
  color: var(--text-mute);
  letter-spacing: 0.08em;
  font-family: var(--mono);
}

/* ═══════════════════════════════════════════════════════════
   FEATURED PRODUCTS
   ═══════════════════════════════════════════════════════════ */
.featured-section {
  position: relative;
  padding: 100px 40px 120px;
  max-width: 1280px;
  margin: 0 auto;
}
.featured-head {
  text-align: center;
  margin-bottom: 60px;
}
.featured-eyebrow {
  display: inline-flex; align-items: center; gap: 14px;
  font-size: 11px; font-weight: 600;
  color: var(--coral);
  letter-spacing: 0.3em;
  margin-bottom: 18px;
  font-family: var(--mono);
}
.eyebrow-line {
  width: 36px; height: 1px;
  background: linear-gradient(90deg, transparent, var(--coral));
}
.eyebrow-line:last-child { background: linear-gradient(90deg, var(--coral), transparent); }
.featured-title {
  font-size: clamp(36px, 5vw, 60px);
  font-weight: 700;
  letter-spacing: -0.035em;
  font-variation-settings: 'opsz' 72;
  color: var(--text);
  margin-bottom: 12px;
}
.featured-accent {
  background: linear-gradient(110deg, var(--coral) 0%, var(--lavender) 100%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: shimmer 6s linear infinite;
}
.featured-sub {
  font-size: 14px;
  color: var(--text-mute);
  letter-spacing: 0.02em;
}

.featured-stack {
  display: flex; flex-direction: column;
  gap: 36px;
}

/* ═══════════════════════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════════════════════ */
.foot {
  border-top: 1px solid var(--border);
  padding: 36px 40px;
  background: #000;
}
.foot-row {
  max-width: 1280px;
  margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}
.foot-brand { font-size: 15px; color: var(--text-soft); }
.foot-mid { font-size: 13px; color: var(--text-mute); }
.foot-end { font-size: 12px; color: var(--text-faint); letter-spacing: 0.1em; }

/* ═══════════════════════════════════════════════════════════
   FAB
   ═══════════════════════════════════════════════════════════ */
.fab {
  position: fixed;
  bottom: 32px; right: 32px;
  z-index: 100;
  width: 56px; height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--coral), var(--lavender));
  display: grid; place-items: center;
  color: #000;
  box-shadow: 0 12px 30px rgba(232,180,168,0.40), 0 0 0 1px rgba(255,255,255,0.1) inset;
  transition: transform 0.25s;
}
.fab:hover { transform: translateY(-3px) scale(1.04); }
.fab svg { width: 24px; height: 24px; }
.fab-pulse {
  position: absolute; inset: -2px;
  border-radius: 50%;
  border: 2px solid rgba(232,180,168,0.7);
  animation: dot-pulse 2s ease-out infinite;
}

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 1024px) {
  .head-word { font-size: clamp(70px, 12vw, 140px); }
  .phone-wrap { width: 240px; height: 500px; }
  .head-left { margin-right: -20px; }
  .head-right { margin-left: -20px; }
  .brand-row { grid-template-columns: repeat(4, 1fr); gap: 18px 24px; }
}

@media (max-width: 720px) {
  .nav-pill-group { display: none; }
  .nav-row { padding: 0 20px; }
  .hero { padding: 110px 20px 40px; }
  .hero-stage {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    gap: 12px;
    min-height: auto;
  }
  .head-word { font-size: clamp(60px, 18vw, 96px); margin: 0; justify-self: center; }
  .head-left { font-style: italic; }
  .phone-wrap { width: 220px; height: 460px; }
  .brand-row { grid-template-columns: repeat(4, 1fr); gap: 14px 18px; }
  .bw-item { font-size: 15px; }
  .featured-section { padding: 60px 20px 80px; }
  .hero-cta-form { flex-direction: column; padding: 12px; border-radius: 24px; }
  .hero-trial { width: 100%; justify-content: center; }
  .hero-email { width: 100%; text-align: center; }
}
</style>

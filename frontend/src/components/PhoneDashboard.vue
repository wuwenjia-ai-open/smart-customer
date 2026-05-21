<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const HEAT = ref('¥6,499')
const RATE = ref('+48%')
const PROGRESS = ref(80)
const tickKey = ref(0)

const HISTORY = [
  { name: 'iPhone 16 Pro Max', meta: '今日 · 已比价', icon: '📱', tone: 'coral' },
  { name: 'MacBook Pro M4',    meta: '昨日 · 已收藏', icon: '💻', tone: 'lav' },
]

let timer = null
onMounted(() => {
  timer = setInterval(() => {
    tickKey.value++
    PROGRESS.value = 72 + Math.round(Math.random() * 18)
  }, 8000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="dash">
    <!-- iOS status bar -->
    <div class="dash-status mono">
      <span>9:41</span>
      <span class="dash-status-icons">
        <span class="bar bar-1"/><span class="bar bar-2"/><span class="bar bar-3"/><span class="bar bar-4"/>
        <span class="batt"><span/></span>
      </span>
    </div>

    <!-- Title -->
    <div class="dash-title">
      <div class="dash-search">
        <span class="search-icon">⌕</span>
        <span class="search-placeholder">灵犀 · 推荐</span>
      </div>
    </div>

    <!-- Main card -->
    <div class="dash-card">
      <div class="dc-top">
        <div class="dc-eyebrow">本周热推</div>
        <div class="dc-icon">▲</div>
      </div>
      <div class="dc-label">总热度</div>
      <div class="dc-value-row">
        <span :key="tickKey" class="dc-value mono">{{ HEAT }}</span>
      </div>
      <div class="dc-meta">
        <span class="dc-trend">▲ 比上周 {{ RATE }}</span>
      </div>

      <!-- Progress arc -->
      <div class="dc-arc">
        <svg viewBox="0 0 100 60" class="arc-svg">
          <path d="M 10 50 A 40 40 0 0 1 90 50" stroke="rgba(255,255,255,0.08)" stroke-width="6" fill="none" stroke-linecap="round"/>
          <path
            :key="tickKey"
            d="M 10 50 A 40 40 0 0 1 90 50"
            stroke="url(#arc-grad)"
            stroke-width="6" fill="none" stroke-linecap="round"
            stroke-dasharray="125.6"
            :stroke-dashoffset="125.6 - (PROGRESS / 100) * 125.6"
            class="arc-fg"
          />
          <defs>
            <linearGradient id="arc-grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%"  stop-color="#E8B4A8"/>
              <stop offset="100%" stop-color="#C8C5E0"/>
            </linearGradient>
          </defs>
        </svg>
        <span class="arc-num mono">{{ PROGRESS }}<span class="arc-pct">%</span></span>
      </div>
    </div>

    <!-- Category icons -->
    <div class="dash-cats">
      <div class="cat-grid">
        <div class="cat-cell" v-for="(c, i) in ['📱','⌚','💻','🎧','📷']" :key="i">
          <span class="cat-emoji">{{ c }}</span>
        </div>
      </div>
    </div>

    <!-- History -->
    <div class="dash-history">
      <div class="dh-eyebrow">推荐历史</div>
      <div class="dh-item" v-for="(h, i) in HISTORY" :key="i" :class="`tone-${h.tone}`">
        <span class="dh-icon">{{ h.icon }}</span>
        <div class="dh-text">
          <div class="dh-name">{{ h.name }}</div>
          <div class="dh-meta">{{ h.meta }}</div>
        </div>
        <span class="dh-arrow">›</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dash {
  position: absolute; inset: 0;
  padding: 38px 14px 12px;
  z-index: 3;
  display: flex; flex-direction: column;
  gap: 8px;
  color: #fff;
  font-size: 10px;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(232,180,168,0.10), transparent 55%),
    linear-gradient(180deg, #0A0A0C 0%, #050505 60%, #000 100%);
}

/* Status bar */
.dash-status {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 8px;
  font-size: 10px;
  color: #fff;
}
.dash-status-icons { display: flex; align-items: center; gap: 2px; }
.bar { display: inline-block; width: 2px; background: #fff; border-radius: 1px; }
.bar-1 { height: 4px; }
.bar-2 { height: 6px; }
.bar-3 { height: 8px; }
.bar-4 { height: 10px; }
.batt {
  margin-left: 4px;
  width: 16px; height: 8px;
  border: 1px solid rgba(255,255,255,0.7);
  border-radius: 2px;
  padding: 1px;
  position: relative;
}
.batt::after {
  content: ''; position: absolute; right: -3px; top: 2px;
  width: 2px; height: 2px; background: rgba(255,255,255,0.7); border-radius: 0 1px 1px 0;
}
.batt span { display: block; width: 80%; height: 100%; background: #fff; border-radius: 1px; }

/* Search */
.dash-search {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px;
  background: rgba(255,255,255,0.05);
  border-radius: 999px;
  font-size: 10px;
}
.search-icon { color: var(--coral); font-size: 11px; }
.search-placeholder { color: rgba(255,255,255,0.4); }

/* Main card */
.dash-card {
  background: linear-gradient(180deg, #131316 0%, #0B0B0E 100%);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 10px 12px 14px;
  position: relative;
}
.dc-top { display: flex; justify-content: space-between; align-items: center; }
.dc-eyebrow { font-size: 9px; font-weight: 600; color: var(--coral); letter-spacing: 0.08em; text-transform: uppercase; }
.dc-icon {
  width: 16px; height: 16px; border-radius: 6px;
  background: rgba(232,180,168,0.14);
  color: var(--coral);
  display: grid; place-items: center;
  font-size: 8px;
}
.dc-label { font-size: 9px; color: rgba(255,255,255,0.5); margin-top: 6px; }
.dc-value-row { margin-top: 2px; }
.dc-value {
  font-size: 22px; font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
  animation: tick-up 0.8s var(--ease-out-expo);
  display: inline-block;
}
.dc-meta { margin-top: 2px; }
.dc-trend {
  font-size: 9px; color: var(--coral);
  font-weight: 600;
}

/* Arc */
.dc-arc {
  position: relative;
  margin-top: 6px;
  height: 50px;
}
.arc-svg { width: 100%; height: 100%; }
.arc-fg {
  transition: stroke-dashoffset 1.2s var(--ease-out-expo);
  filter: drop-shadow(0 0 4px rgba(232,180,168,0.5));
}
.arc-num {
  position: absolute;
  bottom: -4px; left: 50%;
  transform: translateX(-50%);
  font-size: 18px; font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
}
.arc-pct { font-size: 10px; color: var(--coral); margin-left: 1px; }

/* Categories */
.dash-cats { margin-top: 2px; }
.cat-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
.cat-cell {
  aspect-ratio: 1;
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.05);
  display: grid; place-items: center;
  transition: background 0.3s, border-color 0.3s;
}
.cat-cell:hover {
  background: rgba(232,180,168,0.08);
  border-color: rgba(232,180,168,0.2);
}
.cat-emoji { font-size: 14px; filter: grayscale(0.2); }

/* History */
.dash-history { margin-top: 2px; }
.dh-eyebrow { font-size: 9px; color: rgba(255,255,255,0.45); letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 4px; }
.dh-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  border: 1px solid transparent;
  margin-bottom: 4px;
  transition: background 0.3s, border-color 0.3s;
}
.dh-item.tone-coral:hover { background: rgba(232,180,168,0.08); border-color: rgba(232,180,168,0.18); }
.dh-item.tone-lav:hover { background: rgba(200,197,224,0.08); border-color: rgba(200,197,224,0.18); }
.dh-icon { font-size: 14px; }
.dh-text { flex: 1; min-width: 0; }
.dh-name { font-size: 10px; font-weight: 600; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dh-meta { font-size: 8px; color: rgba(255,255,255,0.4); margin-top: 1px; }
.dh-arrow { font-size: 14px; color: rgba(255,255,255,0.3); }
</style>

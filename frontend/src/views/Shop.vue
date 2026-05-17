<script setup>
import SplineHero from '@/components/SplineHero.vue'
import ProductSection from '@/components/ProductSection.vue'

const products = [
  {
    name: 'iPhone 16 Pro Max', brand: 'Apple', category: '智能手机',
    price: 9999, spec: 'A18 Pro · 8GB · 256GB',
    description: '钛金属设计，A18 Pro 芯片，48MP Fusion 相机系统，支持 Apple Intelligence，USB-C 接口，灵动岛交互。',
    features: ['A18 Pro 芯片', '48MP 主摄', '5G', '灵动岛', '钛金属'],
    rating: 4.8, reviews: 326, image: '/images/16promax.jpg',
  },
  {
    name: '华为 Mate 70 Pro', brand: '华为', category: '智能手机',
    price: 6999, spec: '麒麟9100 · 12GB · 512GB',
    description: '旗舰影像系统，支持卫星通信，昆仑玻璃面板，HarmonyOS NEXT，AI 隔空操控。',
    features: ['卫星通信', 'XMAGE 影像', '昆仑玻璃', 'AI 隔空操控'],
    rating: 4.7, reviews: 289, image: '/images/HUAWEIMate 70 Pro.jpg',
  },
  {
    name: '小米 15 Ultra', brand: '小米', category: '智能手机',
    price: 6499, spec: '骁龙8 Gen4 · 16GB · 1TB',
    description: '徕卡光学镜头，1 英寸大底主摄，HyperOS 2.0，120W 超级快充，专业影像旗舰。',
    features: ['徕卡影像', '120W 快充', '1 英寸 CMOS', 'HyperOS'],
    rating: 4.6, reviews: 178, image: '/images/xiaoml15 ultra.jpg',
  },
  {
    name: '三星 Galaxy S25 Ultra', brand: '三星', category: '智能手机',
    price: 8999, spec: '骁龙8 Gen4 · 12GB · 256GB',
    description: '2 亿像素主摄，内置 S Pen，Galaxy AI 智能助手，钛金属框架，45W 快充。',
    features: ['2 亿像素', 'S Pen', 'Galaxy AI', '钛金属'],
    rating: 4.7, reviews: 215, image: '/images/SAMSUNG.jpg',
  },
  {
    name: 'MacBook Pro 16 M4', brand: 'Apple', category: '笔记本',
    price: 19999, spec: 'M4 Pro · 32GB · 1TB · 16"',
    description: 'Liquid Retina XDR 显示屏，M4 Pro 芯片，22 小时电池续航，专业创作者首选。',
    features: ['M4 Pro 芯片', '32GB 内存', 'XDR 显示屏', '22h 续航'],
    rating: 4.9, reviews: 156, image: '/images/MacBook Pro.jpg',
  },
  {
    name: '华为 MateBook X Pro', brand: '华为', category: '笔记本',
    price: 10999, spec: 'Ultra 9 · 32GB · 1TB · 14.2"',
    description: 'OLED 原色全面屏，超级终端多设备协同，压力触控板，超轻薄金属机身。',
    features: ['OLED 全面屏', '超级终端', '压力触控板', '超轻薄'],
    rating: 4.7, reviews: 134, image: '/images/MacBookXPro.jpg',
  },
  {
    name: 'ROG 幻 16 Air', brand: '华硕', category: '笔记本',
    price: 14999, spec: 'RTX 4070 · 32GB · 1TB · 16"',
    description: '专业创作本，RTX 4070 显卡，2.5K 240Hz 星云屏，重量仅 1.85kg。',
    features: ['RTX 4070', '240Hz 星云屏', '1.85kg', '专业创作'],
    rating: 4.5, reviews: 67, image: '/images/R0G幻6.jpg',
  },
]

function scrollToProducts() {
  document.getElementById('products')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<template>
  <div>
    <SplineHero @scroll-down="scrollToProducts" />

    <div id="products">
      <div class="mx-auto max-w-6xl py-8 text-center">
        <p class="text-xs font-medium tracking-[0.3em] text-purple-400/60 uppercase">Explore Products</p>
      </div>
      <ProductSection
        v-for="(product, index) in products"
        :key="product.name"
        :product="product"
        :index="index"
        :image="product.image"
      />
    </div>

    <footer class="border-t border-white/[0.04] py-16 text-center">
      <p class="text-sm text-neutral-600">灵犀智购 · AI 智能电子产品选购平台</p>
    </footer>
  </div>
</template>

<template>
  <div>
    <div class="hero">
      <h2><span>智能家居</span> · 好物精选</h2>
      <p>精选 20 款智能家居产品，AI 客服随时在线帮你选</p>
    </div>
    <div class="cat-row">
      <button
        v-for="cat in CATS" :key="cat"
        :class="['cat-chip', { active: selectedCategory === cat }]"
        @click="selectCategory(cat)"
      >{{ cat }}</button>
    </div>
    <div class="sec-hd">
      <h3>{{ selectedCategory || '全部产品' }}</h3>
      <span class="count">共 {{ filteredProducts.length }} 款</span>
    </div>
    <div class="product-grid">
      <ProductCard v-for="(p, i) in filteredProducts" :key="i" :product="p" />
    </div>
  </div>
</template>

<script setup>
import ProductCard from './ProductCard.vue'
import { useProducts } from '../composables/useProducts.js'

const { CATS, selectedCategory, filteredProducts, selectCategory } = useProducts()
</script>

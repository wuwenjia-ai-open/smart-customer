<template>
  <div class="p-card">
    <div class="p-cat">{{ product.cat }}</div>
    <div class="p-name">{{ product.name }}</div>
    <div class="p-desc">{{ product.desc }}</div>
    <div class="p-foot">
      <div>
        <div class="p-price">{{ product.price }}<span class="u">元</span></div>
      </div>
      <div class="p-meta">
        库存<span :class="{ lo: product.stock < 50 }">{{ product.stock }}</span>件<br>{{ product.w }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ product: Object })
</script>

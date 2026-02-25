<template>
  <div>
    <h3>推荐商品</h3>
    <div class="waterfall">
      <div v-for="item in items" :key="item.product_id" class="card" @click="$emit('item-click', item)">
        <img :src="`${baseUrl}${item.image_url}`" :alt="item.name" />
        <div class="meta">
          <strong>{{ item.name }}</strong>
          <p>¥ {{ item.price }}</p>
          <small>{{ item.reason }}</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, default: () => [] },
})
const baseUrl = 'http://localhost:8000'
defineEmits(['item-click'])
</script>

<style scoped>
.waterfall { column-count: 3; column-gap: 12px; }
.card { break-inside: avoid; margin-bottom: 12px; border: 1px solid #334155; border-radius: 10px; overflow: hidden; background: #0b1220; cursor: pointer; }
img { width: 100%; display: block; }
.meta { padding: 8px; }
small { color: #94a3b8; }
</style>

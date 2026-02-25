<template>
  <div class="app-shell">
    <header class="topbar">多模态个性化推荐系统</header>
    <main class="layout">
      <aside class="left-panel">
        <EchartsDashboard :user-id="userId" :base-url="baseUrl" />
      </aside>
      <section class="right-panel">
        <ProductList :items="recommendItems" @item-click="handleItemClick" />
      </section>
      <DeepSeekChat class="chat-float" :loading="loading" @send="handleQuery" />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import ProductList from './components/ProductList.vue'
import DeepSeekChat from './components/DeepSeekChat.vue'
import EchartsDashboard from './components/EchartsDashboard.vue'

const baseUrl = 'http://localhost:8000'
const userId = ref('user_001')
const recommendItems = ref([])
const loading = ref(false)

const handleQuery = async (query) => {
  if (!query) return
  loading.value = true
  try {
    const { data } = await axios.post(`${baseUrl}/api/recommend`, {
      user_id: userId.value,
      query,
    })
    recommendItems.value = data.items || []
  } finally {
    loading.value = false
  }
}

const handleItemClick = async (item) => {
  await axios.post(`${baseUrl}/api/log_action`, {
    user_id: userId.value,
    product_id: item.product_id,
    action: 'click',
  })
}
</script>

<style scoped>
.app-shell { min-height: 100vh; background: #0f172a; color: #e2e8f0; }
.topbar { height: 60px; display: flex; align-items: center; padding: 0 20px; font-weight: 700; border-bottom: 1px solid #1e293b; }
.layout { display: grid; grid-template-columns: 340px 1fr; gap: 16px; padding: 16px; position: relative; }
.left-panel, .right-panel { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 12px; }
.chat-float { position: fixed; right: 20px; bottom: 20px; width: 360px; }
</style>

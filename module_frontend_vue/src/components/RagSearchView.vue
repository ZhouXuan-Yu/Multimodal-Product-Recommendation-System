<template>
  <div class="rag-shell">
    <header class="header">
      <div>
        <h3 class="title">本地向量检索（RAG 召回）</h3>
        <p class="subtitle">直接从本地 Chroma 向量库检索 Top-K（不走 LLM），用于验证 3000 条图文数据的多样性与可检索性。</p>
      </div>
      <div class="controls">
        <input
          v-model="q"
          class="search-input"
          placeholder="输入关键词：例如 黑色 户外 鞋 防水 轻量..."
          @keyup.enter="doSearch"
        />
        <select v-model.number="topK" class="select">
          <option :value="10">Top-10</option>
          <option :value="20">Top-20</option>
          <option :value="50">Top-50</option>
        </select>
        <button class="btn" :disabled="loading || !q.trim()" @click="doSearch">
          {{ loading ? '检索中...' : '检索' }}
        </button>
      </div>
    </header>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="items.length" class="grid">
      <div v-for="item in items" :key="item.product_id" class="card" @click="$emit('item-click', item)">
        <div class="img-wrap">
          <img :src="resolveImageUrl(item.image_url)" :alt="item.name" loading="lazy" />
        </div>
        <div class="meta">
          <div class="row">
            <strong class="name" :title="item.name">{{ item.name }}</strong>
            <span class="price">¥ {{ item.price }}</span>
          </div>
          <div class="row muted">
            <span class="badge">{{ item.category }}</span>
            <span class="score" v-if="item.distance !== null && item.distance !== undefined">
              distance: {{ Number(item.distance).toFixed(4) }}
            </span>
          </div>
          <p class="desc">{{ item.description }}</p>
          <div class="row tiny">
            <span class="pid">{{ item.product_id }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty">
      <span v-if="loading">正在检索...</span>
      <span v-else>暂无结果。先输入关键词并点击“检索”。</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ragSearch } from '../api'

defineEmits(['item-click'])

const q = ref('适合户外运动的黑色鞋子')
const topK = ref(20)
const items = ref([])
const loading = ref(false)
const error = ref('')

const resolveImageUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return url
}

const doSearch = async () => {
  error.value = ''
  const query = q.value.trim()
  if (!query) return
  loading.value = true
  try {
    const res = await ragSearch({ q: query, top_k: topK.value })
    items.value = res?.data?.items || []
  } catch (e) {
    items.value = []
    error.value = '检索失败：请确认后端已启动、向量库已完成入库（data/vector_store），并检查控制台日志。'
    // eslint-disable-next-line no-console
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.rag-shell {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(209, 213, 219, 0.6);
}

.title {
  font-size: 16px;
  font-weight: 650;
  margin: 0;
}

.subtitle {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input {
  width: min(520px, 42vw);
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.85);
  outline: none;
  transition: all 0.2s ease;
}

.search-input:focus {
  border-color: rgba(249, 115, 22, 0.55);
  box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.12);
}

.select {
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.85);
}

.btn {
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(249, 115, 22, 0.6);
  background: linear-gradient(120deg, #fff7ed, #fffbeb);
  color: var(--accent-deep);
  font-weight: 650;
  cursor: pointer;
  transition: transform 0.08s ease, opacity 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn:active:not(:disabled) {
  transform: translateY(1px);
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  overflow: auto;
  padding-right: 4px;
}

.card {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.img-wrap {
  width: 100%;
  aspect-ratio: 1 / 1;
  background: rgba(2, 6, 23, 0.03);
}

.img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.meta {
  padding: 10px 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.name {
  font-size: 13px;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-deep);
}

.muted {
  color: var(--text-muted);
  font-size: 12px;
}

.badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.12);
  color: rgba(124, 45, 18, 0.95);
  border: 1px solid rgba(249, 115, 22, 0.18);
}

.score {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.desc {
  margin: 0;
  font-size: 12px;
  color: rgba(51, 65, 85, 0.9);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tiny {
  font-size: 11px;
  color: rgba(100, 116, 139, 0.9);
}

.pid {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.error {
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.7);
  border: 1px solid rgba(220, 38, 38, 0.25);
  padding: 10px 12px;
  border-radius: 12px;
}

.empty {
  color: var(--text-muted);
  padding: 14px 2px;
}

@media (max-width: 1280px) {
  .grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .search-input {
    width: 100%;
  }
  .header {
    flex-direction: column;
    align-items: stretch;
  }
  .controls {
    width: 100%;
  }
}
</style>


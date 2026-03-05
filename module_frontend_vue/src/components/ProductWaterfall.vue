<template>
  <div class="mall-root">
    <!-- 顶部搜索与筛选条，可与 AI 导购联动 -->
    <section class="search-bar glass-panel">
      <input
        v-model="keyword"
        class="search-input"
        type="text"
        placeholder="搜索你感兴趣的商品，如：复古相机、春季风衣..."
        @keyup.enter="handleSearch"
      />
      <select v-model="category" class="category-select">
        <option value="all">全部类目</option>
        <option value="men's clothing">男装</option>
        <option value="women's clothing">女装</option>
        <option value="jewelery">珠宝配饰</option>
        <option value="electronics">数码电子</option>
      </select>
      <button class="search-btn" @click="handleSearch">搜索</button>
    </section>

    <!-- 瀑布流商品列表 -->
    <section class="waterfall-wrapper soft-scrollbar">
      <div class="waterfall" v-if="products.length">
        <article
          v-for="item in products"
          :key="item.product_id"
          class="card glass-panel"
          @click="onItemClick(item)"
        >
          <div class="image-wrapper">
            <!-- 原生 lazy loading；如需更强大支持可换为 IntersectionObserver 懒加载 -->
            <img
              :src="resolveImageUrl(item)"
              :alt="item.name"
              loading="lazy"
            />
            <span class="badge-ai">
              <span class="gradient-text">DeepSeek 推荐</span>
            </span>
          </div>
          <div class="meta">
            <h3 class="title" :title="item.name">{{ item.name }}</h3>
            <p class="price">¥ {{ formatPrice(item.price) }}</p>
            <!-- 个性化偏好标记：喜欢 / 一般 / 不喜欢 -->
            <div class="preference-bar" @click.stop>
              <button
                class="pref-btn pref-dislike"
                :disabled="preferenceSubmitting"
                @click="markPreference(item, 'dislike', 0)"
              >
                不喜欢
              </button>
              <button
                class="pref-btn pref-normal"
                :disabled="preferenceSubmitting"
                @click="markPreference(item, 'normal', 1)"
              >
                一般
              </button>
              <button
                class="pref-btn pref-like"
                :disabled="preferenceSubmitting"
                @click="markPreference(item, 'like', 2)"
              >
                喜欢
              </button>
            </div>
            <!-- AI 推荐理由：使用区别于普通描述的专属样式 -->
            <p class="reason">
              <span class="reason-label">AI 推荐理由</span>
              <span class="reason-text">
                {{ item.reason || '基于您的近期偏好，系统为您智能筛选出的高匹配商品。' }}
              </span>
            </p>
          </div>
        </article>
      </div>

      <!-- 空状态：在非加载中且没有商品时展示 -->
      <div v-else class="empty-state">
        <p class="empty-title">暂无相关商品</p>
        <p class="empty-subtitle">
          试试换一个关键词，比如「蓝牙耳机」「春季外套」，或删除部分限定词。
        </p>
      </div>

      <!-- 底部分页条：上一页 / 下一页 / 首页 -->
      <div class="pagination-bar" v-if="products.length">
        <button
          class="pagination-btn"
          :disabled="page <= 1 || loadingMore"
          @click="goFirst"
        >
          首页
        </button>
        <button
          class="pagination-btn"
          :disabled="page <= 1 || loadingMore"
          @click="goPrev"
        >
          ‹ 上一页
        </button>
        <button
          class="pagination-btn"
          :disabled="noMore || loadingMore"
          @click="goNext"
        >
          下一页 ›
        </button>
        <span class="page-info">第 {{ page }} 页</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { fetchRecommendations, logUserAction } from '../api'

const props = defineProps({
  userId: {
    type: String,
    required: true,
  },
  // 外部（例如 AI 聊天）传入的 query，用于联动刷新推荐
  query: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['item-click'])

const products = ref([])
const page = ref(1)
// 与后端 RecommendRequest.page_size 的约束保持一致（最大 50）
// 一页展示 6 列 × 8~9 行 ≈ 48~54 个商品；这里取 50，避免触发 422 校验错误
const pageSize = 50
const loadingMore = ref(false)
const noMore = ref(false)
const preferenceSubmitting = ref(false)

// 搜索关键词（初始与 props.query 保持同步）
const keyword = ref('')
const category = ref('all')

// 格式化价格
const formatPrice = (value) => {
  if (value == null) return '--'
  return Number(value).toFixed(2)
}

// 拼接图片 URL，兼容后端返回的相对路径
const resolveImageUrl = (item) => {
  if (!item) return ''
  const url = item.image_url || item.image || ''
  if (!url) return ''
  if (url.startsWith('http')) return url
  // 默认返回相对路径（/static/images/xxx），开发环境由 Vite proxy 转发，生产环境可同源部署
  return url
}

// 实际向后端请求推荐列表的核心函数（分页模式）
const loadRecommendations = async (targetPage = 1) => {
  if (loadingMore.value) return

  loadingMore.value = true
  try {
    console.debug('[ProductWaterfall] 即将请求推荐列表', {
      user_id: props.userId,
      keyword: keyword.value,
      externalQuery: props.query,
      category: category.value,
      targetPage,
      pageSize,
    })
    const { data } = await fetchRecommendations({
      user_id: props.userId,
      query: keyword.value || props.query || '',
      page: targetPage,
      page_size: pageSize,
      category: category.value,
    })

    const items = data.items || data.recommendations || []

    console.debug('[ProductWaterfall] 收到推荐结果', {
      targetPage,
      receivedCount: items.length,
      raw: data,
    })

    products.value = items
    page.value = targetPage

    // 优先使用后端返回的 total 字段判断是否还有更多数据；
    // 若未提供 total，则回退到“当前页条数 < pageSize 视为尾页”的策略
    const total = typeof data.total === 'number' ? data.total : 0
    if (total > 0) {
      noMore.value = targetPage * pageSize >= total
    } else {
      noMore.value = !items.length || items.length < pageSize
    }
  } catch (e) {
    console.error('加载推荐商品失败', e)
  } finally {
    loadingMore.value = false
  }
}

// 处理搜索：将当前关键字作为 query 重新触发推荐
const handleSearch = () => {
  noMore.value = false
  loadRecommendations(1)
}

// 商品点击时，向父组件抛出事件，便于统一日志上报
const onItemClick = (item) => {
  emit('item-click', item)
}

// 用户个性化偏好标记：将行为带权重上报到后端
const markPreference = async (item, label, weight) => {
  if (!item || !item.product_id || preferenceSubmitting.value) return

  preferenceSubmitting.value = true
  try {
    await logUserAction({
      user_id: props.userId,
      product_id: item.product_id,
      action: label,
      weight,
    })
  } catch (e) {
    console.error('上报偏好失败', e)
  } finally {
    preferenceSubmitting.value = false
  }
}

// 分页按钮：上一页 / 下一页 / 首页
const goFirst = () => {
  if (page.value === 1) return
  console.debug('[ProductWaterfall] 分页跳转：首页')
  loadRecommendations(1)
}

const goPrev = () => {
  if (page.value <= 1) return
  console.debug('[ProductWaterfall] 分页跳转：上一页', { currentPage: page.value })
  loadRecommendations(page.value - 1)
}

const goNext = () => {
  if (noMore.value) return
  console.debug('[ProductWaterfall] 分页跳转：下一页', {
    currentPage: page.value,
    noMore: noMore.value,
  })
  loadRecommendations(page.value + 1)
}

// 当外部 query 发生变化时（例如用户在 AI 聊天中输入“复古相机”），重置并重新拉取数据
watch(
  () => props.query,
  (val) => {
    if (val != null) {
      keyword.value = val
      noMore.value = false
      loadRecommendations(1)
    }
  },
  { immediate: true },
)

onMounted(() => {
  // 首次进入时，无论是否传入 query，都以当前 keyword / query 为条件加载第 1 页
  loadRecommendations(1)
})

onBeforeUnmount(() => {
  // 预留清理逻辑（当前分页模式下无需特殊处理）
})
</script>

<style scoped>
.mall-root {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.search-bar {
  display: flex;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 10px 28px rgba(15, 23, 42, 0.04),
    0 0 0 1px rgba(226, 232, 240, 0.9);
}

.search-input {
  flex: 1;
  border-radius: 999px;
  border: none;
  background: rgba(248, 250, 252, 0.96);
  padding: 9px 14px;
  font-size: 13px;
  color: #111827;
  outline: none;
  transition: box-shadow 0.16s ease, background-color 0.16s ease, transform 0.12s ease;
}

.search-input::placeholder {
  color: #9ca3af;
}

.search-input:focus {
  box-shadow:
    0 0 0 1px rgba(249, 115, 22, 0.4),
    0 0 0 4px rgba(249, 115, 22, 0.12);
  background: #ffffff;
  transform: translateY(-1px);
}

.search-btn {
  padding: 0 18px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(to right, #f97316, #fb923c);
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(248, 113, 22, 0.4);
  transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.12s ease;
}

.category-select {
  min-width: 120px;
  border-radius: 999px;
  border: none;
  background: rgba(248, 250, 252, 0.96);
  padding: 8px 10px;
  font-size: 12px;
  color: #374151;
  outline: none;
}

.search-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(248, 113, 22, 0.55);
}

.search-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(248, 113, 22, 0.35);
}

.waterfall-wrapper {
  flex: 1;
  overflow: auto;
  padding: 6px 0 0;
}

.waterfall {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px 10px;
}

.card {
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(229, 231, 235, 0.9);
  box-shadow:
    0 8px 20px rgba(15, 23, 42, 0.04),
    0 0 0 1px rgba(255, 255, 255, 0.7);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.card:hover {
  transform: translateY(-3px);
  border-color: #f97316;
  box-shadow:
    0 14px 28px rgba(15, 23, 42, 0.12),
    0 0 0 1px rgba(249, 115, 22, 0.2);
}

.image-wrapper {
  position: relative;
  overflow: hidden;
  background: #f9fafb;
}

.image-wrapper img {
  width: 100%;
  display: block;
  object-fit: cover;
}

.badge-ai {
  position: absolute;
  left: 8px;
  bottom: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(17, 24, 39, 0.82);
  font-size: 11px;
  color: #fef3c7;
}

.meta {
  padding: 10px 10px 12px;
}

.title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
  line-height: 1.4;
  color: #111827;
}

.price {
  font-size: 15px;
  font-weight: 700;
  color: #f97316;
  margin-bottom: 6px;
}

.preference-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
}

.pref-btn {
  flex: 1;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  font-size: 10px;
  padding: 2px 4px;
  cursor: pointer;
  color: #4b5563;
  transition: background-color 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}

.pref-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.pref-dislike:hover {
  border-color: #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.pref-normal:hover {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}

.pref-like:hover {
  border-color: #fed7aa;
  background: #fffbeb;
  color: #c2410c;
}

.reason {
  font-size: 11px;
  color: #6b7280;
  border-radius: 6px;
  padding: 6px 8px;
  background: #f9fafb;
}

.reason-label {
  display: inline-block;
  margin-right: 4px;
  padding: 1px 6px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
}

.reason-text {
  color: #4b5563;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 0 12px;
}

.pagination-btn {
  min-width: 72px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  font-size: 12px;
  color: #4b5563;
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease, color 0.12s ease,
    box-shadow 0.12s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: #ffffff;
  border-color: #f97316;
  color: #c2410c;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.page-info {
  font-size: 12px;
  color: #9ca3af;
}

@media (max-width: 1280px) {
  .waterfall {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .waterfall {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .waterfall {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 540px) {
  .waterfall {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>


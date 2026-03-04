<template>
  <div class="app-shell">
    <!-- 顶部导航 & 视图切换 -->
    <header class="topbar glass-panel">
      <div class="brand">
        <span class="dot"></span>
        <span class="title gradient-text">多模态个性化推荐系统</span>
      </div>
      <nav class="nav-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-btn', { active: activeView === tab.key }]"
          @click="activeView = tab.key"
        >
          <span class="tab-label" :class="{ 'text-glow': activeView === tab.key }">
            {{ tab.label }}
          </span>
        </button>
      </nav>
      <div class="user-pill">
        <span class="user-id-label">User</span>
        <span class="user-id">{{ userId }}</span>
      </div>
    </header>

    <!-- 主体区域：根据 activeView 展示不同视图 -->
    <main class="layout">
      <!-- 视图 A：智能推荐商城 -->
      <section v-if="activeView === 'mall'" class="panel panel-mall glass-elevated">
        <header class="panel-header">
          <div>
            <h2>智能推荐商城</h2>
            <p class="subtitle">基于多模态画像 & DeepSeek 推理的实时个性化推荐</p>
          </div>
        </header>

        <ProductWaterfall
          :user-id="userId"
          :query="mallQuery"
          @item-click="handleItemClick"
        />
      </section>

      <!-- 视图 B：本地向量检索（RAG 召回） -->
      <section v-else-if="activeView === 'rag'" class="panel panel-rag glass-elevated">
        <header class="panel-header">
          <div>
            <h2>本地向量检索</h2>
            <p class="subtitle">直接从本地 Chroma 向量库检索 Top-K（不走 LLM）</p>
          </div>
        </header>

        <RagSearchView @item-click="handleItemClick" />
      </section>

      <!-- 视图 C：个人数据洞察中心 -->
      <section v-else class="panel panel-analytics glass-elevated">
        <header class="panel-header">
          <div>
            <h2>个人数据洞察中心</h2>
            <p class="subtitle">多维度行为轨迹 · 类目偏好 · 转化漏斗可视分析</p>
          </div>
        </header>

        <InsightCenter :user-id="userId" />
      </section>
    </main>

    <!-- 悬浮 DeepSeek AI 智能导购对话框 -->
    <AIChatWidget
      class="chat-float"
      :user-id="userId"
      @recommend-query="handleMallQueryFromChat"
      @item-click="handleItemClick"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import InsightCenter from './components/InsightCenter.vue'
import ProductWaterfall from './components/ProductWaterfall.vue'
import AIChatWidget from './components/AIChatWidget.vue'
import RagSearchView from './components/RagSearchView.vue'
import { logUserAction } from './api'

// 模拟当前登录用户 ID，真实项目中可从登录态或后端获取
const userId = ref('user_001')

// 当前激活的视图：mall | analytics
const activeView = ref('mall')

const tabs = [
  { key: 'mall', label: '智能推荐商城' },
  { key: 'rag', label: '本地向量检索' },
  { key: 'analytics', label: '个人数据洞察中心' },
]

// 商城区搜索 / AI 导购联动使用的 query
const mallQuery = ref('')

// 从 AI 聊天组件中收到“推荐意图”，用于刷新商城视图
const handleMallQueryFromChat = (queryText) => {
  mallQuery.value = queryText || ''
  activeView.value = 'mall'
}

// 商品点击时上报行为日志，形成“推荐 → 点击 → 数据回流”的闭环
const handleItemClick = async (item) => {
  try {
    await logUserAction({
      user_id: userId.value,
      product_id: item.product_id,
      action: 'click',
      // 可以附加更多上下文信息，方便后端做埋点分析
      extra: {
        from: 'mall_or_chat',
      },
    })
  } catch (e) {
    console.warn('上报点击日志失败，可忽略不影响主流程', e)
  }
}
</script>

.style-reset {
  /* 占位，避免空 style 块被移除 */
}

<style scoped>
.app-shell {
  min-height: 100vh;
  color: var(--text-main);
  display: flex;
  flex-direction: column;
  padding: 18px 22px 26px;
  gap: 14px;
}

.topbar {
  position: sticky;
  top: 10px;
  inset-inline: 0;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  z-index: 20;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: radial-gradient(circle, var(--accent-orange), var(--accent-deep));
  box-shadow: 0 0 10px rgba(249, 115, 22, 0.7);
}

.title {
  font-weight: 700;
  letter-spacing: 0.06em;
  font-size: 16px;
}

.nav-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  position: relative;
  padding: 6px 18px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
}

.tab-btn:hover {
  color: var(--accent-deep);
  border-color: rgba(251, 146, 60, 0.35);
  background: var(--accent-orange-bg);
}

.tab-btn.active {
  color: var(--accent-deep);
  border-color: rgba(249, 115, 22, 0.8);
  background: linear-gradient(120deg, #fff7ed, #fffbeb);
  box-shadow:
    0 10px 25px rgba(249, 115, 22, 0.2),
    0 0 0 1px rgba(248, 250, 252, 0.7);
}

.tab-btn::after {
  content: '';
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 4px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    rgba(248, 171, 98, 0),
    rgba(249, 115, 22, 0.95),
    rgba(248, 171, 98, 0)
  );
  opacity: 0;
  transform: scaleX(0.4);
  transform-origin: center;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.tab-btn.active::after {
  opacity: 1;
  transform: scaleX(1);
}

.tab-label {
  position: relative;
  z-index: 1;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
  font-size: 12px;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.04);
}

.user-id-label {
  color: var(--text-subtle);
}

.user-id {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'SF Mono', ui-monospace;
  color: var(--accent-deep);
}

.layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel {
  flex: 1;
  padding: 16px 18px 18px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(209, 213, 219, 0.6);
}

.panel-header h2 {
  font-size: 19px;
  font-weight: 600;
}

.subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-muted);
}

.panel-mall {
  /* 可以在后续加入额外商城特化样式 */
}

.panel-analytics {
  /* 可以在后续加入额外分析特化样式 */
}

.chat-float {
  position: fixed;
  right: 20px;
  bottom: 18px;
  width: 360px;
  max-height: 70vh;
  z-index: 30;
}

@media (max-width: 1024px) {
  .layout {
    padding: 0;
  }

  .panel {
    padding: 12px 10px 14px;
  }

  .chat-float {
    width: calc(100% - 24px);
    right: 12px;
    bottom: 14px;
  }
}
</style>


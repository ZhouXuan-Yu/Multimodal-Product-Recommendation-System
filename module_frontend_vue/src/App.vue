<template>
  <div class="app-shell">
    <!-- 顶部导航 & 视图切换（未登录时仅展示品牌和占位用户信息） -->
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
      <div class="user-pill" :class="{ 'is-clickable': !!authUser, 'has-menu': !!authUser }">
        <div class="user-pill-main">
          <span class="user-id-label">{{ authUser ? 'User' : 'Guest' }}</span>
          <span class="user-id">
            {{ authUser ? authUser.email : '未登录' }}
          </span>
          <span v-if="authUser" class="user-chevron">▾</span>
        </div>

        <!-- 下拉菜单：仅登录后可见，hover 展开 -->
        <div v-if="authUser" class="user-menu">
          <button
            type="button"
            class="user-menu-item"
            @click="activeView = 'profile'"
          >
            个人信息
          </button>
          <button
            type="button"
            class="user-menu-item is-danger"
            @click="handleLogout"
          >
            退出登录
          </button>
        </div>
      </div>
    </header>

    <!-- 主体区域：未登录时展示登录页 / 注册页，已登录时展示业务视图 -->
    <main class="layout">
      <!-- 未登录：展示登录 / 注册界面 -->
      <LoginView
        v-if="!authUser && authView === 'login'"
        @login-success="handleLoginSuccess"
        @switch-view="authView = $event"
      />
      <RegisterView
        v-else-if="!authUser && authView === 'register'"
        @register-success="handleLoginSuccess"
        @switch-view="authView = $event"
      />

      <!-- 已登录时的主业务区域（未登录时不渲染任何内部功能页） -->
      <!-- 视图 A：智能推荐商城（保持组件挂载，只在翻页等交互时重新请求数据） -->
      <section
        v-if="authUser"
        v-show="activeView === 'mall'"
        class="panel panel-mall glass-elevated"
      >
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
      <section
        v-if="authUser"
        v-show="activeView === 'rag'"
        class="panel panel-rag glass-elevated"
      >
        <header class="panel-header">
          <div>
            <h2>本地向量检索</h2>
            <p class="subtitle">直接从本地 Chroma 向量库检索 Top-K（不走 LLM）</p>
          </div>
        </header>

        <RagSearchView @item-click="handleItemClick" />
      </section>

      <!-- 视图 C：个人数据洞察中心 -->
      <section
        v-if="authUser"
        v-show="activeView === 'analytics'"
        class="panel panel-analytics glass-elevated"
      >
        <header class="panel-header">
          <div>
            <h2>个人数据洞察中心</h2>
            <p class="subtitle">多维度行为轨迹 · 类目偏好 · 转化漏斗可视分析</p>
          </div>
        </header>

        <InsightCenter :user-id="userId" />
      </section>
      <!-- 视图 D：我的订单 -->
      <section
        v-if="authUser"
        v-show="activeView === 'orders'"
        class="panel panel-orders glass-elevated"
      >
        <OrderCenter :user-id="userId" />
      </section>

      <!-- 视图 E：购物车结算页 -->
      <section
        v-if="authUser"
        v-show="activeView === 'cart'"
        class="panel panel-cart glass-elevated"
      >
        <CartCheckout
          :items="cartItems"
          :submitting="submittingOrder"
          @update:items="updateCartItems"
          @back-to-mall="activeView = 'mall'"
          @submit-order="handleSubmitOrder"
        />
      </section>

      <!-- 视图 F：个人信息 -->
      <section
        v-if="authUser"
        v-show="activeView === 'profile'"
        class="panel panel-profile glass-elevated"
      >
        <header class="panel-header">
          <div>
            <h2>个人信息</h2>
            <p class="subtitle">当前登录账号的基础信息与画像说明</p>
          </div>
        </header>
        <div class="profile-body">
          <div class="profile-card">
            <div class="profile-row">
              <span class="profile-label">登录邮箱</span>
              <span class="profile-value">{{ authUser?.email || '-' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">昵称</span>
              <span class="profile-value">{{ authUser?.display_name || '未设置' }}</span>
            </div>
            <div class="profile-row">
              <span class="profile-label">用户 ID</span>
              <span class="profile-value mono">{{ userId }}</span>
            </div>
          </div>
          <div class="profile-desc">
            <h3>画像与数据说明</h3>
            <p>
              当前 Demo 环境下，你的浏览、加购与下单行为仅用于本地个性化推荐与行为分析，不会上传到真实生产环境。
            </p>
            <p>
              后续可以在「个人数据洞察中心」中查看你的行为轨迹、偏好分布和转化漏斗。
            </p>
          </div>
        </div>
      </section>
    </main>

    <!-- 悬浮 DeepSeek AI 智能导购对话框 -->
    <AIChatWidget
      v-if="authUser"
      class="chat-float"
      :user-id="userId"
      @recommend-query="handleMallQueryFromChat"
      @item-click="handleItemClick"
    />
    <!-- 仿淘宝风格的加购弹窗 -->
    <CartModal
      :visible="showCartModal"
      :product="selectedProduct"
      @close="showCartModal = false"
      @add-to-cart="addToCart"
      @checkout="checkoutNow"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import InsightCenter from './components/InsightCenter.vue'
import ProductWaterfall from './components/ProductWaterfall.vue'
import AIChatWidget from './components/AIChatWidget.vue'
import RagSearchView from './components/RagSearchView.vue'
import CartModal from './components/CartModal.vue'
import CartCheckout from './components/CartCheckout.vue'
import OrderCenter from './components/OrderCenter.vue'
import LoginView from './components/LoginView.vue'
import RegisterView from './components/RegisterView.vue'
import { logUserAction, previewOrder, createOrder, payOrder } from './api'
import { loadAuthUser, saveAuthUser, clearAuthUser } from './authStorage'

// 认证状态：当前登录用户 & 当前认证视图（login / register）
const authUser = ref(loadAuthUser())
const authView = ref(authUser.value ? 'none' : 'login')

// 当前登录用户 ID（用于传给各业务组件）
const userId = ref(authUser.value ? authUser.value.email || 'guest' : 'guest')

// 当前激活的主业务视图：mall | rag | analytics | orders | cart | profile
const activeView = ref(authUser.value ? 'mall' : 'mall')

const tabs = [
  { key: 'mall', label: '智能推荐商城' },
  { key: 'rag', label: '本地向量检索' },
  { key: 'analytics', label: '个人数据洞察中心' },
  { key: 'orders', label: '我的订单' },
  { key: 'cart', label: '购物车结算' },
]

// 后续登录 / 注册成功时会调用的辅助函数
const handleLoginSuccess = (user) => {
  authUser.value = user
  userId.value = user?.email || 'guest'
  saveAuthUser(user)
  authView.value = 'none'
  activeView.value = 'mall'
}

const handleLogout = () => {
  authUser.value = null
  userId.value = 'guest'
  clearAuthUser()
  authView.value = 'login'
  activeView.value = 'mall'
}

// 商城区搜索 / AI 导购联动使用的 query
const mallQuery = ref('')

// 购物车状态
const showCartModal = ref(false)
const selectedProduct = ref(null)
const cartItems = ref([])
const submittingOrder = ref(false)
const lastOrder = ref(null)

// 从 AI 聊天组件中收到“推荐意图”，用于刷新商城视图
const handleMallQueryFromChat = (queryText) => {
  mallQuery.value = queryText || ''
  activeView.value = 'mall'
}

// 商品点击时：上报点击日志并打开加购弹窗
const handleItemClick = async (item) => {
  selectedProduct.value = item
  showCartModal.value = true

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

// 加入购物车
const addToCart = ({ product, quantity }) => {
  if (!product) return
  const idx = cartItems.value.findIndex((r) => r.product.product_id === product.product_id)
  if (idx >= 0) {
    cartItems.value[idx].quantity += quantity
  } else {
    cartItems.value.push({ product, quantity })
  }
  showCartModal.value = false
}

// 立即结算：加入购物车并跳转到结算页
const checkoutNow = (payload) => {
  addToCart(payload)
  activeView.value = 'cart'
}

const updateCartItems = (next) => {
  cartItems.value = next
}

// 从购物车发起下单流程：预览 → 用户确认 → 创建订单 → 可选模拟支付
const handleSubmitOrder = async () => {
  if (!cartItems.value.length || submittingOrder.value) return

  const items = cartItems.value.map((row) => ({
    product_id: row.product.product_id,
    quantity: row.quantity,
  }))

  const totalCount = cartItems.value.reduce((sum, row) => sum + row.quantity, 0)
  const totalAmount = cartItems.value.reduce(
    (sum, row) => sum + (row.product.price || 0) * row.quantity,
    0,
  )

  const payload = {
    user_id: userId.value,
    currency: 'CNY',
    note: null,
    items,
  }

  submittingOrder.value = true
  try {
    // 1）预览订单，获取 AI 摘要与总价校验
    const previewResp = await previewOrder(payload)
    const previewData = previewResp.data || {}
    const previewSummary = previewData.summary || '系统已根据你的偏好为本次组合做了智能评估。'

    const ok = window.confirm(
      [
        `本次共 ${totalCount} 件商品，合计金额约 ¥${totalAmount.toFixed(2)}。`,
        '',
        'AI 订单摘要：',
        previewSummary,
        '',
        '确认现在创建订单吗？',
      ].join('\n'),
    )
    if (!ok) return

    // 2）正式创建订单
    const createResp = await createOrder(payload)
    let order = (createResp.data && createResp.data.order) || null

    // 3）可选：本地模拟支付，把状态从 pending 改为 paid
    if (order && order.order_id) {
      try {
        const payResp = await payOrder({
          order_id: order.order_id,
          payment_channel: 'mock_pay',
        })
        order = (payResp.data && payResp.data.order) || order
      } catch (e) {
        console.warn('模拟支付失败，保留待支付状态：', e)
      }
    }

    lastOrder.value = order
    cartItems.value = []
    activeView.value = 'mall'

    if (order) {
      window.alert(
        [
          '下单成功！',
          `订单号：${order.order_id}`,
          `状态：${order.status}`,
          `实付金额：¥${Number(order.total_amount || 0).toFixed(2)}`,
        ].join('\n'),
      )
    } else {
      window.alert('下单成功，已创建订单。')
    }
  } catch (e) {
    console.error('提交订单失败：', e)
    window.alert('提交订单失败，请稍后重试或检查后端服务日志。')
  } finally {
    submittingOrder.value = false
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
  padding: 3px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
  font-size: 12px;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.04);
}

.user-pill-main {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-inline: 4px;
  position: relative;
  z-index: 2;
}

.user-pill.is-clickable {
  cursor: default;
}

.user-pill.has-menu {
  position: relative;
}

.user-id-label {
  color: var(--text-subtle);
}

.user-id {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'SF Mono', ui-monospace;
  color: var(--accent-deep);
}

.user-chevron {
  font-size: 11px;
  color: #9ca3af;
}

.user-menu {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  min-width: 132px;
  padding: 4px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow:
    0 18px 35px rgba(15, 23, 42, 0.16),
    0 0 0 1px rgba(248, 250, 252, 0.9);
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transform-origin: top right;
  transition: opacity 0.14s ease, transform 0.14s ease;
  z-index: 10;
}

.user-pill.has-menu:hover .user-menu {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.user-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 12px;
  color: #4b5563;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.user-menu-item:hover {
  background: rgba(239, 246, 255, 0.95);
  color: #1d4ed8;
}

.user-menu-item.is-danger {
  color: #b91c1c;
}

.user-menu-item.is-danger:hover {
  background: rgba(254, 242, 242, 0.96);
  color: #b91c1c;
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

.panel-profile .profile-body {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(260px, 1fr);
  gap: 18px;
  padding-top: 14px;
}

.profile-card {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(229, 231, 235, 0.9);
}

.profile-row + .profile-row {
  margin-top: 10px;
}

.profile-label {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 2px;
}

.profile-value {
  font-size: 13px;
  color: #111827;
}

.profile-value.mono {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'SF Mono', ui-monospace;
  letter-spacing: 0.02em;
}

.profile-desc h3 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}

.profile-desc p {
  font-size: 12px;
  color: #4b5563;
  margin-bottom: 4px;
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


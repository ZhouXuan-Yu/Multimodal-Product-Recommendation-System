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
            <p class="subtitle">基于多模态画像 & DeepSeek 智能导购的淘宝风格首页体验</p>
          </div>
        </header>

        <!-- 顶部橙色活动看板：全宽展示 -->
        <section class="mall-hero-row">
          <div class="mall-hero-main">
            <div class="mall-hero-badge">今日好货·AI 精选</div>
            <h3 class="mall-hero-title">根据你的兴趣，实时刷新专属会场</h3>
            <p class="mall-hero-sub">
              结合浏览行为、下单记录与 DeepSeek 语义理解，多模态模型为你筛选更高命中率的服饰与配饰好物。
            </p>
            <div class="mall-hero-tags">
              <span class="mall-hero-tag">通勤正装</span>
              <span class="mall-hero-tag">休闲潮流</span>
              <span class="mall-hero-tag">轻奢珠宝</span>
              <span class="mall-hero-tag">学生党预算</span>
            </div>
          </div>
          <div class="mall-hero-side">
            <div class="mall-hero-card">
              <p class="mall-hero-card-title">DeepSeek 智能导购</p>
              <p class="mall-hero-card-desc">
                不再需要手动输入搜索词，直接和右侧「DeepSeek 智能导购」对话，让 AI 帮你缩小范围、搭配穿搭、挑选珠宝。
              </p>
            </div>
            <div class="mall-hero-card secondary">
              <p class="mall-hero-card-title">多轮对话 · 精准筛选</p>
              <p class="mall-hero-card-desc">
                支持按预算、场景、风格等多条件反复沟通，逐步收窄到最适合的一批候选商品。
              </p>
            </div>
          </div>
        </section>

        <!-- 中下部：左 70% 商品流 + 右 30% DeepSeek 导购，支持拖拽缩放 -->
        <div
          ref="mallSplitRef"
          class="mall-main-split"
          :style="{
            '--mall-left-width': mallSplitRatio * 100 + '%',
            '--mall-right-width': (100 - mallSplitRatio * 100) + '%',
          }"
        >
          <div class="mall-main-column">
            <div class="mall-main-card">
              <section class="mall-products-section">
                <div class="mall-products-header">
                  <h3 class="mall-products-title">为你推荐 · 个性化好物</h3>
                  <p class="mall-products-sub">
                    推荐结果完全由右侧 DeepSeek 智能导购驱动，顶部不再提供传统搜索框。
                  </p>
                </div>
                <ProductWaterfall
                  :user-id="userId"
                  :query="mallQuery"
                  @item-click="handleItemClick"
                />
              </section>
            </div>
          </div>

          <!-- 中间拖拽手柄 -->
          <div class="mall-split-handle" @mousedown="startMallResize">
            <div class="mall-split-grip"></div>
          </div>

          <!-- 右侧 DeepSeek 智能导购栏 -->
          <aside class="mall-chat-column">
            <div class="mall-chat-card">
              <AIChatWidget
                v-if="authUser"
                :user-id="userId"
                @recommend-query="handleMallQueryFromChat"
                @item-click="handleItemClick"
              />
            </div>
          </aside>
        </div>
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

      <!-- 视图 F：个人信息 / 个人中心（现代 AI 平台风格） -->
      <section
        v-if="authUser"
        v-show="activeView === 'profile'"
        class="panel panel-profile glass-elevated"
      >
        <header class="panel-header panel-header-profile">
          <div>
            <h2 class="profile-title">个人画像与账号中心</h2>
            <p class="subtitle profile-subtitle">
              极简 · 未来感 · 新时代购物新范式 · 你更懂你自己
            </p>
          </div>
        </header>

        <!-- 单列三卡片布局：身份名片 / 账号属性（居中排布）+ 下方行为画像卡片 -->
        <div class="profile-main">
          <div class="profile-main-inner">
            <div class="profile-grid profile-grid-basic">
              <!-- 核心身份卡片（中间视觉主角） -->
              <section class="profile-card glass-card identity-card">
                <header class="profile-card-header">
                  <div>
                    <h3>身份名片</h3>
                    <p class="profile-card-subtitle">当前登录身份与基础账号信息</p>
                  </div>
                </header>

                <div class="profile-card-body">
                  <div class="identity-main">
                    <div class="identity-avatar-block">
                      <div class="identity-avatar">
                        <img :src="devAvatar" alt="Developer Avatar" />
                      </div>
                    </div>
                    <div class="identity-meta">
                      <div class="identity-name">
                        {{ authUser?.display_name || '未命名研究者' }}
                      </div>
                      <div class="identity-email mono truncate">
                        {{ authUser?.email || '未绑定邮箱' }}
                      </div>
                      <div class="identity-tags">
                        <span class="identity-tag accent">AI 研究 · 杭州</span>
                        <span class="identity-tag subtle">本机 RTX 5060 环境</span>
                      </div>
                    </div>
                  </div>

                  <div class="profile-row">
                    <span class="profile-label">昵称</span>
                    <div class="profile-field">
                      <span class="profile-value">{{ authUser?.display_name || '未设置' }}</span>
                    </div>
                  </div>
                  <div class="profile-row">
                    <span class="profile-label">登录邮箱</span>
                    <div class="profile-field">
                      <span class="profile-value mono truncate">{{ authUser?.email || '-' }}</span>
                      <button
                        v-if="authUser?.email"
                        class="profile-icon-btn"
                        type="button"
                        @click="copyToClipboard(authUser.email, 'email')"
                        title="复制邮箱"
                      >
                        <span class="icon icon-copy" />
                      </button>
                      <span
                        v-if="lastCopied === 'email'"
                        class="profile-copy-hint"
                      >
                        已复制
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              <!-- 账号属性卡 -->
              <section class="profile-card glass-card">
                <header class="profile-card-header">
                  <div>
                    <h3>账号属性</h3>
                    <p class="profile-card-subtitle">当前会话下的系统标识</p>
                  </div>
                </header>

                <div class="profile-card-body profile-stats">
                  <div class="profile-stat-pill">
                    <div class="profile-stat-label">用户 ID</div>
                    <div class="profile-field">
                      <span class="profile-value mono truncate">{{ userId }}</span>
                      <button
                        class="profile-icon-btn"
                        type="button"
                        @click="copyToClipboard(String(userId), 'userId')"
                        title="复制用户 ID"
                      >
                        <span class="icon icon-copy" />
                      </button>
                      <span
                        v-if="lastCopied === 'userId'"
                        class="profile-copy-hint"
                      >
                        已复制
                      </span>
                    </div>
                  </div>
                  <div class="profile-stat-pill">
                    <div class="profile-stat-label">当前身份</div>
                    <div class="profile-value badge">AI 开发者</div>
                  </div>
                  <div class="profile-stat-pill">
                    <div class="profile-stat-label">环境</div>
                    <div class="profile-value badge subtle">本地 Demo · 不写入生产</div>
                  </div>
                </div>
              </section>
            </div>

            <!-- 数据画像与项目中心：置于上方两卡片下方，占据下方主要视野 -->
            <section class="profile-card glass-card profile-insight-card profile-insight-below">
              <header class="profile-card-header">
                <div class="profile-card-title-row">
                  <div>
                    <h3>AI 行为画像与研究项目</h3>
                    <p class="profile-card-subtitle">行为画像摘要 · 兴趣标签云 · 当前研究项目概览</p>
                  </div>
                  <div class="profile-insight-chip">AI 引擎驱动</div>
                </div>
              </header>

              <div class="profile-card-body">
                <!-- 上半部分：行为采样窗口 + 画像摘要，独立毛玻璃小卡片 -->
                <div class="insight-subcard insight-overview-card">
                  <div class="profile-insight-meta">
                    <span class="profile-insight-dot" />
                    <span class="profile-insight-label">
                      行为采样窗口：近 14 天
                    </span>
                  </div>

                  <!-- 标题与内容之间的浅色分割线 -->
                  <div class="insight-section-separator" />

                  <!-- 画像摘要 -->
                  <p v-if="personaSummary" class="profile-summary">
                    {{ personaSummary }}
                  </p>
                  <p v-else class="profile-summary">
                    系统正在根据你的浏览、搜索和下单行为逐步学习兴趣画像，使用一段时间后将在此为你生成一段个性化的画像总结。
                  </p>
                </div>

                <!-- 下半部分：类目偏好 + 标签云，单独毛玻璃小卡片 -->
                <div class="insight-subcard insight-category-card">
                  <!-- 类目偏好：条形进度展示，长度与数量成比例（类目名称已映射为中文） -->
                  <div class="profile-tags" v-if="personaTopCategories.length">
                    <div class="profile-insight-meta profile-insight-meta--secondary">
                      <span class="profile-insight-dot" />
                      <span class="profile-insight-label">
                        类目偏好（近一段时间）
                      </span>
                    </div>
                    <!-- 标题与数据区域之间的浅色分割线 -->
                    <div class="insight-section-separator" />
                    <div class="persona-category-list">
                      <div
                        v-for="c in personaTopCategories"
                        :key="`cat-${c.name}`"
                        class="persona-category-row"
                      >
                        <div class="persona-category-label">
                          <span class="persona-category-name">{{ formatPersonaCategory(c.name) }}</span>
                          <span class="persona-category-count">· {{ c.value }}</span>
                        </div>
                        <div class="persona-category-progress">
                          <div class="persona-category-bar">
                            <div
                              class="persona-category-bar-fill"
                              :style="{
                                width:
                                  personaMaxCategory > 0
                                    ? Math.max(
                                        8,
                                        Math.round(
                                          ((Number(c.value) || 0) / personaMaxCategory) * 100,
                                        ),
                                      ) + '%'
                                    : '0%',
                              }"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 兴趣标签 -->
                  <div class="profile-tags" v-if="personaTopTags.length">
                    <div class="profile-tags-title">兴趣标签</div>
                    <div class="profile-tag-list">
                      <span
                        v-for="t in personaTopTags"
                        :key="`tag-${t.name}`"
                        class="profile-tag"
                      >
                        {{ t.name }}
                      </span>
                    </div>
                  </div>

                  <!-- 标签云：与画像标签共享数据，更多偏向可视权重展示 -->
                  <div class="persona-cloud">
                    <template v-if="personaTopTags.length || personaTopCategories.length">
                      <div
                        v-for="t in personaTopTags"
                        :key="`tag-${t.name}`"
                        class="persona-chip"
                      >
                        {{ t.name }}
                      </div>
                      <div
                        v-for="c in personaTopCategories"
                        :key="`cat-${c.name}`"
                        class="persona-chip subtle"
                      >
                        {{ c.name }}
                      </div>
                    </template>
                    <template v-else>
                      <div class="persona-empty">
                        系统正在根据你的浏览、搜索和下单行为逐步学习画像，稍后将在此以标签云形式呈现。
                      </div>
                    </template>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </section>
    </main>

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
import { ref, onBeforeUnmount, onMounted, watch, computed } from 'vue'
import InsightCenter from './components/InsightCenter.vue'
import ProductWaterfall from './components/ProductWaterfall.vue'
import AIChatWidget from './components/AIChatWidget.vue'
import RagSearchView from './components/RagSearchView.vue'
import CartModal from './components/CartModal.vue'
import CartCheckout from './components/CartCheckout.vue'
import OrderCenter from './components/OrderCenter.vue'
import LoginView from './components/LoginView.vue'
import RegisterView from './components/RegisterView.vue'
import { logUserAction, previewOrder, createOrder, payOrder, fetchInsightReport } from './api'
import { loadAuthUser, saveAuthUser, clearAuthUser } from './authStorage'
import devAvatar from '../../data/svg/地址空空的.svg'

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

// 画像与数据说明：AI 画像摘要 + 关键标签 + 偏好分布
const personaSummary = ref('')
const personaTopCategories = ref([])
const personaTopTags = ref([])

// 类目偏好最大值，用于条形进度长度归一化
const personaMaxCategory = computed(() => {
  if (!personaTopCategories.value.length) return 0
  return Math.max(
    ...personaTopCategories.value.map((c) => {
      const n = Number(c.value)
      return Number.isFinite(n) ? n : 0
    }),
  )
})

// 画像卡片内类目英文 -> 中文映射（与 InsightCenter / localeZh 保持一致）
const formatPersonaCategory = (c) => {
  if (!c) return '-'
  const map = {
    electronics: '数码电子',
    jewelery: '珠宝配饰',
    "men's clothing": '男装',
    "women's clothing": '女装',
    sports: '运动户外',
    unknown: '未知',
  }
  return map[c] || c
}

// 个人中心子导航：基本信息 / 数据隐私 / 账号安全 / 项目偏好
const profileNav = [
  { key: 'basic', label: '基本信息', icon: '◎' },
  { key: 'privacy', label: '数据隐私', icon: '⚙' },
  { key: 'security', label: '账号安全', icon: '⌁' },
  { key: 'preferences', label: '项目 / 偏好', icon: '★' },
]
const activeProfileSection = ref('basic')

// 一键复制提示状态
const lastCopied = ref('')
let copyTimer = null

const copyToClipboard = async (text, type) => {
  if (!text) return
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const input = document.createElement('input')
      input.value = text
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    lastCopied.value = type
    if (copyTimer) {
      clearTimeout(copyTimer)
    }
    copyTimer = setTimeout(() => {
      lastCopied.value = ''
    }, 1500)
  } catch (e) {
    console.warn('复制到剪贴板失败：', e)
  }
}

const loadPersonaInsight = async () => {
  if (!authUser.value || !userId.value) {
    personaSummary.value = ''
    personaTopCategories.value = []
    personaTopTags.value = []
    return
  }
  try {
    const { data } = await fetchInsightReport(userId.value, { days: 14 })
    personaSummary.value = data?.summary || ''
    personaTopCategories.value = Array.isArray(data?.top_categories) ? data.top_categories : []
    personaTopTags.value = Array.isArray(data?.top_tags) ? data.top_tags : []
  } catch (e) {
    console.warn('加载画像报告失败，将使用占位文案：', e)
    if (!personaSummary.value) {
      personaSummary.value =
        '近期你的浏览和下单行为还不算多，系统会在你继续使用的过程中逐步学习你的兴趣偏好，用于后续推荐与画像展示。'
    }
  }
}

// 后续登录 / 注册成功时会调用的辅助函数
const handleLoginSuccess = (user) => {
  authUser.value = user
  userId.value = user?.email || 'guest'
  saveAuthUser(user)
  authView.value = 'none'
  activeView.value = 'mall'
  loadPersonaInsight()
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

// 商城主视图左右分栏拖拽缩放（默认左 70% / 右 30%）
const mallSplitRatio = ref(0.7)
const mallSplitRef = ref(null)
let resizing = false

const clamp = (val, min, max) => Math.min(max, Math.max(min, val))

const handleMallMouseMove = (event) => {
  if (!resizing || !mallSplitRef.value) return
  const rect = mallSplitRef.value.getBoundingClientRect()
  const relativeX = (event.clientX - rect.left) / rect.width
  // 限制范围：左栏 55% - 80%
  mallSplitRatio.value = clamp(relativeX, 0.55, 0.8)
}

const stopMallResize = () => {
  if (!resizing) return
  resizing = false
  window.removeEventListener('mousemove', handleMallMouseMove)
  window.removeEventListener('mouseup', stopMallResize)
}

const startMallResize = () => {
  if (!mallSplitRef.value) return
  resizing = true
  window.addEventListener('mousemove', handleMallMouseMove)
  window.addEventListener('mouseup', stopMallResize)
}

onBeforeUnmount(() => {
  stopMallResize()
  if (copyTimer) {
    clearTimeout(copyTimer)
  }
})

// 初始化时，如已登录则预加载画像摘要
onMounted(() => {
  if (authUser.value) {
    loadPersonaInsight()
  }
})

// 当切换到“个人信息”视图时，若还没有画像摘要则尝试加载一次
watch(
  () => activeView.value,
  (view) => {
    if (view === 'profile' && !personaSummary.value && authUser.value) {
      loadPersonaInsight()
    }
  },
)
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
  /* 仿淘宝风格的商城首页布局容器 */
}

.mall-main-split {
  flex: 1;
  display: flex;
  gap: 24px;
  padding-top: 14px;
  align-items: stretch;
}

.mall-main-column {
  flex: 0 0 var(--mall-left-width, 70%);
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.mall-chat-column {
  flex: 0 0 var(--mall-right-width, 30%);
  min-width: 320px;
  max-width: 520px;
  display: flex;
  flex-direction: column;
}

.mall-main-card,
.mall-chat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  background: #ffffff;
  box-shadow:
    0 20px 40px rgba(15, 23, 42, 0.08),
    0 0 0 1px rgba(226, 232, 240, 0.9);
}

.mall-chat-card {
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.96), rgba(249, 250, 251, 0.98));
}

.mall-split-handle {
  position: relative;
  width: 10px;
  cursor: col-resize;
  display: flex;
  align-items: stretch;
  justify-content: center;
}

.mall-split-grip {
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(to bottom, rgba(209, 213, 219, 0.4), rgba(148, 163, 184, 0.7));
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.9),
    0 10px 30px rgba(15, 23, 42, 0.14);
}

.mall-hero-row {
  display: grid;
  grid-template-columns: minmax(0, 2.1fr) minmax(260px, 1fr);
  gap: 12px;
  margin-top: 14px;
}

.mall-hero-main {
  position: relative;
  padding: 16px 18px;
  border-radius: 16px;
  background: linear-gradient(120deg, #f97316, #fb923c, #fed7aa);
  color: #111827;
  overflow: hidden;
}

.mall-hero-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  font-size: 11px;
  color: #c2410c;
  margin-bottom: 6px;
}

.mall-hero-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 6px;
}

.mall-hero-sub {
  font-size: 12px;
  color: #1f2937;
  max-width: 520px;
}

.mall-hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.mall-hero-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #b45309;
}

.mall-hero-side {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mall-hero-card {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid rgba(229, 231, 235, 0.9);
}

.mall-hero-card.secondary {
  background: #fef3c7;
  border-color: #fbbf24;
}

.mall-hero-card-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.mall-hero-card-desc {
  font-size: 12px;
  color: #4b5563;
}

.mall-products-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
  padding: 14px 14px 12px;
}

.mall-products-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.mall-products-title {
  font-size: 15px;
  font-weight: 600;
}

.mall-products-sub {
  font-size: 11px;
  color: #9ca3af;
}

.panel-analytics {
  /* 可以在后续加入额外分析特化样式 */
}

.panel-profile {
  position: relative;
  background-color: #fdfbf7;
  background-image:
    radial-gradient(circle at 0% 0%, rgba(255, 140, 0, 0.08), transparent 55%),
    radial-gradient(circle at 100% 100%, rgba(255, 220, 180, 0.5), transparent 60%);
  color: #2d2d2d;
  font-family: 'Poppins', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI',
    sans-serif;
}

.panel-header-profile {
  border-bottom: none;
  padding-bottom: 4px;
}

.profile-title {
  font-size: 32px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.profile-subtitle {
  margin-top: 4px;
  font-size: 14px;
  color: #555;
}

.profile-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
  padding-top: 14px;
}

.profile-sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(25px);
}

.profile-sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.profile-avatar {
  position: relative;
  width: 52px;
  height: 52px;
  border-radius: 24px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.45);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.35),
    0 14px 28px rgba(15, 23, 42, 0.22);
}

.profile-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-sidebar-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.profile-sidebar-name {
  font-size: 14px;
  font-weight: 600;
}

.profile-sidebar-role {
  font-size: 11px;
  color: #9ca3af;
}

.profile-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

.profile-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  color: #6b7280;
  transition:
    background 0.16s ease,
    color 0.16s ease,
    border-color 0.16s ease,
    transform 0.12s ease,
    box-shadow 0.12s ease;
}

.profile-nav-item:hover {
  background: rgba(255, 255, 255, 0.35);
  border-color: rgba(255, 255, 255, 0.4);
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.1);
}

.profile-nav-item.active {
  position: relative;
  background: rgba(255, 255, 255, 0.5);
  border-color: rgba(255, 140, 0, 0.5);
  color: #111827;
  font-weight: 600;
}

.profile-nav-item.active::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 999px;
  background: #ff8c00;
}

.profile-nav-icon {
  width: 20px;
  text-align: center;
  font-size: 13px;
}

.profile-nav-label {
  flex: 1;
  text-align: left;
}

.profile-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.profile-main-inner {
  width: 100%;
  max-width: 1180px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1.2fr) minmax(220px, 1fr);
  gap: 14px;
}

.profile-grid-basic {
  grid-template-columns: minmax(260px, 1.4fr) minmax(220px, 1fr);
}

.profile-grid.single {
  grid-template-columns: minmax(0, 1.4fr);
}

.glass-card {
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(25px);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.glass-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 26px 60px rgba(15, 23, 42, 0.22);
  border-color: rgba(255, 255, 255, 0.3);
}

.profile-card-header {
  padding-bottom: 6px;
  border-bottom: none;
  margin-bottom: 8px;
}

.profile-card-header h3 {
  font-size: 13px;
  font-weight: 600;
}

.profile-card-subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: #9ca3af;
}

.profile-card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.profile-row + .profile-row {
  margin-top: 4px;
}

.profile-label {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 2px;
}

.profile-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
}

.profile-value {
  font-size: 13px;
  color: #2d2d2d;
}

.profile-value.mono {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'SF Mono', ui-monospace;
  letter-spacing: 0.02em;
}

.profile-value.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  background: rgba(34, 197, 94, 0.06);
  color: #15803d;
  border: 1px solid rgba(34, 197, 94, 0.35);
}

.profile-value.badge.subtle {
  background: rgba(59, 130, 246, 0.06);
  color: #1d4ed8;
  border-color: rgba(59, 130, 246, 0.35);
}

.profile-icon-btn {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  border: 1px solid rgba(209, 213, 219, 0.9);
  background: rgba(255, 255, 255, 0.95);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  transition:
    background 0.14s ease,
    border-color 0.14s ease,
    transform 0.12s ease,
    box-shadow 0.12s ease;
}

.profile-icon-btn:hover {
  background: rgba(249, 250, 251, 0.98);
  border-color: rgba(148, 163, 184, 0.9);
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.16);
}

.icon {
  position: relative;
  display: inline-block;
}

.icon-copy {
  width: 11px;
  height: 11px;
  border-radius: 3px;
  box-shadow:
    0 0 0 1px rgba(148, 163, 184, 0.9),
    3px -3px 0 0 rgba(248, 250, 252, 1),
    3px -3px 0 1px rgba(209, 213, 219, 0.9);
}

.profile-copy-hint {
  font-size: 11px;
  color: #22c55e;
}

.profile-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profile-stat-pill {
  padding: 9px 10px;
  border-radius: 12px;
  background: rgba(249, 250, 251, 0.96);
  border: 1px solid rgba(229, 231, 235, 0.95);
}

.profile-stat-label {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 2px;
}

.profile-insight-card {
  /* 与身份名片同系的玻璃卡片风格，取消黑紫色背景，整体更「海报感」 */
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 24px 52px rgba(15, 23, 42, 0.16);
  /* 卡片内文案统一使用近似黑色 */
  color: #000;
  min-height: calc(100vh - 260px);
  display: flex;
  flex-direction: column;
  padding: 22px 26px 24px;
}

.profile-insight-card .profile-card-header {
  border-color: transparent;
  margin-bottom: 10px;
}

.profile-insight-card h3 {
  color: #000;
  /* 标题字号提升到原来的约 1.5 倍 */
  font-size: 27px;
  line-height: 1.3;
}

.profile-insight-card .profile-card-subtitle {
  color: #000;
  /* 副标题同样放大约 1.5 倍 */
  font-size: 20px;
  line-height: 1.5;
}

.profile-card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.profile-insight-chip {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  border: 1px solid rgba(16, 185, 129, 0.5);
  animation: profile-chip-breath 7s ease-in-out infinite;
}

.profile-insight-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 18px;
  color: #000;
  margin-bottom: 10px;
}

.profile-insight-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #22c55e;
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.7);
}

.profile-insight-label {
  white-space: nowrap;
}

/* 类目偏好标题复用同一行样式，适当压缩下方间距 */
.profile-insight-meta--secondary {
  margin-bottom: 8px;
}

/* 行为采样窗口 / 类目偏好标题下方的浅色分割线，用于与下方数据区域做视觉区隔 */
.insight-section-separator {
  width: 100%;
  height: 1px;
  border-radius: 999px;
  background: rgba(209, 213, 219, 0.8);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.65);
  margin-bottom: 14px;
}

.profile-summary {
  margin-top: 4px;
  margin-bottom: 18px;
  font-size: 16px;
  line-height: 1.9;
  color: #000;
}

/* 让画像摘要更「海报感」：在大屏下采用两列排版，小屏保持单列 */
@media (min-width: 1100px) {
  .profile-summary {
    column-count: 2;
    column-gap: 28px;
  }
}

.profile-tags {
  margin-top: 10px;
}

.profile-tags-title {
  font-size: 16px;
  color: #000;
  margin-bottom: 10px;
}

.profile-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.profile-tag {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 14px;
  background: rgba(249, 115, 22, 0.1);
  color: #000;
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.45);
}

.profile-tag.light {
  background: rgba(59, 130, 246, 0.16);
  color: #1d4ed8;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.55);
}

.profile-footnote {
  margin-top: 10px;
  font-size: 11px;
  color: #9ca3af;
}

/* 让行为采样与类目偏好一起撑满整张卡片，形成上下分区的大海报布局 */
.profile-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* 画像卡片内部：两个毛玻璃子卡片，分别包裹「行为采样窗口」与「类目偏好」 */
.insight-subcard {
  background: rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  border: 1px solid rgba(209, 213, 219, 0.9);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  padding: 18px 20px 20px;
}

.insight-overview-card {
  margin-bottom: 18px;
}

.insight-category-card {
  margin-top: 4px;
}

.persona-category-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  /* 让下半部分类目偏好区域整体吃掉更多垂直空间 */
  padding-top: 10px;
  padding-bottom: 14px;
}

/* 类目偏好：标签 + 进度条，使用更强烈的可视化色系 */
.persona-category-row {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  align-items: center;
  gap: 18px;
}

.persona-category-label {
  font-size: 17px;
  color: #000;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.persona-category-name {
  font-weight: 600;
}

.persona-category-count {
  font-size: 15px;
  color: #000;
}

.persona-category-progress {
  width: 100%;
}

.persona-category-bar {
  position: relative;
  width: 100%;
  height: 16px;
  border-radius: 999px;
  background: rgba(229, 231, 235, 0.9);
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.6);
}

.persona-category-bar-fill {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #60a5fa, #2563eb);
  box-shadow: 0 0 16px rgba(59, 130, 246, 0.55);
}

/* 标签云稍微加大，整体更像一张信息海报底部的补充信息带 */
.persona-cloud {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.persona-chip {
  font-size: 12px;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  color: #4b5563;
  box-shadow: 0 0 0 1px rgba(209, 213, 219, 0.9);
}

.persona-chip.subtle {
  background: rgba(239, 246, 255, 0.95);
  color: #1d4ed8;
  box-shadow: 0 0 0 1px rgba(191, 219, 254, 0.9);
}

.profile-list {
  margin: 4px 0;
  padding-left: 16px;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.6;
}

.truncate {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.identity-card {
  grid-column: 1 / 2;
}

.identity-main {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.identity-avatar {
  width: 88px;
  height: 88px;
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.55);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.25),
    0 22px 45px rgba(15, 23, 42, 0.35);
}

.identity-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.identity-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.identity-name {
  font-size: 18px;
  font-weight: 600;
  color: #1f2933;
}

.identity-email {
  font-size: 12px;
  color: #6b7280;
}

.identity-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.identity-tag {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  border: 1px solid rgba(148, 163, 184, 0.5);
  background: rgba(255, 255, 255, 0.7);
}

.identity-tag.accent {
  border-color: rgba(255, 140, 0, 0.8);
  color: #b45309;
  background: rgba(255, 237, 213, 0.85);
}

.identity-tag.subtle {
  border-color: rgba(148, 163, 184, 0.6);
  color: #374151;
  background: rgba(243, 244, 246, 0.9);
}

/* 覆盖旧的标签云样式，统一黑色字体并放大字号 */
.persona-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.persona-chip {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.9);
  color: #000;
  border: 1px solid rgba(209, 213, 219, 0.9);
}

.persona-chip.subtle {
  background: rgba(239, 246, 255, 0.9);
  color: #000;
  border-color: rgba(96, 165, 250, 0.6);
}

.persona-empty {
  font-size: 12px;
  color: #9ca3af;
}

/* 类目偏好条形进度（参考研究时间线设计） */
.persona-category-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.profile-insight-below {
  width: 100%;
}

.project-center {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.4);
}

.project-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 8px;
}

.project-title {
  font-size: 12px;
  font-weight: 600;
  color: #e5e7eb;
}

.project-caption {
  font-size: 11px;
  color: #9ca3af;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.project-row {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1.2fr);
  gap: 6px;
  align-items: center;
}

.project-name {
  font-size: 12px;
  color: #e5e7eb;
}

.project-progress {
  display: flex;
  align-items: center;
  gap: 6px;
}

.project-bar {
  flex: 1;
  height: 5px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.9);
  overflow: hidden;
}

.project-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #fed7aa, #ff8c00);
}

.project-bar-gestures {
  width: 72%;
}

.project-bar-nav {
  width: 54%;
}

.project-percent {
  font-size: 11px;
  color: #e5e7eb;
}

/* Profile inputs - 无界表单风格 */
.panel-profile input,
.panel-profile textarea,
.panel-profile select {
  border: none;
  outline: none;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 13px;
  background: rgba(243, 244, 246, 0.5);
  transition:
    background 0.16s ease,
    box-shadow 0.16s ease;
}

.panel-profile input:focus,
.panel-profile textarea:focus,
.panel-profile select:focus {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 1px rgba(255, 140, 0, 0.5), 0 0 0 6px rgba(255, 140, 0, 0.12);
}

@keyframes profile-chip-breath {
  0%,
  100% {
    opacity: 0.9;
    transform: translateY(0);
  }
  50% {
    opacity: 0.6;
    transform: translateY(-1px);
  }
}

@media (max-width: 1024px) {
  .layout {
    padding: 0;
  }

  .panel {
    padding: 12px 10px 14px;
  }

  .mall-main-split {
    flex-direction: column;
    gap: 12px;
  }

  .mall-main-column,
  .mall-chat-column {
    flex: 1 1 auto;
    min-width: 0;
    max-width: none;
  }

  .mall-split-handle {
    display: none;
  }
}
</style>


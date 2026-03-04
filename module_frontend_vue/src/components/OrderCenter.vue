<template>
  <div class="orders-root">
    <header class="orders-header">
      <div>
        <h2>我的订单</h2>
        <p class="subtitle">
          查看最近在本地多模态推荐系统中生成的订单，支持快速查看订单详情与状态。
        </p>
      </div>
      <div class="header-right">
        <span class="user-pill">
          <span class="label">User</span>
          <span class="id">{{ userId }}</span>
        </span>
        <button class="refresh-btn" :disabled="loading" @click="loadOrders">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </header>

    <section class="orders-body">
      <div class="orders-list glass-panel soft-scrollbar">
        <div class="list-header">
          <span class="th th-id">订单号</span>
          <span class="th th-status">状态</span>
          <span class="th th-amount">金额</span>
          <span class="th th-time">创建时间</span>
        </div>

        <div v-if="loading" class="state state-loading">
          <span class="dot"></span>
          <span>正在加载订单列表...</span>
        </div>

        <div v-else-if="!orders.length" class="state state-empty">
          <p class="title">暂时还没有订单</p>
          <p class="subtitle">
            可以先在「智能推荐商城」中挑选商品，完成一次结算后再来这里查看订单记录。
          </p>
        </div>

        <ul v-else class="list">
          <li
            v-for="item in orders"
            :key="item.order_id"
            :class="['row', { active: item.order_id === selectedOrderId }]"
            @click="selectOrder(item)"
          >
            <span class="cell cell-id" :title="item.order_id">
              {{ item.order_id }}
            </span>
            <span class="cell cell-status">
              <span class="status-pill" :data-status="item.status">
                {{ renderStatusLabel(item.status) }}
              </span>
            </span>
            <span class="cell cell-amount">¥ {{ formatPrice(item.total_amount) }}</span>
            <span class="cell cell-time">
              {{ formatTime(item.created_at || item.updated_at) }}
            </span>
          </li>
        </ul>
      </div>

      <div class="orders-detail glass-panel" v-if="currentOrder">
        <header class="detail-header">
          <div>
            <h3>订单详情</h3>
            <p class="subtitle">
              订单号：<span class="mono">{{ currentOrder.order_id }}</span>
            </p>
          </div>
          <span class="status-pill" :data-status="currentOrder.status">
            {{ renderStatusLabel(currentOrder.status) }}
          </span>
        </header>

        <section class="detail-section">
          <h4>基础信息</h4>
          <div class="detail-grid">
            <div class="field">
              <span class="label">用户</span>
              <span class="value mono">{{ currentOrder.user_id }}</span>
            </div>
            <div class="field">
              <span class="label">总金额</span>
              <span class="value highlight">¥ {{ formatPrice(currentOrder.total_amount) }}</span>
            </div>
            <div class="field">
              <span class="label">创建时间</span>
              <span class="value">{{ formatTime(currentOrder.created_at) }}</span>
            </div>
            <div class="field">
              <span class="label">最近更新时间</span>
              <span class="value">{{ formatTime(currentOrder.updated_at) }}</span>
            </div>
            <div class="field" v-if="currentOrder.currency">
              <span class="label">币种</span>
              <span class="value">{{ currentOrder.currency }}</span>
            </div>
            <div class="field" v-if="currentOrder.note">
              <span class="label">备注</span>
              <span class="value">{{ currentOrder.note }}</span>
            </div>
          </div>
        </section>

        <section class="detail-section">
          <h4>商品明细</h4>
          <div class="items-table soft-scrollbar" v-if="currentOrder.items?.length">
            <div class="items-header">
              <span class="th th-name">商品</span>
              <span class="th th-qty">数量</span>
              <span class="th th-price">单价</span>
              <span class="th th-subtotal">小计</span>
            </div>
            <div
              v-for="it in currentOrder.items"
              :key="it.product_id + '-' + (it.sku_id || '')"
              class="items-row"
            >
              <span class="cell cell-name">
                <span class="mono">{{ it.product_id }}</span>
              </span>
              <span class="cell cell-qty">x {{ it.quantity }}</span>
              <span class="cell cell-price">¥ {{ formatPrice(it.price) }}</span>
              <span class="cell cell-subtotal">
                ¥ {{ formatPrice((it.price || 0) * (it.quantity || 0)) }}
              </span>
            </div>
          </div>
          <p v-else class="muted">当前订单暂未包含商品明细。</p>
        </section>
      </div>

      <div class="orders-detail glass-panel empty-detail" v-else>
        <p class="title">选择左侧一条订单即可查看详情</p>
        <p class="subtitle">
          你也可以通过 Postman 调用 <code>/api/orders</code> 接口构造更多不同场景的订单数据。
        </p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchOrders, fetchOrderDetail } from '../api'

const props = defineProps({
  userId: {
    type: String,
    required: true,
  },
})

const orders = ref([])
const loading = ref(false)
const selectedOrderId = ref(null)
const currentOrder = ref(null)

const loadOrders = async () => {
  if (loading.value) return
  loading.value = true
  try {
    const { data } = await fetchOrders({ user_id: props.userId, limit: 50 })
    orders.value = data.orders || data.items || []
    if (orders.value.length && !selectedOrderId.value) {
      await selectOrder(orders.value[0])
    } else if (!orders.value.length) {
      selectedOrderId.value = null
      currentOrder.value = null
    }
  } catch (e) {
    console.error('加载订单列表失败', e)
  } finally {
    loading.value = false
  }
}

const selectOrder = async (order) => {
  if (!order || !order.order_id) return
  selectedOrderId.value = order.order_id
  try {
    const { data } = await fetchOrderDetail(order.order_id)
    currentOrder.value = data.order || data
  } catch (e) {
    console.error('加载订单详情失败', e)
    currentOrder.value = order
  }
}

const formatPrice = (value) => {
  if (value == null) return '0.00'
  return Number(value).toFixed(2)
}

const formatTime = (value) => {
  if (!value) return '--'
  try {
    return new Date(value).toLocaleString()
  } catch (e) {
    return String(value)
  }
}

const renderStatusLabel = (status) => {
  if (!status) return '未知'
  if (status === 'paid') return '已支付'
  if (status === 'pending') return '待支付'
  if (status === 'cancelled') return '已取消'
  return status
}

const orderedList = computed(() => orders.value)

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.orders-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

.orders-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(209, 213, 219, 0.7);
}

.orders-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
  font-size: 11px;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}

.user-pill .label {
  color: #9ca3af;
}

.user-pill .id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    'Courier New', monospace;
  color: #f97316;
}

.refresh-btn {
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  font-size: 12px;
  color: #4b5563;
  cursor: pointer;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.orders-body {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1.75fr);
  gap: 12px;
  min-height: 0;
}

.orders-list {
  padding: 10px 10px 8px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 8px 22px rgba(15, 23, 42, 0.05),
    0 0 0 1px rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.list-header {
  display: grid;
  grid-template-columns: 2.4fr 1fr 1.2fr 1.5fr;
  padding: 4px 6px;
  font-size: 11px;
  color: #9ca3af;
}

.th {
  white-space: nowrap;
}

.state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 8px;
  font-size: 13px;
  color: #6b7280;
}

.state-loading .dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: radial-gradient(circle, #fb923c, #c2410c);
  box-shadow: 0 0 10px rgba(249, 115, 22, 0.7);
}

.state-empty .title {
  font-size: 15px;
  font-weight: 500;
}

.list {
  margin-top: 4px;
  padding: 0;
  list-style: none;
  flex: 1;
  overflow: auto;
}

.row {
  display: grid;
  grid-template-columns: 2.4fr 1fr 1.2fr 1.5fr;
  align-items: center;
  padding: 6px 6px;
  font-size: 12px;
  cursor: pointer;
  border-radius: 8px;
  margin-bottom: 4px;
  transition:
    background-color 0.12s ease,
    transform 0.12s ease;
}

.row:hover {
  background: #f9fafb;
}

.row.active {
  background: #fffbeb;
  transform: translateY(-1px);
}

.cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    'Courier New', monospace;
}

.cell-amount {
  font-weight: 600;
  color: #ea580c;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
}

.status-pill[data-status='paid'] {
  background: #dcfce7;
  color: #15803d;
}

.status-pill[data-status='pending'] {
  background: #fef3c7;
  color: #b45309;
}

.status-pill[data-status='cancelled'] {
  background: #fee2e2;
  color: #b91c1c;
}

.orders-detail {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 8px 22px rgba(15, 23, 42, 0.05),
    0 0 0 1px rgba(226, 232, 240, 0.9);
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.empty-detail {
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-detail .title {
  font-size: 15px;
  font-weight: 500;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(229, 231, 235, 0.9);
}

.detail-header h3 {
  font-size: 15px;
  font-weight: 600;
}

.detail-section {
  margin-top: 6px;
}

.detail-section h4 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 12px;
  font-size: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field .label {
  font-size: 11px;
  color: #9ca3af;
}

.field .value {
  color: #111827;
}

.field .value.highlight {
  font-size: 14px;
  font-weight: 700;
  color: #ea580c;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
    'Courier New', monospace;
}

.items-table {
  margin-top: 4px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  max-height: 200px;
  overflow: auto;
}

.items-header,
.items-row {
  display: grid;
  grid-template-columns: 2.4fr 1fr 1.2fr 1.3fr;
  padding: 6px 8px;
  font-size: 12px;
}

.items-header {
  background: #f9fafb;
  color: #6b7280;
  font-size: 11px;
}

.items-row:nth-child(odd) {
  background: #ffffff;
}

.items-row:nth-child(even) {
  background: #f9fafb;
}

.items-row .cell {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.muted {
  font-size: 12px;
  color: #9ca3af;
}

@media (max-width: 1024px) {
  .orders-body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>


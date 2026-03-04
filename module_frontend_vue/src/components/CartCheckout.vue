<template>
  <div class="cart-page">
    <header class="cart-header">
      <h2>购物车结算</h2>
      <p class="subtitle">参考淘宝风格的简化版结算页 · 支持批量结算与数量调整</p>
    </header>

    <section v-if="items.length" class="cart-content">
      <table class="cart-table">
        <thead>
          <tr>
            <th class="col-product">商品信息</th>
            <th class="col-price">单价</th>
            <th class="col-qty">数量</th>
            <th class="col-subtotal">小计</th>
            <th class="col-op">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.product.product_id">
            <td class="col-product">
              <div class="prod-cell">
                <img
                  class="thumb"
                  :src="row.product.image_url || row.product.image || ''"
                  :alt="row.product.name"
                />
                <div class="meta">
                  <p class="name" :title="row.product.name">{{ row.product.name }}</p>
                  <p class="desc">
                    {{ row.product.description || '系统为你推荐的高匹配好物' }}
                  </p>
                </div>
              </div>
            </td>
            <td class="col-price">
              ¥ {{ formatPrice(row.product.price) }}
            </td>
            <td class="col-qty">
              <div class="stepper">
                <button :disabled="row.quantity <= 1" @click="updateQty(row, row.quantity - 1)">
                  -
                </button>
                <input
                  v-model.number="row.quantity"
                  type="number"
                  min="1"
                  @change="updateQty(row, row.quantity)"
                />
                <button @click="updateQty(row, row.quantity + 1)">+</button>
              </div>
            </td>
            <td class="col-subtotal">
              ¥ {{ formatPrice(row.product.price * row.quantity) }}
            </td>
            <td class="col-op">
              <button class="link-btn" @click="remove(row.product.product_id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-else class="empty-cart">
      <p class="title">购物车还是空的</p>
      <p class="subtitle">可以回到智能推荐商城，挑几件感兴趣的好物再来结算 ~</p>
    </section>

    <footer class="cart-footer">
      <div class="summary">
        <span>已选 {{ totalCount }} 件商品，合计：</span>
        <span class="total-price">¥ {{ formatPrice(totalAmount) }}</span>
      </div>
      <div class="actions">
        <button class="btn-secondary" @click="$emit('back-to-mall')">返回商城继续逛</button>
        <button
          class="btn-primary"
          :disabled="!items.length || submitting"
          @click="$emit('submit-order')"
        >
          {{ submitting ? '正在提交...' : '提交订单' }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  submitting: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:items', 'back-to-mall', 'submit-order'])

const totalAmount = computed(() =>
  props.items.reduce((sum, row) => sum + (row.product.price || 0) * row.quantity, 0),
)

const totalCount = computed(() => props.items.reduce((sum, row) => sum + row.quantity, 0))

const formatPrice = (value) => {
  if (value == null) return '0.00'
  return Number(value).toFixed(2)
}

const updateQty = (row, value) => {
  const qty = Math.max(1, Number(value) || 1)
  const next = props.items.map((r) =>
    r.product.product_id === row.product.product_id ? { ...r, quantity: qty } : r,
  )
  emit('update:items', next)
}

const remove = (productId) => {
  const next = props.items.filter((r) => r.product.product_id !== productId)
  emit('update:items', next)
}
</script>

<style scoped>
.cart-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

.cart-header {
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(209, 213, 219, 0.7);
}

.cart-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}

.cart-content {
  flex: 1;
  overflow: auto;
}

.cart-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.cart-table th,
.cart-table td {
  padding: 10px 8px;
  border-bottom: 1px solid #e5e7eb;
}

.col-product {
  width: 45%;
}

.col-price,
.col-qty,
.col-subtotal,
.col-op {
  text-align: center;
  white-space: nowrap;
}

.prod-cell {
  display: flex;
  gap: 8px;
  align-items: center;
}

.thumb {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  object-fit: cover;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
}

.meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.name {
  font-size: 13px;
  font-weight: 500;
  color: #111827;
}

.desc {
  font-size: 11px;
  color: #6b7280;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stepper {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.stepper button {
  width: 24px;
  height: 26px;
  border: none;
  background: #f9fafb;
  cursor: pointer;
}

.stepper input {
  width: 40px;
  border: none;
  text-align: center;
  font-size: 13px;
  outline: none;
}

.empty-cart {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.empty-cart .title {
  font-size: 16px;
  font-weight: 500;
}

.cart-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid rgba(209, 213, 219, 0.7);
}

.summary {
  font-size: 13px;
  color: #4b5563;
}

.total-price {
  margin-left: 6px;
  font-size: 18px;
  font-weight: 700;
  color: #ea580c;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-secondary,
.btn-primary {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
}

.btn-secondary {
  background: #f9fafb;
  border-color: #e5e7eb;
  color: #4b5563;
}

.btn-primary {
  background: linear-gradient(to right, #f97316, #fb923c);
  color: #ffffff;
  box-shadow: 0 6px 18px rgba(248, 113, 22, 0.4);
}

.link-btn {
  border: none;
  background: none;
  color: #f97316;
  cursor: pointer;
  font-size: 12px;
}
</style>


<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="cart-modal-backdrop" @click.self="emit('close')">
        <div class="cart-modal glass-elevated">
          <header class="modal-header">
            <h3>加入购物车</h3>
            <button class="close-btn" @click="emit('close')">×</button>
          </header>

          <section class="modal-body" v-if="product">
            <div class="product-brief">
              <div class="thumb">
                <img :src="product.image_url || product.image || ''" :alt="product.name" />
              </div>
              <div class="info">
                <h4 class="name" :title="product.name">{{ product.name }}</h4>
                <p class="price">¥ {{ formatPrice(product.price) }}</p>
                <p class="desc">
                  {{ product.description || '由多模态推荐系统为你智能筛选的高匹配好物。' }}
                </p>
              </div>
            </div>

            <div class="quantity-row">
              <span>购买数量</span>
              <div class="stepper">
                <button :disabled="quantity <= 1" @click="quantity = Math.max(1, quantity - 1)">-</button>
                <input v-model.number="quantity" type="number" min="1" />
                <button @click="quantity += 1">+</button>
              </div>
            </div>
          </section>

          <footer class="modal-footer">
            <div class="total">
              <span>合计：</span>
              <span class="total-price">
                ¥ {{ product ? formatPrice((product.price || 0) * quantity) : '0.00' }}
              </span>
            </div>
            <div class="actions">
              <button class="btn-secondary" @click="emit('close')">再看看</button>
              <button
                class="btn-primary"
                @click="emit('add-to-cart', { product, quantity })"
              >
                加入购物车
              </button>
              <button
                class="btn-accent"
                @click="emit('checkout', { product, quantity })"
              >
                立即结算
              </button>
            </div>
          </footer>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  product: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'add-to-cart', 'checkout'])

const quantity = ref(1)

watch(
  () => props.visible,
  (val) => {
    if (val) {
      quantity.value = 1
    }
  },
)

const formatPrice = (value) => {
  if (value == null) return '0.00'
  return Number(value).toFixed(2)
}
</script>

<style scoped>
.cart-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.46);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.cart-modal {
  width: 520px;
  max-width: 92vw;
  max-height: 90vh;
  border-radius: 16px;
  padding: 16px 18px 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 24px 60px rgba(15, 23, 42, 0.35),
    0 0 0 1px rgba(226, 232, 240, 0.9);
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.modal-header h3 {
  font-size: 17px;
  font-weight: 600;
}

.close-btn {
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0 10px;
}

.product-brief {
  display: flex;
  gap: 12px;
}

.thumb {
  width: 96px;
  height: 96px;
  border-radius: 10px;
  overflow: hidden;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.name {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.price {
  font-size: 16px;
  font-weight: 700;
  color: #f97316;
}

.desc {
  font-size: 12px;
  color: #6b7280;
  max-height: 96px;
  overflow-y: auto;
}

.quantity-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: #4b5563;
}

.stepper {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.stepper button {
  width: 28px;
  height: 28px;
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

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(209, 213, 219, 0.7);
}

.total {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: #6b7280;
}

.total-price {
  font-size: 18px;
  font-weight: 700;
  color: #ea580c;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-secondary,
.btn-primary,
.btn-accent {
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
  box-shadow: 0 6px 18px rgba(248, 113, 22, 0.5);
}

.btn-accent {
  background: #111827;
  color: #f9fafb;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>


<template>
  <div class="auth-shell glass-elevated">
    <!-- 左侧说明区：延续品牌叙事，强调“画像初始化 / 冷启动” -->
    <aside class="visual-pane">
      <div class="badge-row">
        <span class="pill pill-soft">新用户冷启动</span>
        <span class="pill pill-soft">行为画像预热</span>
      </div>
      <h1 class="hero-title">
        先留个联系方式，
        <br />
        我们帮你把画像「预热」好。
      </h1>
      <p class="hero-subtitle">
        通过简单的注册信息，我们会为你创建一个本地账号，并为后续的浏览、加购和下单行为建立一条独立的数据轨迹。
      </p>
      <ul class="benefits">
        <li>更精准的首页推荐</li>
        <li>专属订单与优惠记录</li>
        <li>后续可一键导出个人数据</li>
      </ul>
    </aside>

    <!-- 右侧表单区：账号注册 -->
    <section class="form-pane">
      <header class="form-header">
        <h2>创建你的账号</h2>
        <p class="form-subtitle">填写基础信息，用于标识你在本地系统中的“数字分身”。</p>
      </header>

      <form class="form-body" @submit.prevent="handleSubmit">
        <label class="field">
          <span class="field-label">昵称</span>
          <input
            v-model="displayName"
            type="text"
            required
            autocomplete="nickname"
            placeholder="例如：小北、运营狗、数据控..."
          />
        </label>

        <label class="field">
          <span class="field-label">邮箱</span>
          <input
            v-model="email"
            type="email"
            required
            autocomplete="email"
            placeholder="you@example.com"
          />
        </label>

        <label class="field">
          <span class="field-label">密码</span>
          <input
            v-model="password"
            type="password"
            required
            minlength="6"
            autocomplete="new-password"
            placeholder="至少 6 位密码（本地演示不做强校验）"
          />
        </label>

        <div class="hint-row">
          <span class="hint">
            当前为本地 Demo 环境，账号信息仅保存在浏览器本地，
            后端不接入真实用户体系，你可以随意输入模拟信息。
          </span>
        </div>

        <button class="submit-btn" type="submit" :disabled="submitting">
          <span v-if="!submitting">注册并登录</span>
          <span v-else>注册中...</span>
        </button>
      </form>

      <footer class="form-footer">
        <span class="footer-text">已经有账号？</span>
        <button class="link-btn" type="button" @click="$emit('switch-view', 'login')">
          直接去登录
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['register-success', 'switch-view'])

const displayName = ref('')
const email = ref('')
const password = ref('')
const submitting = ref(false)

const handleSubmit = async () => {
  if (!email.value || !password.value || !displayName.value || submitting.value) return

  submitting.value = true
  try {
    // 本地 Demo：不做真实后端注册，直接当作已创建账号并登录。
    const user = {
      email: email.value.trim(),
      display_name: displayName.value.trim(),
    }
    await new Promise((resolve) => setTimeout(resolve, 400))
    emit('register-success', user)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-shell {
  display: grid;
  grid-template-columns: minmax(260px, 2.5fr) minmax(320px, 3.5fr);
  gap: 32px;
  padding: 28px 26px;
  border-radius: 22px;
  background: linear-gradient(135deg, #eff6ff, #f9fafb);
  box-shadow:
    0 20px 60px rgba(15, 23, 42, 0.12),
    0 0 0 1px rgba(248, 250, 252, 0.9);
}

.visual-pane {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 18px;
  padding-right: 8px;
  border-right: 1px dashed rgba(191, 219, 254, 0.7);
}

.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.04em;
}

.pill-soft {
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(219, 234, 254, 0.95);
  color: #1d4ed8;
}

.hero-title {
  margin-top: 8px;
  font-size: 24px;
  line-height: 1.4;
  font-weight: 700;
  color: #0f172a;
}

.hero-subtitle {
  margin-top: 10px;
  font-size: 13px;
  color: #6b7280;
  max-width: 340px;
}

.benefits {
  margin-top: 14px;
  padding-left: 16px;
  font-size: 12px;
  color: #4b5563;
}

.benefits li + li {
  margin-top: 4px;
}

.form-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
  justify-content: center;
}

.form-header h2 {
  font-size: 22px;
  font-weight: 600;
  color: #111827;
}

.form-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.form-body {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  color: #6b7280;
}

.field input {
  border-radius: 999px;
  border: 1px solid rgba(209, 213, 219, 0.9);
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
  background: rgba(255, 255, 255, 0.98);
}

.field input:focus {
  border-color: rgba(59, 130, 246, 0.8);
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.25);
  background: #ffffff;
}

.hint-row {
  margin-top: 4px;
}

.hint {
  font-size: 11px;
  color: #9ca3af;
}

.submit-btn {
  margin-top: 6px;
  width: 100%;
  border-radius: 999px;
  padding: 9px 14px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  color: white;
  background: linear-gradient(120deg, #3b82f6, #1d4ed8);
  box-shadow:
    0 14px 30px rgba(37, 99, 235, 0.4),
    0 0 0 1px rgba(248, 250, 252, 0.9);
  cursor: pointer;
  transition: transform 0.08s ease, box-shadow 0.08s ease, opacity 0.08s ease;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: default;
  box-shadow: 0 10px 22px rgba(148, 163, 184, 0.3);
}

.submit-btn:not(:disabled):active {
  transform: translateY(1px);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.4);
}

.form-footer {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}

.link-btn {
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: #1d4ed8;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

@media (max-width: 960px) {
  .auth-shell {
    grid-template-columns: 1fr;
    padding: 20px 16px;
  }

  .visual-pane {
    border-right: none;
    border-bottom: 1px dashed rgba(191, 219, 254, 0.7);
    padding-right: 0;
    padding-bottom: 14px;
  }
}
</style>


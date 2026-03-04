<template>
  <div class="login-shell glass-elevated">
    <!-- 左侧：品牌 / 插画，占比约 40% -->
    <aside class="visual-pane">
      <div class="badge-row">
        <span class="pill pill-soft">DeepSeek 驱动</span>
        <span class="pill pill-soft">多模态画像</span>
      </div>
      <h1 class="hero-title">
        先 <span class="highlight">登录</span>，
        <br />
        再让 AI 懂你一点。
      </h1>
      <p class="hero-subtitle">
        结合浏览、加购、订单等行为轨迹，实时构建你的兴趣画像，
        为你生成只属于自己的推荐“货架”。
      </p>
      <div class="stat-row">
        <div class="stat-card">
          <div class="stat-value">3x</div>
          <div class="stat-label">转化率提升</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">10k+</div>
          <div class="stat-label">向量召回/秒</div>
        </div>
      </div>
      <div class="bottom-note">
        <span class="dot"></span>
        行为数据只用于本地建模，不会上传至第三方。
      </div>
    </aside>

    <!-- 右侧：登录表单，占比约 60% -->
    <section class="form-pane">
      <header class="form-header">
        <h2>欢迎回来</h2>
        <p class="form-subtitle">使用邮箱登录，体验个性化推荐与订单洞察。</p>
      </header>

      <form class="form-body" @submit.prevent="handleSubmit">
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
            autocomplete="current-password"
            placeholder="至少 6 位密码"
          />
        </label>

        <div class="hint-row">
          <span class="hint">当前为本地演示环境，可随意输入模拟账号。</span>
        </div>

        <button class="submit-btn" type="submit" :disabled="submitting">
          <span v-if="!submitting">登录并进入商城</span>
          <span v-else>登录中...</span>
        </button>
      </form>

      <footer class="form-footer">
        <span class="footer-text">还没有账号？</span>
        <button class="link-btn" type="button" @click="$emit('switch-view', 'register')">
          先注册一个
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['login-success', 'switch-view'])

const email = ref('')
const password = ref('')
const submitting = ref(false)

const handleSubmit = async () => {
  if (!email.value || !password.value || submitting.value) return

  submitting.value = true
  try {
    // 这里暂时做本地模拟验证：将任意邮箱视为一个合法用户。
    // 如果后续接入真实登录 API，只需要在这里替换为后端校验逻辑。
    const user = {
      email: email.value.trim(),
      display_name: email.value.trim().split('@')[0] || 'Guest',
    }
    // 小延迟模拟请求
    await new Promise((resolve) => setTimeout(resolve, 400))
    emit('login-success', user)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-shell {
  display: grid;
  grid-template-columns: minmax(260px, 2.5fr) minmax(320px, 3.5fr);
  gap: 32px;
  padding: 28px 26px;
  border-radius: 22px;
  background: linear-gradient(135deg, #fefce8, #f9fafb);
  box-shadow:
    0 20px 60px rgba(15, 23, 42, 0.14),
    0 0 0 1px rgba(248, 250, 252, 0.9);
}

.visual-pane {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 18px;
  padding-right: 8px;
  border-right: 1px dashed rgba(209, 213, 219, 0.7);
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
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
  color: #334155;
}

.hero-title {
  margin-top: 8px;
  font-size: 26px;
  line-height: 1.3;
  font-weight: 700;
  color: #0f172a;
}

.highlight {
  background: linear-gradient(120deg, #fb923c, #ea580c);
  -webkit-background-clip: text;
  color: transparent;
}

.hero-subtitle {
  margin-top: 10px;
  font-size: 13px;
  color: #6b7280;
  max-width: 320px;
}

.stat-row {
  margin-top: 18px;
  display: flex;
  gap: 12px;
}

.stat-card {
  flex: 1;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.stat-label {
  margin-top: 2px;
  font-size: 11px;
  color: #6b7280;
}

.bottom-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 11px;
  color: #9ca3af;
}

.bottom-note .dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: radial-gradient(circle, #22c55e, #16a34a);
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);
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
  background: rgba(255, 255, 255, 0.95);
}

.field input:focus {
  border-color: rgba(249, 115, 22, 0.8);
  box-shadow: 0 0 0 1px rgba(249, 115, 22, 0.25);
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
  background: linear-gradient(120deg, #fb923c, #ea580c);
  box-shadow:
    0 14px 30px rgba(249, 115, 22, 0.4),
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
  box-shadow: 0 10px 22px rgba(249, 115, 22, 0.4);
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
  color: #ea580c;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

@media (max-width: 960px) {
  .login-shell {
    grid-template-columns: 1fr;
    padding: 20px 16px;
  }

  .visual-pane {
    border-right: none;
    border-bottom: 1px dashed rgba(209, 213, 219, 0.7);
    padding-right: 0;
    padding-bottom: 14px;
  }
}
</style>


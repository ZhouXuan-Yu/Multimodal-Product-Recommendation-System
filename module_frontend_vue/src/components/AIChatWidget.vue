<template>
  <div class="chat-root">
    <header class="chat-header" @click="toggleCollapse">
      <div class="left">
        <span class="dot"></span>
        <div class="titles">
          <span class="title">DeepSeek 智能导购</span>
          <span class="sub">描述你的需求，AI 将为你定制个性化选品</span>
        </div>
      </div>
      <button class="collapse-btn">
        {{ collapsed ? '展开' : '收起' }}
      </button>
    </header>

    <section v-if="!collapsed" class="chat-body">
      <div ref="listRef" class="messages">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['msg-row', msg.role]"
        >
          <div class="avatar">
            <span v-if="msg.role === 'user'">U</span>
            <span v-else>D</span>
          </div>
          <div class="bubble">
            <p class="text" v-html="msg.displayText"></p>

            <!-- 在 AI 回复中渲染微型商品卡片 -->
            <div
              v-if="msg.products && msg.products.length"
              class="inline-products"
            >
              <article
                v-for="p in msg.products"
                :key="p.product_id"
                class="mini-card"
                @click="handleItemClick(p)"
              >
                <img
                  class="mini-img"
                  :src="resolveImageUrl(p)"
                  :alt="p.name"
                  loading="lazy"
                />
                <div class="mini-meta">
                  <p class="mini-title" :title="p.name">{{ p.name }}</p>
                  <p class="mini-price">¥ {{ formatPrice(p.price) }}</p>
                </div>
              </article>
            </div>
          </div>
        </div>

        <!-- 加载中动效：光标闪烁 -->
        <div v-if="loading" class="msg-row assistant">
          <div class="avatar"><span>D</span></div>
          <div class="bubble loading">
            <span class="cursor"></span>
          </div>
        </div>
      </div>

      <footer class="input-bar">
        <input
          v-model="input"
          class="input"
          type="text"
          placeholder="例如：帮我推荐几款通勤黑色风衣，适合 20-30 岁..."
          :disabled="loading"
          @keyup.enter="handleSend"
        />
        <button
          class="send-btn"
          :disabled="loading || !input.trim()"
          @click="handleSend"
        >
          {{ loading ? '思考中...' : '发送' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { chatWithAI } from '../api'

const props = defineProps({
  userId: {
    type: String,
    required: true,
  },
})

const emit = defineEmits([
  // 当 AI 给出一个明确的“检索意图”时，通知父组件刷新商城视图
  'recommend-query',
  // 在聊天内点击商品卡片时继续复用统一的日志上报逻辑
  'item-click',
])

const messages = ref([
  {
    role: 'assistant',
    text: '你好，我是 DeepSeek 智能导购。可以直接告诉我你的预算、风格偏好或使用场景，我会结合你的历史行为为你做个性化选品。',
    displayText:
      '你好，我是 DeepSeek 智能导购。可以直接告诉我你的预算、风格偏好或使用场景，我会结合你的历史行为为你做个性化选品。',
  },
])

const input = ref('')
const loading = ref(false)
const collapsed = ref(false)
const listRef = ref(null)

// 简单的打字机效果：逐字显示 AI 回复内容
const typeWriter = async (fullText, msgIndex) => {
  messages.value[msgIndex].displayText = ''
  for (let i = 0; i < fullText.length; i += 1) {
    messages.value[msgIndex].displayText += fullText[i]
    // 每次更新后，滚动到底部
    await nextTick()
    scrollToBottom()
    await new Promise((resolve) => setTimeout(resolve, 12)) // 可根据需要调整打字速度
  }
}

const scrollToBottom = () => {
  if (!listRef.value) return
  listRef.value.scrollTop = listRef.value.scrollHeight
}

// 格式化价格
const formatPrice = (value) => {
  if (value == null) return '--'
  return Number(value).toFixed(2)
}

// 拼接图片 URL
const resolveImageUrl = (item) => {
  if (!item) return ''
  const url = item.image_url || item.image || ''
  if (!url) return ''
  if (url.startsWith('http')) return url
  return url
}

// 发送消息主流程：1) push 用户消息 2) 请求后端 3) 打字机方式写入 AI 回复 4) 解析出商品列表
const handleSend = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return

  // 推入用户消息
  messages.value.push({
    role: 'user',
    text,
    displayText: text,
  })
  input.value = ''
  await nextTick()
  scrollToBottom()

  loading.value = true
  try {
    const { data } = await chatWithAI({
      user_id: props.userId,
      message: text,
    })

    // 后端建议返回：{ reply: string, product_suggestions?: [] }
    const replyText =
      data.reply ||
      '我已经根据你的偏好生成了一批候选商品，你可以在右侧商城视图中查看详情。'
    const products = data.product_suggestions || []

    const msgIndex = messages.value.length
    // 先插入一个空的 assistant 消息，再通过打字机效果填充
    messages.value.push({
      role: 'assistant',
      text: replyText,
      displayText: '',
      products,
    })

    // 启动打字机效果
    await typeWriter(replyText, msgIndex)

    // 如果 AI 回复中包含“明确检索意图”（可以是后端单独给出一个 query 字段），则联动商城视图
    if (data.query_suggestion) {
      emit('recommend-query', data.query_suggestion)
    } else {
      // 兜底：直接使用用户输入作为商城检索词
      emit('recommend-query', text)
    }
  } catch (e) {
    console.error('AI 聊天失败', e)
    messages.value.push({
      role: 'assistant',
      text: '抱歉，当前智能导购服务暂时不可用，请稍后再试。',
      displayText: '抱歉，当前智能导购服务暂时不可用，请稍后再试。',
    })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const handleItemClick = (item) => {
  emit('item-click', item)
}

const toggleCollapse = () => {
  collapsed.value = !collapsed.value
}
</script>

<style scoped>
.chat-root {
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow:
    0 18px 40px rgba(15, 23, 42, 0.08),
    0 0 0 1px rgba(255, 255, 255, 0.9);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
}

.left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: radial-gradient(circle, #f97316, #c2410c);
  box-shadow: 0 0 10px rgba(249, 115, 22, 0.8);
}

.titles {
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 13px;
  font-weight: 600;
}

.sub {
  font-size: 11px;
  color: #9ca3af;
}

.collapse-btn {
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.8);
  background: rgba(248, 250, 252, 0.9);
  color: #4b5563;
  font-size: 11px;
  padding: 2px 8px;
  cursor: pointer;
}

.chat-body {
  display: flex;
  flex-direction: column;
  border-top: 1px solid rgba(229, 231, 235, 0.9);
}

.messages {
  max-height: 360px;
  overflow-y: auto;
  padding: 10px 10px 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.msg-row {
  display: flex;
  gap: 6px;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-row.user .avatar {
  order: 2;
}

.msg-row.user .bubble {
  order: 1;
  background: linear-gradient(to right, #f97316, #fb923c);
}

.avatar {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #f5f1ea;
  border: 1px solid rgba(209, 213, 219, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #6b7280;
}

.bubble {
  max-width: 82%;
  padding: 6px 8px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.5;
  background: #f9fafb;
  border: 1px solid rgba(229, 231, 235, 0.9);
}

.bubble.loading {
  display: inline-flex;
  align-items: center;
  width: 40px;
  justify-content: flex-start;
}

.text {
  white-space: pre-wrap;
}

.cursor {
  display: inline-block;
  width: 10px;
  height: 14px;
  background: #4b5563;
  animation: blink 0.9s steps(2, start) infinite;
}

.inline-products {
  margin-top: 6px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.mini-card {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 4px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(229, 231, 235, 0.9);
  cursor: pointer;
}

.mini-card:hover {
  border-color: #f97316;
}

.mini-img {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  object-fit: cover;
}

.mini-meta {
  flex: 1;
}

.mini-title {
  font-size: 11px;
  color: #1f2933;
  margin-bottom: 2px;
}

.mini-price {
  font-size: 11px;
  color: #f97316;
}

.input-bar {
  display: flex;
  gap: 6px;
  padding: 6px 8px 8px;
  border-top: 1px solid rgba(229, 231, 235, 0.9);
}

.input {
  flex: 1;
  border-radius: 999px;
  border: none;
  background: rgba(248, 250, 252, 0.96);
  padding: 7px 12px;
  font-size: 12px;
  color: #111827;
  box-shadow:
    0 0 0 1px rgba(229, 231, 235, 0.9),
    0 8px 18px rgba(15, 23, 42, 0.04);
}

.input::placeholder {
  color: #6b7280;
}

.send-btn {
  border-radius: 999px;
  border: none;
  padding: 0 12px;
  background: linear-gradient(to right, #f97316, #fb923c);
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(248, 113, 22, 0.5);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

@keyframes blink {
  0% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}
</style>


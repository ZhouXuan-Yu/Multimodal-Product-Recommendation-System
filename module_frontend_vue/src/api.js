// 统一封装前端与 FastAPI 后端交互的 API 模块
// 使用 axios 实例，便于后续统一处理超时、鉴权、错误上报等逻辑

import axios from 'axios'

// 开发环境推荐保持「前端和后端同源」，通过 Vite proxy 转发到 FastAPI（见 vite.config.js）。
// 默认走同源（BASE_URL 为空字符串），这样：
//   - 你在自己电脑上访问 http://localhost:5173，前端会请求 http://localhost:5173/api/...
//   - 你在手机 / 其他电脑上访问 http://192.168.x.x:5173，前端会请求 http://192.168.x.x:5173/api/...
//   - 再由 Vite 代理到真正的后端 http://127.0.0.1:8000，避免在其他设备上 127.0.0.1 指向「自己那台设备」导致 Network Error。
// 如需跳过代理、直连 FastAPI，可在 .env.local 中设置：
//   VITE_API_BASE_URL=http://127.0.0.1:8000
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const instance = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
})

// 请求拦截器：可以在这里自动附加用户标识、token 等
instance.interceptors.request.use(
  (config) => {
    // 例如：config.headers['X-User-Id'] = currentUserId
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器：统一处理错误、打印日志
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    // 这里可以接入全局消息组件（如 ElMessage / 自定义 Toast）
    console.error('API 请求异常：', error)
    return Promise.reject(error)
  },
)

// 获取用户画像与行为数据，用于仪表盘
export function fetchUserProfile(userId) {
  return instance.get(`/api/user_profile/${userId}`)
}

// 洞察中心：获取用户事件流（已在后端 join product 信息，可用于筛选/钻取/对比/异常检测/导出）
export function fetchInsightEvents(userId, params = {}) {
  return instance.get(`/api/insights/${userId}/events`, { params })
}

// 洞察中心：获取用户画像向量偏移轨迹（用于向量轨迹图）
export function fetchVectorDrift(userId, params = {}) {
  // params: { max_events? }
  return instance.get(`/api/insights/${userId}/vector_drift`, { params })
}

// 洞察中心：获取用户多模态行为路径桑基图数据
export function fetchBehaviorSankey(userId, params = {}) {
  // params: { limit? }
  return instance.get(`/api/insights/${userId}/behavior_sankey`, { params })
}

// 洞察中心：获取两个时间段的语义化对比结果（语义差分看板 + 健康度 + AI 叙事）
export function fetchInsightSemanticDiff(userId, params = {}) {
  // params: { a_start, a_end, b_start, b_end }
  return instance.get(`/api/insights/${userId}/semantic_diff`, { params })
}

// 获取推荐商品列表（支持 query / 分页，具体参数需与后端对齐）
export function fetchRecommendations(params) {
  // 约定 params: { user_id, query, page, page_size }
  return instance.post('/api/recommend', params)
}

// 日志上报：点击、加购等行为
export function logUserAction(payload) {
  // payload: { user_id, product_id, action, extra? }
  return instance.post('/api/log_action', payload)
}

// 与 DeepSeek / 后端 LLM 对话
export function chatWithAI(payload) {
  // payload: { user_id, message, context? }
  // 后端建议返回：{ reply: string, product_suggestions?: Array<{product_id, name, price, image_url, reason}> }
  return instance.post('/api/ai_chat', payload)
}

// 本地向量库检索（不走 LLM），用于直接展示 RAG 召回结果
export function ragSearch(params) {
  // params: { q, top_k }
  return instance.get('/api/rag_search', { params })
}

// ===== 订单相关接口封装 =====

// 订单预览：不写入本地文件，只用于结算前预确认
// payload: { user_id, currency?, note?, items: [{ product_id, quantity }] }
export function previewOrder(payload) {
  return instance.post('/api/orders/preview', payload)
}

// 创建订单：真正写入 data/meta/orders.json，返回带 order_id 的订单对象
// payload 结构与 previewOrder 相同
export function createOrder(payload) {
  return instance.post('/api/orders', payload)
}

// 模拟支付：仅本地将状态从 pending → paid
// payload: { order_id, payment_channel }
export function payOrder(payload) {
  return instance.post('/api/orders/pay', payload)
}

// 订单列表与详情
export function fetchOrders(params = {}) {
  // params: { user_id?, limit? }
  return instance.get('/api/orders', { params })
}

export function fetchOrderDetail(orderId) {
  return instance.get(`/api/orders/${orderId}`)
}

export { BASE_URL, instance as axiosInstance }


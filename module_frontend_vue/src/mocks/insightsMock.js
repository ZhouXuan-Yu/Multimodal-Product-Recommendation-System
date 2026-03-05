// 本地模拟数据：用于“个人数据洞察中心”在后端无数据时的兜底展示
// 目标：
// - 按 userId 稳定可复现（种子随机），并持久化到 localStorage
// - 支持追加虚拟数据（方便后续用户继续补充）
// - 输出结构与后端 /api/insights/{userId}/events 保持一致：{ overview, events }

const STORAGE_PREFIX = 'mmrs_insights_mock_v1:'

function safeJsonParse(text, fallback) {
  try {
    return JSON.parse(text)
  } catch {
    return fallback
  }
}

// ---------- seeded PRNG ----------
function hashToSeed(str) {
  // FNV-1a 32-bit
  let h = 0x811c9dc5
  for (let i = 0; i < String(str).length; i++) {
    h ^= String(str).charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

function mulberry32(seed) {
  let a = seed >>> 0
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function pick(rng, list) {
  if (!list || !list.length) return null
  const idx = Math.min(list.length - 1, Math.floor(rng() * list.length))
  return list[idx]
}

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n))
}

function ymd(d) {
  return new Date(d).toISOString().slice(0, 10)
}

function addDays(date, days) {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function weightedPick(rng, items) {
  // items: [{value, weight}]
  const total = items.reduce((acc, x) => acc + (x.weight || 0), 0) || 1
  let r = rng() * total
  for (const it of items) {
    r -= it.weight || 0
    if (r <= 0) return it.value
  }
  return items[items.length - 1]?.value
}

// ---------- domain mocks ----------
const CATEGORIES = ['electronics', 'jewelery', "men's clothing", "women's clothing", 'sports']
const ACTIONS = ['view', 'click', 'add_to_cart', 'purchase', 'search', 'favorite']

const PRODUCT_TEMPLATES = {
  electronics: [
    '降噪无线耳机',
    '机械键盘',
    '4K 显示器',
    '轻薄笔记本',
    '智能手表',
    'USB-C 扩展坞',
  ],
  jewelery: ['珍珠项链', '银质戒指', '复古耳钉', '钛钢手链', '水晶吊坠'],
  "men's clothing": ['机能夹克', '针织衫', '商务衬衫', '休闲裤', '羽绒马甲'],
  "women's clothing": ['通勤风衣', '针织连衣裙', '高腰牛仔裤', '简约上衣', '运动瑜伽套装'],
  sports: ['跑鞋', '筋膜枪', '登山背包', '速干衣', '智能跳绳', '瑜伽垫'],
}

function buildProduct(rng, category, idx) {
  const base = pick(rng, PRODUCT_TEMPLATES[category] || ['商品'])
  const suffix = ['Pro', 'Max', 'Lite', 'Plus', '2026', 'SE'][Math.floor(rng() * 6)]
  const id = `P-${category.replace(/\W/g, '').slice(0, 6)}-${String(idx).padStart(4, '0')}`
  return {
    product_id: id,
    product_name: `${base} ${suffix}`.trim(),
    // 不强依赖外部图片服务，空字符串即可（钻取列表会自动不渲染 img）
    image_url: '',
  }
}

function buildEvent(rng, userId, date, seq, productPool) {
  const day = ymd(date)
  const category = weightedPick(rng, [
    { value: 'electronics', weight: 32 },
    { value: "women's clothing", weight: 22 },
    { value: "men's clothing", weight: 18 },
    { value: 'sports', weight: 16 },
    { value: 'jewelery', weight: 12 },
  ])

  const action = weightedPick(rng, [
    { value: 'view', weight: 36 },
    { value: 'click', weight: 24 },
    { value: 'add_to_cart', weight: 14 },
    { value: 'favorite', weight: 10 },
    { value: 'search', weight: 10 },
    { value: 'purchase', weight: 6 },
  ])

  const poolKey = category
  if (!productPool[poolKey]) productPool[poolKey] = []
  if (productPool[poolKey].length < 18) {
    productPool[poolKey].push(buildProduct(rng, category, productPool[poolKey].length + 1))
  }

  const product = action === 'search' ? null : pick(rng, productPool[poolKey])
  const ts = new Date(date)
  ts.setHours(Math.floor(rng() * 24), Math.floor(rng() * 60), Math.floor(rng() * 60), 0)

  const qWords = ['耳机', '跑鞋', '风衣', '键盘', '戒指', '瑜伽', '显示器', '手表', '衬衫', '背包']
  const searchQuery = action === 'search' ? `${pick(rng, qWords)} ${pick(rng, ['推荐', '性价比', '对比', '测评', '新款'])}` : ''

  return {
    id: `${userId}-${day}-${seq}`,
    day,
    timestamp: ts.toISOString(),
    action,
    category,
    product_id: product?.product_id || '',
    product_name: product?.product_name || (action === 'search' ? `搜索：${searchQuery}` : ''),
    image_url: product?.image_url || '',
  }
}

function computeOverviewFromEvents(evs) {
  const events = Array.isArray(evs) ? evs : []
  const kpiEvents = events.length
  const daySet = new Set()
  const productSet = new Set()
  const byAction = new Map()
  const byCategory = new Map()
  const byDay = new Map()

  for (const e of events) {
    if (e.day) daySet.add(e.day)
    if (e.product_id) productSet.add(e.product_id)
    const a = e.action || 'unknown'
    const c = e.category || 'unknown'
    byAction.set(a, (byAction.get(a) || 0) + 1)
    byCategory.set(c, (byCategory.get(c) || 0) + 1)
    if (e.day) byDay.set(e.day, (byDay.get(e.day) || 0) + 1)
  }

  const toSortedList = (m) =>
    [...m.entries()]
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)

  const timeseries = [...byDay.entries()]
    .map(([day, value]) => ({ day, value }))
    .sort((a, b) => String(a.day).localeCompare(String(b.day)))

  return {
    kpis: {
      events: kpiEvents,
      active_days: daySet.size,
      unique_products: productSet.size,
    },
    distribution: {
      by_action: toSortedList(byAction),
      by_category: toSortedList(byCategory),
    },
    timeseries,
  }
}

function loadStore(userId) {
  const key = STORAGE_PREFIX + String(userId || 'guest')
  const raw = localStorage.getItem(key)
  const parsed = raw ? safeJsonParse(raw, null) : null
  if (parsed && Array.isArray(parsed.events)) return parsed
  return null
}

function saveStore(userId, store) {
  const key = STORAGE_PREFIX + String(userId || 'guest')
  localStorage.setItem(key, JSON.stringify(store))
}

function ensureStore(userId) {
  const existing = loadStore(userId)
  if (existing) return existing

  const seed = hashToSeed(userId || 'guest')
  const rng = mulberry32(seed)
  const now = new Date()
  const start = addDays(now, -27)
  const productPool = {}
  const events = []

  // 基础：28 天数据，带 2 个“峰值日”方便异常检测
  const spikeDays = new Set([ymd(addDays(now, -9)), ymd(addDays(now, -3))])
  let seq = 1
  for (let i = 0; i < 28; i++) {
    const d = addDays(start, i)
    const day = ymd(d)
    const base = Math.floor(6 + rng() * 10) // 6~15
    const spike = spikeDays.has(day) ? Math.floor(18 + rng() * 18) : 0 // 峰值额外 18~35
    const n = base + spike
    for (let k = 0; k < n; k++) {
      events.push(buildEvent(rng, userId, d, seq++, productPool))
    }
  }

  const store = {
    version: 1,
    userId: String(userId || 'guest'),
    createdAt: new Date().toISOString(),
    seed,
    nextSeq: seq,
    events,
  }
  saveStore(userId, store)
  return store
}

function filterByParams(events, params) {
  const p = params || {}
  const start = p.start ? new Date(p.start + 'T00:00:00') : null
  const end = p.end ? new Date(p.end + 'T23:59:59') : null
  const q = String(p.q || '').trim().toLowerCase()

  return (events || []).filter((e) => {
    if (p.action && e.action !== p.action) return false
    if (p.category && e.category !== p.category) return false
    if (q) {
      const text = `${e.product_name || ''} ${e.product_id || ''}`.toLowerCase()
      if (!text.includes(q)) return false
    }
    if (start || end) {
      const t = e.timestamp ? new Date(e.timestamp) : null
      if (t) {
        if (start && t < start) return false
        if (end && t > end) return false
      }
    }
    return true
  })
}

export function mockFetchInsightEvents(userId, params = {}) {
  const store = ensureStore(userId)
  const filtered = filterByParams(store.events, params)
  return {
    __mock: true,
    overview: computeOverviewFromEvents(filtered),
    events: filtered,
  }
}

// 将后端新增的真实事件“并入”本地 mock 仓库：
// - 以本地生成的历史 mock 作为基线
// - 对于后端返回的事件，如果本地还没有，就追加进去
// - 之后再按现有逻辑（mockFetchInsightEvents）做过滤与 overview 计算
export function syncExternalInsightEvents(userId, externalEvents = [], params = {}) {
  const list = Array.isArray(externalEvents) ? externalEvents : []
  if (!list.length) {
    return mockFetchInsightEvents(userId, params)
  }

  const store = ensureStore(userId)

  const buildKey = (e) => {
    if (!e) return ''
    if (e.id != null) return String(e.id)
    const t = e.timestamp || e.time || ''
    const pid = e.product_id || e.productId || ''
    const act = e.action || ''
    return `${t}|${pid}|${act}`
  }

  const existingKeys = new Set((store.events || []).map((e) => buildKey(e)).filter(Boolean))

  for (const e of list) {
    const key = buildKey(e)
    if (!key || existingKeys.has(key)) continue
    existingKeys.add(key)
    store.events.push({ ...e })
  }

  saveStore(userId, store)
  return mockFetchInsightEvents(userId, params)
}

export function mockAppendInsightEvents(userId, count = 60) {
  const store = ensureStore(userId)
  const seed = (store.seed || hashToSeed(userId || 'guest')) + store.nextSeq
  const rng = mulberry32(seed >>> 0)
  const productPool = {}

  // 用现有事件推断产品池（让追加数据更“连贯”）
  for (const e of store.events || []) {
    if (!e.category || !e.product_id) continue
    if (!productPool[e.category]) productPool[e.category] = []
    if (!productPool[e.category].some((p) => p.product_id === e.product_id)) {
      productPool[e.category].push({
        product_id: e.product_id,
        product_name: e.product_name,
        image_url: e.image_url || '',
      })
    }
  }

  const now = new Date()
  const daysBack = 21
  const minDate = addDays(now, -daysBack)
  const n = clamp(Number(count || 0), 1, 500)

  for (let i = 0; i < n; i++) {
    const offset = Math.floor(rng() * (daysBack + 1))
    const d = addDays(minDate, offset)
    store.events.push(buildEvent(rng, userId, d, store.nextSeq++, productPool))
  }

  saveStore(userId, store)
  return { __mock: true, added: n, total: store.events.length }
}

export function mockResetInsightEvents(userId) {
  const key = STORAGE_PREFIX + String(userId || 'guest')
  localStorage.removeItem(key)
  // 重新生成一份
  ensureStore(userId)
  return { __mock: true, ok: true }
}

// 向量漂移 mock：随机游走 + 语义注释段
export function mockFetchVectorDrift(userId, params = {}) {
  const store = ensureStore(userId)
  const max = clamp(Number(params.max_events || 120), 20, 220)
  const seed = hashToSeed(userId || 'guest') ^ 0x9e3779b9
  const rng = mulberry32(seed >>> 0)
  const evs = store.events.slice(-max)

  let x = 0
  let y = 0
  const points = []
  const segments = []

  const semanticPool = [
    '对同类产品进行横向对比，兴趣向“性价比”方向偏移。',
    '受到图片风格刺激，审美维度向“技术感/机能”增强。',
    '从泛浏览转向深度阅读，研究意图提升。',
    '出现加购行为，短期购买意图明显增强。',
    '多次回访相似商品，说明偏好正在收敛。',
  ]

  for (let i = 0; i < evs.length; i++) {
    const e = evs[i]
    const stepScale = e.action === 'purchase' ? 0.22 : e.action === 'add_to_cart' ? 0.15 : 0.08
    const dx = (rng() - 0.5) * stepScale
    const dy = (rng() - 0.5) * stepScale
    x += dx
    y += dy
    const delta = Math.sqrt(dx * dx + dy * dy)
    points.push({
      x: Number(x.toFixed(4)),
      y: Number(y.toFixed(4)),
      action: e.action || 'view',
      product_id: e.product_id || '',
      delta_norm: Number(delta.toFixed(4)),
    })
    if (i > 0 && i % 7 === 0) {
      segments.push({
        to_step: i,
        semantic_shift: pick(rng, semanticPool),
      })
    }
  }

  return { __mock: true, points, segments }
}

// 桑基图 mock：固定结构 + 计数（用事件量缩放）
export function mockFetchBehaviorSankey(userId) {
  const store = ensureStore(userId)
  const n = store.events.length || 120
  const scale = Math.max(1, Math.round(n / 120))

  const nodes = [
    { name: '入口：首页推荐' },
    { name: '入口：搜索' },
    { name: '浏览：列表页' },
    { name: '浏览：详情页' },
    { name: '行为：收藏' },
    { name: '行为：加购' },
    { name: '行为：下单' },
  ]

  const links = [
    { source: '入口：首页推荐', target: '浏览：列表页', value: 38 * scale },
    { source: '入口：搜索', target: '浏览：列表页', value: 22 * scale },
    { source: '浏览：列表页', target: '浏览：详情页', value: 44 * scale },
    { source: '浏览：详情页', target: '行为：收藏', value: 16 * scale },
    { source: '浏览：详情页', target: '行为：加购', value: 18 * scale },
    { source: '行为：加购', target: '行为：下单', value: 6 * scale },
    { source: '行为：收藏', target: '浏览：详情页', value: 7 * scale },
  ]

  return { __mock: true, nodes, links }
}

// 语义差分 mock：根据日期范围生成稳定叙事
export function mockFetchInsightSemanticDiff(userId, params = {}) {
  const seed = hashToSeed(`${userId || 'guest'}|${params.a_start || ''}|${params.a_end || ''}|${params.b_start || ''}|${params.b_end || ''}`)
  const rng = mulberry32(seed >>> 0)

  const focusList = ['数码电子', '运动户外', '女装通勤', '男装机能', '珠宝配饰']
  const from_focus = pick(rng, focusList)
  let to_focus = pick(rng, focusList)
  if (to_focus === from_focus) to_focus = pick(rng, focusList)

  const intent_delta_pct = Math.round((rng() - 0.35) * 60) // -21% ~ +39%

  const dims = [
    '性价比',
    '技术参数',
    '外观风格',
    '品牌偏好',
    '场景需求',
    '复购倾向',
    '决策速度',
  ]
  const semantic_diff_board = dims.map((d) => {
    const before = clamp(rng(), 0.05, 0.95)
    const after = clamp(before + (rng() - 0.5) * 0.25, 0.02, 0.98)
    const delta = Number((after - before).toFixed(2))
    const direction = delta > 0.02 ? 'up' : delta < -0.02 ? 'down' : 'flat'
    const comment =
      direction === 'up'
        ? '本期关注度提升，建议增加对应语义召回与相似推荐权重。'
        : direction === 'down'
          ? '本期关注度下降，可适度降低该维度对排序的影响。'
          : '变化不大，维持当前推荐策略即可。'
    return {
      dimension: d,
      weight_before: Number(before.toFixed(2)),
      weight_after: Number(after.toFixed(2)),
      delta,
      direction,
      comment,
    }
  })

  const healthList = ['good', 'warning', 'bad']
  const overall_health = pick(rng, healthList)
  const behavior_depth_health = pick(rng, healthList)
  const suggested_action =
    overall_health === 'good'
      ? '兴趣稳定且健康，建议继续保持多样性探索，避免推荐过度收敛。'
      : overall_health === 'bad'
        ? '兴趣波动较大，建议降低强意图触达频率，提升探索性推荐比例。'
        : '兴趣正在迁移，建议关注新兴趣类目的持续性，并逐步调整召回与排序权重。'

  return {
    __mock: true,
    summary_text: `在本期时间窗口内，用户关注点从「${from_focus}」逐步迁移至「${to_focus}」，意图强度变化 ${intent_delta_pct > 0 ? '+' : ''}${intent_delta_pct}%。`,
    focus_shift: {
      from_focus,
      to_focus,
      intent_delta_pct,
      focus_shift_desc: '对比两段周期的 Top 商品语义与行为强度后，发现用户偏好正在向新的主题聚焦。',
    },
    semantic_diff_board,
    health: {
      overall_health,
      behavior_depth_health,
      suggested_action,
    },
  }
}


<template>
  <div class="ic-root">
    <!-- Top nav: tabs + tools -->
    <section class="ic-top glass-panel">
      <div class="ic-tabs segmented">
        <button
          v-for="t in tabs"
          :key="t.key"
          :class="['ic-tab', { active: activeTab === t.key }]"
          @click="activeTab = t.key"
        >
          <span :class="['ic-tab-label', { 'text-glow': activeTab === t.key }]">{{ t.label }}</span>
        </button>
      </div>

      <div class="ic-tools">
        <button class="ic-tool-btn ghost" @click="filterOpen = !filterOpen">筛选</button>
        <button class="ic-tool-btn ghost" @click="handleRefresh">刷新</button>
        <button class="ic-tool-btn primary breathe" @click="handleExport">导出</button>

        <div class="ic-date">
          <span class="ic-date-label">日期</span>
          <input v-model="filters.start" class="ic-input" type="date" />
          <span class="ic-date-sep">至</span>
          <input v-model="filters.end" class="ic-input" type="date" />
        </div>
      </div>
    </section>

    <!-- Filter panel -->
    <section v-if="filterOpen" class="ic-filter glass-elevated">
      <div class="ic-filter-grid">
        <label class="ic-field">
          <span class="ic-field-label">行为类型</span>
          <select v-model="filters.action" class="ic-select">
            <option value="">全部</option>
            <option v-for="a in actionOptions" :key="a" :value="a">{{ a }}</option>
          </select>
        </label>

        <label class="ic-field">
          <span class="ic-field-label">商品类目</span>
          <select v-model="filters.category" class="ic-select">
            <option value="">全部</option>
            <option v-for="c in categoryOptions" :key="c" :value="c">{{ formatCategory(c) }}</option>
          </select>
        </label>

        <label class="ic-field ic-field-wide">
          <span class="ic-field-label">关键词</span>
          <input v-model.trim="filters.q" class="ic-input" type="text" placeholder="搜索商品名/描述" />
        </label>

        <div class="ic-filter-actions">
          <button class="ic-tool-btn ghost" @click="handleResetFilters">重置</button>
          <button class="ic-tool-btn primary" @click="handleRefresh">应用筛选</button>
        </div>
      </div>
    </section>

    <!-- Content -->
    <section class="ic-body">
      <!-- BASIC -->
      <div v-if="activeTab === 'basic'" class="ic-grid">
        <div class="ic-card glass-elevated floaty">
          <header class="ic-card-head">
            <div class="ic-title">
              <span class="ic-dot"></span>
              <div>
                <h3>数据总览</h3>
                <p class="ic-sub">行为事件 · 活跃天数 · 触达商品</p>
              </div>
            </div>
          </header>

          <div class="ic-kpis">
            <div class="ic-kpi">
              <div class="ic-kpi-label">事件数</div>
              <div class="ic-kpi-value">{{ overview?.kpis?.events ?? 0 }}</div>
            </div>
            <div class="ic-kpi">
              <div class="ic-kpi-label">活跃天数</div>
              <div class="ic-kpi-value">{{ overview?.kpis?.active_days ?? 0 }}</div>
            </div>
            <div class="ic-kpi">
              <div class="ic-kpi-label">触达商品</div>
              <div class="ic-kpi-value">{{ overview?.kpis?.unique_products ?? 0 }}</div>
            </div>
          </div>

          <div class="ic-mini-grid">
            <div class="ic-mini">
              <div class="ic-mini-title">行为分布</div>
              <div class="ic-mini-badges">
                <span v-for="x in topActions" :key="x.name" class="ic-badge">
                  {{ x.name }} · {{ x.value }}
                </span>
              </div>
            </div>
            <div class="ic-mini">
              <div class="ic-mini-title">类目分布</div>
              <div class="ic-mini-badges">
                <span v-for="x in topCategories" :key="x.name" class="ic-badge">
                  {{ formatCategory(x.name) }} · {{ x.value }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="ic-card glass-elevated floaty">
          <header class="ic-card-head">
            <div class="ic-title">
              <span class="ic-dot orange"></span>
              <div>
                <h3>类目偏好分布</h3>
                <p class="ic-sub">点击扇区可下钻到该类目明细</p>
              </div>
            </div>
          </header>
          <div ref="donutRef" class="ic-chart"></div>
        </div>

        <div class="ic-card glass-elevated floaty wide">
          <header class="ic-card-head">
            <div class="ic-title">
              <span class="ic-dot emerald"></span>
              <div>
                <h3>趋势分析</h3>
                <p class="ic-sub">按天汇总的事件量（可用于异常检测与对比）</p>
              </div>
            </div>
          </header>
          <div ref="trendRef" class="ic-chart"></div>
        </div>

        <div class="ic-card glass-elevated floaty wide">
          <header class="ic-card-head">
            <div class="ic-title">
              <span class="ic-dot"></span>
              <div>
                <h3>数据明细</h3>
                <p class="ic-sub">按类目汇总（支持钻取）</p>
              </div>
            </div>
          </header>

          <div class="ic-table-wrap soft-scrollbar">
            <table class="ic-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th class="num">数量</th>
                  <th class="num">趋势</th>
                  <th class="ops">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in categoryRows" :key="row.name">
                  <td>{{ formatCategory(row.name) }}</td>
                  <td class="num">{{ row.value }}</td>
                  <td class="num" :class="{ down: row.delta < 0, up: row.delta > 0 }">
                    {{ row.delta > 0 ? '+' : '' }}{{ row.delta }}%
                  </td>
                  <td class="ops">
                    <button class="ic-row-btn" @click="goDrillCategory(row.name)">钻取</button>
                  </td>
                </tr>
                <tr v-if="!categoryRows.length">
                  <td colspan="4" class="empty">暂无数据（可尝试点击“刷新”或放宽筛选条件）</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- DRILL -->
      <div v-else-if="activeTab === 'drill'" class="ic-grid">
        <div class="ic-card glass-elevated floaty wide">
          <header class="ic-card-head">
            <div class="ic-title">
              <span class="ic-dot orange"></span>
              <div>
                <h3>数据钻取</h3>
                <p class="ic-sub">从类目 → 商品 → 行为明细逐层下钻</p>
              </div>
            </div>
            <div class="ic-breadcrumb">
              <button v-if="drill.category" class="ic-crumb" @click="resetDrill">返回</button>
              <span v-if="drill.category" class="ic-crumb-current">{{ formatCategory(drill.category) }}</span>
            </div>
          </header>

          <div v-if="!drill.category" class="ic-drill-empty">
            <div class="ic-hint">
              从“基础图表/明细表”点击 <b>钻取</b>，或点击左侧类目环图扇区开始下钻。
            </div>
            <div class="ic-drill-list">
              <button
                v-for="x in topCategories"
                :key="x.name"
                class="ic-pill"
                @click="goDrillCategory(x.name)"
              >
                {{ formatCategory(x.name) }} · {{ x.value }}
              </button>
            </div>
          </div>

          <div v-else class="ic-drill-grid">
            <div class="ic-card-inner glass-panel">
              <div class="ic-inner-title">该类目 Top 商品（点击可查看向量影响与行为路径）</div>
              <div class="ic-top-items soft-scrollbar">
                <div
                  v-for="p in drillTopProducts"
                  :key="p.product_id"
                  class="ic-item clickable"
                  @click="handleClickProduct(p)"
                >
                  <img v-if="p.image_url" class="ic-item-img" :src="p.image_url" :alt="p.product_name" />
                  <div class="ic-item-meta">
                    <div class="ic-item-name">
                      {{ p.product_name || p.product_id }}
                    </div>
                    <div class="ic-item-sub">
                      点击/事件：{{ p.count }}
                      <span v-if="drill.productId === p.product_id" class="ic-tag-current">已选中</span>
                    </div>
                  </div>
                </div>
                <div v-if="!drillTopProducts.length" class="ic-hint">该类目暂无事件</div>
              </div>
            </div>

            <div class="ic-card-inner glass-panel">
              <div class="ic-inner-title">类目行为分布</div>
              <div ref="drillDonutRef" class="ic-chart small"></div>
            </div>

            <div class="ic-card-inner glass-panel wide">
              <div class="ic-inner-title">类目趋势</div>
              <div ref="drillTrendRef" class="ic-chart small"></div>
            </div>

            <div class="ic-card-inner glass-panel wide">
              <div class="ic-inner-title">
                向量偏移轨迹图
                <span v-if="drill.productName" class="ic-inner-sub">
                  · 当前商品：{{ drill.productName }}
                </span>
              </div>
              <div v-if="!drill.productId" class="ic-hint">
                请选择左侧任一 Top 商品，查看该商品点击后用户画像在向量空间中的偏移轨迹。
              </div>
              <div v-else ref="vectorDriftRef" class="ic-chart small"></div>
            </div>

            <div class="ic-card-inner glass-panel wide">
              <div class="ic-inner-title">行为轨迹流 · 多模态路径桑基图</div>
              <div v-if="!sankeyReady" class="ic-hint">
                选择任一商品后，将自动加载从搜索 / 入口到详情再到反馈的行为路径。
              </div>
              <div v-else ref="sankeyRef" class="ic-chart small"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- COMPARE -->
      <div v-else-if="activeTab === 'compare'" class="ic-grid">
        <div class="ic-card glass-elevated floaty wide">
          <header class="ic-card-head">
            <div class="ic-title">
              <span class="ic-dot"></span>
              <div>
                <h3>数据对比</h3>
                <p class="ic-sub">支持两段时间窗口对比，查看变化与趋势差异</p>
              </div>
            </div>
          </header>

          <div class="ic-compare-bar glass-panel">
            <div class="ic-compare-group">
              <label class="ic-check">
                <input v-model="compare.a.enabled" type="checkbox" />
                本周期
              </label>
              <input v-model="compare.a.start" class="ic-input" type="date" />
              <span class="ic-date-sep">至</span>
              <input v-model="compare.a.end" class="ic-input" type="date" />
            </div>
            <div class="ic-compare-group">
              <label class="ic-check">
                <input v-model="compare.b.enabled" type="checkbox" />
                上周期
              </label>
              <input v-model="compare.b.start" class="ic-input" type="date" />
              <span class="ic-date-sep">至</span>
              <input v-model="compare.b.end" class="ic-input" type="date" />
            </div>
            <div class="ic-compare-actions">
              <button class="ic-tool-btn primary" @click="renderCompare">更新对比</button>
            </div>
          </div>

          <div ref="compareRef" class="ic-chart tall"></div>

          <div class="ic-compare-summary">
            <div class="ic-kpi">
              <div class="ic-kpi-label">本周期事件</div>
              <div class="ic-kpi-value">{{ compareSummary.aTotal }}</div>
            </div>
            <div class="ic-kpi">
              <div class="ic-kpi-label">上周期事件</div>
              <div class="ic-kpi-value">{{ compareSummary.bTotal }}</div>
            </div>
            <div class="ic-kpi">
              <div class="ic-kpi-label">变化</div>
              <div class="ic-kpi-value" :class="{ up: compareSummary.deltaPct > 0, down: compareSummary.deltaPct < 0 }">
                {{ compareSummary.deltaPct > 0 ? '+' : '' }}{{ compareSummary.deltaPct }}%
              </div>
            </div>
          </div>

          <!-- 语义差分看板 + AI 叙事 -->
          <div class="ic-semantic-card glass-panel">
            <div class="ic-card-head ic-semantic-head">
              <div class="ic-title">
                <span class="ic-dot emerald"></span>
                <div>
                  <h3>语义差分看板 · AI 解读</h3>
                  <p class="ic-sub">
                    基于 Top10 商品语义与行为强度，解释本期与上期「为什么会不一样」
                  </p>
                </div>
              </div>
              <div class="ic-semantic-status">
                <span v-if="semanticLoading" class="ic-sub">AI 正在分析...</span>
                <span v-else-if="semanticError" class="ic-sub error">{{ semanticError }}</span>
              </div>
            </div>

            <div v-if="semanticDiff" class="ic-semantic-body">
              <!-- AI 叙事总结 -->
              <p class="ic-semantic-summary">
                {{ semanticDiff.summary_text }}
              </p>

              <!-- 语义重心迁移 -->
              <div class="ic-focus-shift-row">
                <div class="ic-focus-pill from">
                  <span class="label">上期焦点</span>
                  <span class="value">{{ semanticDiff.focus_shift?.from_focus || '—' }}</span>
                </div>
                <div class="ic-focus-arrow">→</div>
                <div class="ic-focus-pill to">
                  <span class="label">本期焦点</span>
                  <span class="value">{{ semanticDiff.focus_shift?.to_focus || '—' }}</span>
                </div>
                <div class="ic-intent-chip" :class="{ up: (semanticDiff.focus_shift?.intent_delta_pct || 0) > 0, down: (semanticDiff.focus_shift?.intent_delta_pct || 0) < 0 }">
                  意图强度
                  <span class="num">
                    {{ semanticDiff.focus_shift?.intent_delta_pct > 0 ? '+' : '' }}{{ semanticDiff.focus_shift?.intent_delta_pct ?? 0 }}%
                  </span>
                </div>
              </div>
              <div class="ic-focus-desc">
                {{ semanticDiff.focus_shift?.focus_shift_desc }}
              </div>

              <!-- 关键语义维度差分列表 -->
              <div class="ic-semantic-dims soft-scrollbar">
                <div
                  v-for="dim in semanticDiff.semantic_diff_board || []"
                  :key="dim.dimension"
                  class="ic-dim-row"
                >
                  <div class="ic-dim-main">
                    <div class="ic-dim-name">{{ dim.dimension }}</div>
                    <div class="ic-dim-bars">
                      <div class="ic-dim-bar before">
                        <span class="label">上期</span>
                        <div class="bar">
                          <div
                            class="fill"
                            :style="{ width: Math.min(100, (dim.weight_before || 0) * 100) + '%' }"
                          ></div>
                        </div>
                      </div>
                      <div class="ic-dim-bar after">
                        <span class="label">本期</span>
                        <div class="bar">
                          <div
                            class="fill"
                            :style="{ width: Math.min(100, (dim.weight_after || 0) * 100) + '%' }"
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="ic-dim-meta">
                    <span
                      class="delta"
                      :class="{
                        up: dim.direction === 'up',
                        down: dim.direction === 'down',
                      }"
                    >
                      {{ dim.direction === 'up' ? '↑' : dim.direction === 'down' ? '↓' : '→' }}
                      {{ dim.delta > 0 ? '+' : '' }}{{ dim.delta }}
                    </span>
                    <span class="comment">{{ dim.comment }}</span>
                  </div>
                </div>
              </div>

              <!-- 健康度红/绿呼吸灯 -->
              <div class="ic-health-row">
                <div class="ic-health-block">
                  <div class="ic-health-title">
                    <span
                      class="ic-health-dot breathe"
                      :class="`status-${semanticDiff.health?.overall_health || 'warning'}`"
                    ></span>
                    整体兴趣健康度
                  </div>
                  <div class="ic-health-tag">
                    {{ semanticDiff.health?.overall_health || '—' }}
                  </div>
                </div>

                <div class="ic-health-block">
                  <div class="ic-health-title">
                    <span
                      class="ic-health-dot breathe"
                      :class="`status-${semanticDiff.health?.behavior_depth_health || 'warning'}`"
                    ></span>
                    行为深度健康度
                  </div>
                  <div class="ic-health-tag">
                    {{ semanticDiff.health?.behavior_depth_health || '—' }}
                  </div>
                </div>

                <div class="ic-health-block suggestion">
                  <div class="ic-health-title">AI 建议</div>
                  <div class="ic-health-text">
                    {{ semanticDiff.health?.suggested_action }}
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="!semanticLoading && !semanticError" class="ic-hint ic-semantic-empty">
              请选择完整的本期/上期时间范围并点击「更新对比」，AI 将为你解读语义差异与健康度。
            </div>
          </div>
        </div>
      </div>

      <!-- ANOMALY -->
      <div v-else class="ic-grid">
        <div class="ic-card glass-elevated floaty wide">
          <header class="ic-card-head">
            <div class="ic-title">
              <span class="ic-dot emerald"></span>
              <div>
                <h3>异常检测</h3>
                <p class="ic-sub">基于按天事件量的 Z-Score 置信区间，识别兴趣突变与新兴兴趣</p>
              </div>
            </div>
            <div class="ic-anom-tools">
              <label class="ic-field inline">
                <span class="ic-field-label">敏感度</span>
                <input v-model.number="anomaly.sensitivity" class="ic-input short" type="number" step="0.1" min="1" max="5" />
              </label>
              <button class="ic-tool-btn primary" @click="renderAnomaly">重新检测</button>
            </div>
          </header>

          <div ref="anomalyRef" class="ic-chart tall"></div>

          <!-- 兴趣偏移预测预警 -->
          <div v-if="anomalies.some((x) => x.willShiftProfile)" class="ic-anom-warning glass-panel">
            <div class="ic-anom-warning-main">
              <div class="ic-anom-warning-title">系统发现可能存在新的兴趣领域</div>
              <div class="ic-anom-warning-text">
                若这类异常行为在未来 3 天持续，用户画像在对应方向上的权重将发生明显偏移，建议评估并适当调整推荐策略。
              </div>
            </div>
            <div class="ic-anom-warning-actions">
              <button class="ic-tool-btn ghost small">稍后再说</button>
              <button class="ic-tool-btn primary small">查看推荐策略</button>
            </div>
          </div>

          <div class="ic-anom-list glass-panel">
            <div class="ic-inner-title">检测到的异常（{{ anomalies.length }}）</div>
            <div class="ic-anom-items soft-scrollbar">
              <div v-for="a in anomalies" :key="a.day" class="ic-anom-item">
                <div class="ic-anom-left">
                  <div class="ic-anom-day">{{ a.day }}</div>
                  <div class="ic-anom-tag" :class="`type-${a.type}`">
                    {{ a.typeLabel }}
                  </div>
                </div>
                <div class="ic-anom-meta">
                  <div>值：<b>{{ a.value }}</b></div>
                  <div>Z：<b>{{ a.z.toFixed(2) }}</b></div>
                  <div class="ic-anom-extra">
                    <span class="ic-anom-reason">{{ a.reason }}</span>
                    <span v-if="a.projectedShiftPct" class="ic-anom-pred">
                      若持续 3 天，该方向权重预计变化 {{ a.projectedShiftPct }}%
                    </span>
                  </div>
                </div>
              </div>
              <div v-if="!anomalies.length" class="ic-hint">未检测到异常波动</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { fetchBehaviorSankey, fetchInsightEvents, fetchInsightSemanticDiff, fetchVectorDrift } from '../api'
import { mockFetchInsightSemanticDiff } from '../mocks/insightsMock'

const props = defineProps({
  userId: { type: String, required: true },
})

const tabs = [
  { key: 'basic', label: '基础图表' },
  { key: 'drill', label: '数据钻取' },
  { key: 'compare', label: '数据对比' },
  { key: 'anomaly', label: '异常检测' },
]

const activeTab = ref('basic')
const filterOpen = ref(false)

const filters = reactive({
  start: '',
  end: '',
  action: '',
  category: '',
  q: '',
})

const compare = reactive({
  a: { enabled: true, start: '', end: '' },
  b: { enabled: true, start: '', end: '' },
})

const anomaly = reactive({
  sensitivity: 2.2,
})

const drill = reactive({
  category: '',
  productId: '',
  productName: '',
})

const loading = ref(false)
const raw = ref({ overview: null, events: [] })

const overview = computed(() => raw.value.overview)
const events = computed(() => raw.value.events || [])

const donutRef = ref(null)
const trendRef = ref(null)
const compareRef = ref(null)
const anomalyRef = ref(null)
const drillDonutRef = ref(null)
const drillTrendRef = ref(null)
const vectorDriftRef = ref(null)
const sankeyRef = ref(null)

let donutChart = null
let trendChart = null
let compareChart = null
let anomalyChart = null
let drillDonutChart = null
let drillTrendChart = null
let vectorDriftChart = null
let sankeyChart = null

const formatCategory = (c) => {
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

const actionOptions = computed(() => {
  const list = overview.value?.distribution?.by_action?.map((x) => x.name) || []
  // 去重 + 保序
  return [...new Set(list.filter(Boolean))]
})

const categoryOptions = computed(() => {
  const list = overview.value?.distribution?.by_category?.map((x) => x.name) || []
  return [...new Set(list.filter(Boolean))]
})

const topActions = computed(() => (overview.value?.distribution?.by_action || []).slice(0, 4))
const topCategories = computed(() => (overview.value?.distribution?.by_category || []).slice(0, 4))

const buildDonutOption = (items, title = '分布') => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'item', formatter: '{b}<br/>数量：{c}（{d}%）' },
  legend: {
    orient: 'vertical',
    right: 10,
    top: 20,
    textStyle: { color: '#808089' },
    formatter: (name) => formatCategory(name),
  },
  series: [
    {
      name: title,
      type: 'pie',
      radius: ['48%', '72%'],
      center: ['34%', '50%'],
      itemStyle: { borderRadius: 10, borderColor: 'rgba(255,255,255,0.9)', borderWidth: 2 },
      label: { color: '#27272f', formatter: (p) => formatCategory(p.name) },
      labelLine: { length: 10, length2: 8 },
      emphasis: { scale: true, scaleSize: 10 },
      animationEasing: 'cubicOut',
      animationDuration: 650,
      data: items || [],
    },
  ],
})

const buildTrendOption = (series, title = '事件量') => ({
  backgroundColor: 'transparent',
  grid: { left: '6%', right: '4%', top: 40, bottom: 28, containLabel: true },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: series.map((d) => d.day),
    axisLine: { lineStyle: { color: 'rgba(39,39,47,0.25)' } },
    axisLabel: { color: '#808089' },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    axisLabel: { color: '#808089' },
    splitLine: { lineStyle: { color: 'rgba(39,39,47,0.08)', type: 'dashed' } },
  },
  series: [
    {
      name: title,
      type: 'line',
      smooth: true,
      data: series.map((d) => d.value),
      symbolSize: 7,
      itemStyle: { color: '#f97316' },
      lineStyle: { width: 2.4, color: '#fb923c' },
      areaStyle: { opacity: 0.12, color: '#fdba74' },
    },
  ],
})

const dailySeriesFromEvents = (evs) => {
  const m = new Map()
  for (const e of evs) {
    if (!e.day) continue
    m.set(e.day, (m.get(e.day) || 0) + 1)
  }
  const days = [...m.keys()].sort()
  return days.map((d) => ({ day: d, value: m.get(d) }))
}

const categoryRows = computed(() => {
  const dist = overview.value?.distribution?.by_category || []
  // 趋势：最近 7 天 vs 之前 7 天（简化版）
  const s = overview.value?.timeseries || []
  const last = s.slice(-7).reduce((acc, x) => acc + (x.value || 0), 0)
  const prev = s.slice(-14, -7).reduce((acc, x) => acc + (x.value || 0), 0)
  const deltaBase = prev <= 0 ? null : Math.round(((last - prev) / prev) * 100)
  return dist.map((x) => ({
    name: x.name,
    value: x.value,
    delta: deltaBase === null ? 0 : deltaBase,
  }))
})

const drillEvents = computed(() => (drill.category ? events.value.filter((e) => e.category === drill.category) : []))

const drillTopProducts = computed(() => {
  const m = new Map()
  for (const e of drillEvents.value) {
    const pid = e.product_id || 'unknown'
    const cur = m.get(pid) || { product_id: pid, product_name: e.product_name, image_url: e.image_url, count: 0 }
    cur.count += 1
    // 补齐展示信息
    cur.product_name = cur.product_name || e.product_name
    cur.image_url = cur.image_url || e.image_url
    m.set(pid, cur)
  }
  return [...m.values()].sort((a, b) => b.count - a.count).slice(0, 8)
})

const compareSummary = reactive({ aTotal: 0, bTotal: 0, deltaPct: 0 })

// 语义差分看板 & AI 叙事（数据对比 Tab）
const semanticDiff = ref(null)
const semanticLoading = ref(false)
const semanticError = ref('')

const anomalies = ref([])
const sankeyReady = ref(false)

const buildVectorDriftOption = (payload, focusProductId, focusProductName) => {
  if (!payload || !Array.isArray(payload.points) || !payload.points.length) {
    return {
      backgroundColor: 'transparent',
      title: { text: '暂无向量轨迹数据', left: 'center', top: 'middle', textStyle: { color: '#9ca3af', fontSize: 13 } },
    }
  }

  const points = payload.points || []
  const segments = payload.segments || []

  const allPoints = points.map((p) => [p.x, p.y])

  const byStepSemantic = new Map()
  for (const seg of segments) {
    if (typeof seg.to_step === 'number' && seg.semantic_shift) {
      byStepSemantic.set(seg.to_step, seg.semantic_shift)
    }
  }

  const focusPoints = points
    .map((p, idx) => ({ p, idx }))
    .filter(({ p }) => p.product_id && p.product_id === focusProductId)
    .map(({ p, idx }) => ({
      value: [p.x, p.y],
      step: idx,
      action: p.action,
      product_id: p.product_id,
      delta_norm: p.delta_norm,
      semantic_shift: byStepSemantic.get(idx),
    }))

  const scatterAll = points.map((p, idx) => ({
    value: [p.x, p.y],
    step: idx,
    action: p.action,
    product_id: p.product_id,
    delta_norm: p.delta_norm,
    semantic_shift: byStepSemantic.get(idx),
  }))

  return {
    backgroundColor: 'transparent',
    grid: { left: '6%', right: '4%', top: 36, bottom: 28, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (param) => {
        const d = param.data || {}
        const step = typeof d.step === 'number' ? d.step : param.dataIndex
        const action = d.action || 'unknown'
        const delta = d.delta_norm != null ? Number(d.delta_norm).toFixed(4) : '0.0000'
        const semantic = d.semantic_shift || '该行为对画像影响有限，用于微调近期兴趣方向。'
        const pid = d.product_id || ''
        const productLine = pid && focusProductId && pid === focusProductId ? `<br/>商品：${focusProductName || pid}` : ''
        return [
          `Step #${step}`,
          `行为：${action}`,
          `向量位移：${delta}`,
          productLine,
          `语义：${semantic}`,
        ]
          .filter(Boolean)
          .join('<br/>')
      },
    },
    xAxis: {
      type: 'value',
      name: '语义 X',
      nameLocation: 'middle',
      nameGap: 24,
      axisLine: { lineStyle: { color: 'rgba(39,39,47,0.25)' } },
      axisLabel: { color: '#808089' },
      splitLine: { lineStyle: { color: 'rgba(39,39,47,0.08)', type: 'dashed' } },
    },
    yAxis: {
      type: 'value',
      name: '语义 Y',
      nameLocation: 'middle',
      nameGap: 28,
      axisLine: { lineStyle: { color: 'rgba(39,39,47,0.25)' } },
      axisLabel: { color: '#808089' },
      splitLine: { lineStyle: { color: 'rgba(39,39,47,0.08)', type: 'dashed' } },
    },
    series: [
      {
        name: '整体轨迹',
        type: 'line',
        data: allPoints,
        smooth: true,
        lineStyle: { width: 1.5, color: '#d4d4d8' },
        symbol: 'none',
        z: 1,
      },
      {
        name: '所有行为节点',
        type: 'scatter',
        data: scatterAll,
        symbolSize: 6,
        itemStyle: { color: '#9ca3af' },
        z: 2,
      },
      {
        name: '当前商品相关节点',
        type: 'scatter',
        data: focusPoints,
        symbolSize: 10,
        itemStyle: { color: '#fb923c' },
        z: 3,
      },
    ],
  }
}

const buildSankeyOption = (payload) => {
  if (!payload || !Array.isArray(payload.nodes) || !payload.nodes.length) {
    return {
      backgroundColor: 'transparent',
      title: { text: '暂无行为路径数据', left: 'center', top: 'middle', textStyle: { color: '#9ca3af', fontSize: 13 } },
    }
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        if (p.dataType === 'edge') {
          return `${p.data.source} → ${p.data.target}<br/>次数：${p.data.value}`
        }
        return `${p.name}`
      },
    },
    series: [
      {
        type: 'sankey',
        data: payload.nodes,
        links: payload.links,
        top: 10,
        left: '5%',
        right: '10%',
        bottom: 10,
        nodeAlign: 'justify',
        nodeGap: 14,
        nodeWidth: 12,
        label: { color: '#374151', fontSize: 11 },
        lineStyle: {
          color: 'gradient',
          opacity: 0.45,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { opacity: 0.8 },
        },
      },
    ],
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.start) params.start = filters.start
    if (filters.end) params.end = filters.end
    if (filters.action) params.action = filters.action
    if (filters.category) params.category = filters.category
    if (filters.q) params.q = filters.q
    const { data } = await fetchInsightEvents(props.userId, params)
    raw.value = { overview: data.overview, events: data.events }
  } finally {
    loading.value = false
  }
}

const initOrUpdateVectorDriftChart = async () => {
  if (!drill.productId) return
  await nextTick()
  if (vectorDriftRef.value && !vectorDriftChart) vectorDriftChart = echarts.init(vectorDriftRef.value)

  const { data } = await fetchVectorDrift(props.userId, { max_events: 120 })
  const option = buildVectorDriftOption(data, drill.productId, drill.productName)
  vectorDriftChart?.setOption(option, true)
}

const initOrUpdateSankeyChart = async () => {
  await nextTick()
  if (sankeyRef.value && !sankeyChart) sankeyChart = echarts.init(sankeyRef.value)

  const { data } = await fetchBehaviorSankey(props.userId, { limit: 500 })
  sankeyReady.value = Array.isArray(data.nodes) && data.nodes.length > 0
  const option = buildSankeyOption(data)
  sankeyChart?.setOption(option, true)
}

const renderSemanticDiff = async () => {
  // 只有在两个时间段都启用且选择了完整日期范围时才触发 AI 语义对比
  if (
    !compare.a.enabled ||
    !compare.b.enabled ||
    !compare.a.start ||
    !compare.a.end ||
    !compare.b.start ||
    !compare.b.end
  ) {
    semanticDiff.value = null
    semanticError.value = ''
    return
  }

  semanticLoading.value = true
  semanticError.value = ''
  try {
    const params = {
      a_start: compare.a.start,
      a_end: compare.a.end,
      b_start: compare.b.start,
      b_end: compare.b.end,
    }

    // 先尝试后端 / 通用接口（内部可能已做一次 mock 兜底）
    const { data } = await fetchInsightSemanticDiff(props.userId, params)

    // 规范化并检查关键字段是否“真有内容”
    const d = data || {}
    const board = Array.isArray(d.semantic_diff_board) ? d.semantic_diff_board : []
    const hasSummary =
      typeof d.summary_text === 'string' && d.summary_text.trim().length > 0
    const hasBoard = board.length > 0
    const hasHealth =
      !!(d.health &&
      (d.health.overall_health ||
        d.health.behavior_depth_health ||
        d.health.suggested_action))

    // 如果后端没有返回可用内容（字段缺失或全为空），则用前端本地 mock 做二次兜底
    if (!hasSummary && !hasBoard && !hasHealth) {
      semanticDiff.value = mockFetchInsightSemanticDiff(props.userId, params)
    } else {
      // 同时把语义维度表标准化回组件预期格式，避免出现 undefined 结构导致模板渲染为空
      semanticDiff.value = {
        ...d,
        semantic_diff_board: board,
      }
    }
  } catch (err) {
    console.error('语义差分对比加载失败：', err)
    // 如果接口异常，同样使用前端 mock 语义结果兜底，保证页面有内容可看
    try {
      semanticDiff.value = mockFetchInsightSemanticDiff(props.userId, {
        a_start: compare.a.start,
        a_end: compare.a.end,
        b_start: compare.b.start,
        b_end: compare.b.end,
      })
      semanticError.value = ''
    } catch (mockErr) {
      console.error('本地 mock 语义差分生成失败：', mockErr)
      semanticError.value = 'AI 语义差分暂不可用，可稍后重试。'
      semanticDiff.value = null
    }
  } finally {
    semanticLoading.value = false
  }
}

const initOrUpdateBasicCharts = async () => {
  await nextTick()
  if (donutRef.value && !donutChart) donutChart = echarts.init(donutRef.value)
  if (trendRef.value && !trendChart) trendChart = echarts.init(trendRef.value)

  const catItems = overview.value?.distribution?.by_category || []
  donutChart?.setOption(buildDonutOption(catItems, '类目分布'), true)
  donutChart?.off('click')
  donutChart?.on('click', (p) => goDrillCategory(p.name))

  const series = overview.value?.timeseries || dailySeriesFromEvents(events.value)
  trendChart?.setOption(buildTrendOption(series, '事件量'), true)
}

const initOrUpdateDrillCharts = async () => {
  await nextTick()
  if (!drill.category) return

  if (drillDonutRef.value && !drillDonutChart) drillDonutChart = echarts.init(drillDonutRef.value)
  if (drillTrendRef.value && !drillTrendChart) drillTrendChart = echarts.init(drillTrendRef.value)

  const byAction = {}
  for (const e of drillEvents.value) {
    const k = e.action || 'unknown'
    byAction[k] = (byAction[k] || 0) + 1
  }
  const actionItems = Object.entries(byAction)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  drillDonutChart?.setOption(buildDonutOption(actionItems, '行为分布'), true)
  drillTrendChart?.setOption(buildTrendOption(dailySeriesFromEvents(drillEvents.value), '类目事件量'), true)
}

const handleClickProduct = async (p) => {
  drill.productId = p.product_id
  drill.productName = p.product_name || p.product_id
  await initOrUpdateVectorDriftChart()
  await initOrUpdateSankeyChart()
}

const renderCompare = async () => {
  await nextTick()
  if (compareRef.value && !compareChart) compareChart = echarts.init(compareRef.value)

  const seriesA = compare.a.enabled ? filterEventsByRange(events.value, compare.a.start, compare.a.end) : []
  const seriesB = compare.b.enabled ? filterEventsByRange(events.value, compare.b.start, compare.b.end) : []

  const dailyA = dailySeriesFromEvents(seriesA)
  const dailyB = dailySeriesFromEvents(seriesB)
  const days = mergeDays(dailyA, dailyB)

  const mapA = new Map(dailyA.map((d) => [d.day, d.value]))
  const mapB = new Map(dailyB.map((d) => [d.day, d.value]))
  const yA = days.map((d) => mapA.get(d) || 0)
  const yB = days.map((d) => mapB.get(d) || 0)

  compareSummary.aTotal = yA.reduce((a, b) => a + b, 0)
  compareSummary.bTotal = yB.reduce((a, b) => a + b, 0)
  compareSummary.deltaPct =
    compareSummary.bTotal > 0
      ? Math.round(((compareSummary.aTotal - compareSummary.bTotal) / compareSummary.bTotal) * 100)
      : 0

  compareChart?.setOption(
    {
      backgroundColor: 'transparent',
      grid: { left: '6%', right: '4%', top: 44, bottom: 28, containLabel: true },
      tooltip: { trigger: 'axis' },
      legend: { top: 10, textStyle: { color: '#808089' } },
      xAxis: {
        type: 'category',
        data: days,
        axisLine: { lineStyle: { color: 'rgba(39,39,47,0.25)' } },
        axisLabel: { color: '#808089' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#808089' },
        splitLine: { lineStyle: { color: 'rgba(39,39,47,0.08)', type: 'dashed' } },
      },
      series: [
        compare.a.enabled
          ? {
              name: '本周期',
              type: 'line',
              smooth: true,
              data: yA,
              itemStyle: { color: '#f97316' },
              lineStyle: { width: 2.4 },
            }
          : null,
        compare.b.enabled
          ? {
              name: '上周期',
              type: 'line',
              smooth: true,
              data: yB,
              itemStyle: { color: '#60a5fa' },
              lineStyle: { width: 2.2, type: 'dashed' },
            }
          : null,
      ].filter(Boolean),
    },
    true,
  )

  // 同步触发语义差分看板的 AI 解析
  await renderSemanticDiff()
}

const renderAnomaly = async () => {
  await nextTick()
  if (anomalyRef.value && !anomalyChart) anomalyChart = echarts.init(anomalyRef.value)
  const series = overview.value?.timeseries || dailySeriesFromEvents(events.value)

  const values = series.map((x) => x.value || 0)
  const mean = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0
  const variance =
    values.length > 1 ? values.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / (values.length - 1) : 0
  const std = Math.sqrt(variance) || 1
  const threshold = Number(anomaly.sensitivity || 2.2)

  // 简单线性回归：用于预测未来 3 天若趋势持续，事件量会到什么水平
  let slope = 0
  let intercept = mean
  if (values.length >= 3) {
    const n = values.length
    let sumX = 0
    let sumY = 0
    let sumXY = 0
    let sumX2 = 0
    for (let i = 0; i < n; i++) {
      const x = i
      const y = values[i]
      sumX += x
      sumY += y
      sumXY += x * y
      sumX2 += x * x
    }
    const denom = n * sumX2 - sumX * sumX
    if (denom !== 0) {
      slope = (n * sumXY - sumX * sumY) / denom
      intercept = (sumY - slope * sumX) / n
    }
  }

  const predictAt = (x) => intercept + slope * x
  const futureIndex = values.length + 3
  const futureValue = predictAt(futureIndex)
  const futureZ = std > 0 ? (futureValue - mean) / std : 0
  const willProfileShiftGlobally = futureZ >= 2.5 && slope > 0

  const out = []
  for (let i = 0; i < series.length; i++) {
    const z = (values[i] - mean) / std
    if (Math.abs(z) >= threshold) {
      out.push({ day: series[i].day, value: values[i], z, index: i })
    }
  }

  // 对异常点做简单语义分类：突发性强意图 / 新兴趣发现 / 行为骤减
  const detailed = out.map((a) => {
    const idx = a.index
    const n = values.length
    const winStart = Math.max(0, idx - 2)
    const winEnd = Math.min(n - 1, idx + 2)
    const neighborValues = []
    for (let k = winStart; k <= winEnd; k++) {
      if (k === idx) continue
      neighborValues.push(values[k])
    }
    const neighborMean =
      neighborValues.length > 0 ? neighborValues.reduce((acc, v) => acc + v, 0) / neighborValues.length : mean
    const localRatio = neighborMean > 0 ? a.value / neighborMean : 0

    let type = 'new'
    let typeLabel = '新兴趣发现'
    let reason = '该日期的行为量相较周边有持续抬升，可能代表一个新兴兴趣方向正在形成。'

    if (a.z >= threshold) {
      // 正向异常
      if (localRatio >= 1.6) {
        type = 'strong'
        typeLabel = '突发性强意图'
        reason = '该日行为量远高于周边，且呈尖刺形态，更像是一次性强需求或紧急意图。'
      } else {
        type = 'new'
        typeLabel = '新兴趣发现'
        reason = '该日行为量在整体上扬趋势中明显偏高，疑似一个新的兴趣主题正在被持续探索。'
      }
    } else {
      // 负向异常
      type = 'drop'
      typeLabel = '行为骤减'
      reason = '该日行为量显著低于常态，可能是该方向兴趣下降或外部因素导致。'
    }

    // 预测 3 天后的权重偏移幅度（用未来 Z 分数粗略映射为百分比）
    const projectedShiftScore = Math.max(-3, Math.min(3, futureZ))
    const projectedShiftPct =
      projectedShiftScore !== 0 ? Math.round(Math.max(5, Math.min(60, Math.abs(projectedShiftScore) * 10))) : 0

    return {
      ...a,
      type,
      typeLabel,
      reason,
      projectedShiftPct,
      willShiftProfile: willProfileShiftGlobally && (type === 'new' || type === 'strong'),
    }
  })

  anomalies.value = detailed

  const upperBand = values.map(() => mean + threshold * std)
  const lowerBand = values.map(() => mean - threshold * std)

  anomalyChart?.setOption(
    {
      backgroundColor: 'transparent',
      grid: { left: '6%', right: '4%', top: 44, bottom: 28, containLabel: true },
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: series.map((d) => d.day),
        axisLine: { lineStyle: { color: 'rgba(39,39,47,0.25)' } },
        axisLabel: { color: '#808089' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#808089' },
        splitLine: { lineStyle: { color: 'rgba(39,39,47,0.08)', type: 'dashed' } },
      },
      series: [
        {
          name: '事件量',
          type: 'line',
          smooth: true,
          data: values,
          symbolSize: 7,
          itemStyle: { color: '#fb923c' },
          lineStyle: { width: 2.4, color: '#f97316' },
        },
        {
          name: '上置信边界',
          type: 'line',
          data: upperBand,
          symbol: 'none',
          lineStyle: { width: 1.2, type: 'dashed', color: 'rgba(59,130,246,0.7)' },
        },
        {
          name: '下置信边界',
          type: 'line',
          data: lowerBand,
          symbol: 'none',
          lineStyle: { width: 1.2, type: 'dashed', color: 'rgba(59,130,246,0.4)' },
        },
        {
          name: '异常点',
          type: 'scatter',
          data: detailed.map((a) => [a.day, a.value]),
          symbolSize: 12,
          itemStyle: { color: '#ef4444' },
        },
      ],
    },
    true,
  )
}

const handleRefresh = async () => {
  await fetchData()
  if (activeTab.value === 'basic') await initOrUpdateBasicCharts()
  if (activeTab.value === 'drill') await initOrUpdateDrillCharts()
  if (activeTab.value === 'compare') await renderCompare()
  if (activeTab.value === 'anomaly') await renderAnomaly()
}

const handleResetFilters = () => {
  filters.start = ''
  filters.end = ''
  filters.action = ''
  filters.category = ''
  filters.q = ''
}

const goDrillCategory = async (cat) => {
  drill.category = cat
  activeTab.value = 'drill'
  await initOrUpdateDrillCharts()
}

const resetDrill = () => {
  drill.category = ''
  drill.productId = ''
  drill.productName = ''
}

const filterEventsByRange = (evs, start, end) => {
  const s = start ? new Date(start + 'T00:00:00') : null
  const e = end ? new Date(end + 'T23:59:59') : null
  return evs.filter((x) => {
    if (!x.timestamp) return true
    const t = new Date(x.timestamp)
    if (s && t < s) return false
    if (e && t > e) return false
    return true
  })
}

const mergeDays = (a, b) => {
  const s = new Set([...(a || []).map((x) => x.day), ...(b || []).map((x) => x.day)].filter(Boolean))
  return [...s].sort()
}

const downloadText = (filename, text, mime = 'text/plain;charset=utf-8') => {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

const downloadDataUrl = (filename, dataUrl) => {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
}

const exportCsvOfCategories = () => {
  const rows = categoryRows.value
  const header = ['category', 'count', 'trend_pct']
  const lines = [header.join(','), ...rows.map((r) => [r.name, r.value, r.delta].join(','))]
  downloadText(`insights_categories_${props.userId}.csv`, lines.join('\n'), 'text/csv;charset=utf-8')
}

const exportChartsPng = () => {
  const list = []
  if (activeTab.value === 'basic') {
    if (donutChart) list.push({ name: 'category_donut', chart: donutChart })
    if (trendChart) list.push({ name: 'trend', chart: trendChart })
  } else if (activeTab.value === 'drill') {
    if (drillDonutChart) list.push({ name: 'drill_action_donut', chart: drillDonutChart })
    if (drillTrendChart) list.push({ name: 'drill_trend', chart: drillTrendChart })
  } else if (activeTab.value === 'compare') {
    if (compareChart) list.push({ name: 'compare', chart: compareChart })
  } else if (activeTab.value === 'anomaly') {
    if (anomalyChart) list.push({ name: 'anomaly', chart: anomalyChart })
  }

  for (const item of list) {
    const url = item.chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: 'transparent' })
    downloadDataUrl(`insights_${item.name}_${props.userId}.png`, url)
  }
}

const handleExport = () => {
  exportChartsPng()
  if (activeTab.value === 'basic') exportCsvOfCategories()
}

const resizeAll = () => {
  donutChart?.resize()
  trendChart?.resize()
  compareChart?.resize()
  anomalyChart?.resize()
  drillDonutChart?.resize()
  drillTrendChart?.resize()
  vectorDriftChart?.resize()
  sankeyChart?.resize()
}

watch(
  () => activeTab.value,
  async (t) => {
    if (t === 'basic') await initOrUpdateBasicCharts()
    if (t === 'drill') await initOrUpdateDrillCharts()
    if (t === 'compare') await renderCompare()
    if (t === 'anomaly') await renderAnomaly()
  },
)

onMounted(async () => {
  await fetchData()
  await initOrUpdateBasicCharts()

  // 初始化对比范围：默认用最后 7 天 vs 前一周
  const ts = (overview.value?.timeseries || []).map((x) => x.day).filter(Boolean)
  const isYmd = (s) => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s)
  if (ts.length && isYmd(ts[ts.length - 1])) {
    const end = ts[ts.length - 1]
    const endDate = new Date(end + 'T00:00:00')
    const startDate = new Date(endDate)
    startDate.setDate(startDate.getDate() - 6)
    const prevEnd = new Date(startDate)
    prevEnd.setDate(prevEnd.getDate() - 1)
    const prevStart = new Date(prevEnd)
    prevStart.setDate(prevStart.getDate() - 6)
    compare.a.start = startDate.toISOString().slice(0, 10)
    compare.a.end = endDate.toISOString().slice(0, 10)
    compare.b.start = prevStart.toISOString().slice(0, 10)
    compare.b.end = prevEnd.toISOString().slice(0, 10)
  }

  window.addEventListener('resize', resizeAll)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAll)
  donutChart?.dispose()
  trendChart?.dispose()
  compareChart?.dispose()
  anomalyChart?.dispose()
  drillDonutChart?.dispose()
  drillTrendChart?.dispose()
  vectorDriftChart?.dispose()
  sankeyChart?.dispose()
})
</script>

<style scoped>
.ic-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ic-top {
  padding: 10px 12px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.segmented {
  padding: 2px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 8px 20px rgba(15, 23, 42, 0.04),
    0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.ic-tab {
  height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.ic-tab:hover {
  transform: translateY(-1px);
  background: rgba(254, 243, 199, 0.55);
  border-color: rgba(249, 115, 22, 0.25);
}

.ic-tab.active {
  background: linear-gradient(120deg, #fff7ed, #fffbeb);
  border-color: rgba(249, 115, 22, 0.8);
  color: var(--accent-deep);
  box-shadow: 0 10px 24px rgba(249, 115, 22, 0.16);
}

.ic-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.ic-tool-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  font-size: 12px;
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}

.ic-tool-btn.ghost {
  background: rgba(255, 255, 255, 0.82);
  color: #3f3f46;
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.04),
    0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-tool-btn.primary {
  background: linear-gradient(to right, #f97316, #fb923c);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(248, 113, 22, 0.28);
}

.ic-tool-btn:hover {
  transform: translateY(-1px);
}

.breathe {
  animation: breathe 2.2s ease-in-out infinite;
}

@keyframes breathe {
  0%,
  100% {
    box-shadow: 0 10px 22px rgba(248, 113, 22, 0.28);
  }
  50% {
    box-shadow: 0 14px 26px rgba(248, 113, 22, 0.4);
  }
}

.ic-date {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  height: 30px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.04),
    0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-date-label {
  font-size: 12px;
  color: var(--text-muted);
}

.ic-date-sep {
  color: var(--text-subtle);
  font-size: 12px;
}

.ic-input,
.ic-select {
  height: 28px;
  border-radius: 999px;
  border: none;
  background: rgba(248, 250, 252, 0.96);
  padding: 0 10px;
  color: #111827;
  font-size: 12px;
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
  outline: none;
}

.ic-input.short {
  width: 88px;
}

.ic-select {
  appearance: none;
}

.ic-filter {
  padding: 12px;
}

.ic-filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  align-items: end;
}

.ic-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ic-field.inline {
  flex-direction: row;
  align-items: center;
}

.ic-field-label {
  font-size: 12px;
  color: var(--text-muted);
}

.ic-field-wide {
  grid-column: span 2;
}

.ic-filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.ic-body {
  flex: 1;
}

.ic-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.ic-card {
  padding: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.floaty {
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.floaty:hover {
  transform: translateY(-2px);
  box-shadow:
    0 24px 55px rgba(15, 23, 42, 0.1),
    0 0 0 1px rgba(148, 163, 184, 0.18);
}

.wide {
  grid-column: 1 / -1;
}

.ic-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.ic-title {
  display: flex;
  gap: 10px;
  align-items: center;
}

.ic-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
}

.ic-sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.ic-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: radial-gradient(circle, #fb923c, #f97316);
  box-shadow: 0 0 12px rgba(249, 115, 22, 0.35);
}

.ic-dot.orange {
  background: radial-gradient(circle, #fdba74, #f97316);
}

.ic-dot.emerald {
  background: radial-gradient(circle, #34d399, #16a34a);
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.3);
}

.ic-kpis {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 2px;
}

.ic-kpi {
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-kpi-label {
  font-size: 12px;
  color: var(--text-muted);
}

.ic-kpi-value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #27272f;
}

.ic-kpi-value.up {
  color: #16a34a;
}

.ic-kpi-value.down {
  color: #ef4444;
}

.ic-mini-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.ic-mini {
  padding: 10px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-mini-title {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.ic-mini-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ic-badge {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.08);
  color: #3f3f46;
  font-size: 12px;
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.22);
}

.ic-chart {
  flex: 1;
  min-height: 280px;
}

.ic-chart.small {
  min-height: 220px;
}

.ic-chart.tall {
  min-height: 360px;
}

.ic-table-wrap {
  overflow: auto;
  border-radius: 16px;
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(255, 255, 255, 0.72);
}

.ic-table th,
.ic-table td {
  padding: 10px 12px;
  font-size: 13px;
  border-bottom: 1px solid rgba(229, 231, 235, 0.9);
}

.ic-table th {
  text-align: left;
  font-weight: 650;
  color: #3f3f46;
  background: rgba(248, 250, 252, 0.9);
  position: sticky;
  top: 0;
}

.ic-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.ic-table .ops {
  text-align: right;
  width: 120px;
}

.ic-row-btn {
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.04),
    0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-row-btn:hover {
  transform: translateY(-1px);
}

.up {
  color: #16a34a;
  font-weight: 650;
}

.down {
  color: #ef4444;
  font-weight: 650;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 22px 12px;
}

.ic-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ic-crumb {
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-crumb-current {
  font-size: 12px;
  color: var(--text-muted);
}

.ic-drill-empty {
  padding: 10px 2px;
}

.ic-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.ic-drill-list {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ic-pill {
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  background: rgba(249, 115, 22, 0.08);
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.22);
}

.ic-drill-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
}

.ic-card-inner {
  padding: 10px;
  border-radius: 18px;
}

.ic-card-inner.wide {
  grid-column: 1 / -1;
}

.ic-inner-title {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.ic-top-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
  padding-right: 4px;
}

.ic-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-item-img {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  object-fit: cover;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
}

.ic-item-name {
  font-size: 13px;
  font-weight: 650;
  color: #27272f;
}

.ic-item-sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-muted);
}

.ic-compare-bar {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 10px;
  padding: 10px;
  border-radius: 18px;
  margin-bottom: 10px;
}

.ic-compare-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ic-check {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
}

.ic-compare-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.ic-compare-summary {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.ic-anom-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ic-anom-list {
  margin-top: 10px;
  padding: 10px;
  border-radius: 18px;
}

.ic-anom-items {
  max-height: 160px;
  overflow: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ic-anom-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-anom-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ic-anom-day {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  color: #3f3f46;
}

.ic-anom-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

.ic-anom-extra {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 280px;
}

.ic-anom-reason {
  font-size: 11px;
}

.ic-anom-pred {
  font-size: 11px;
  color: #2563eb;
}

.ic-anom-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-anom-tag.type-strong {
  background: rgba(251, 146, 60, 0.12);
  color: #9a3412;
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.4);
}

.ic-anom-tag.type-new {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.38);
}

.ic-anom-tag.type-drop {
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
  box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.4);
}

.ic-anom-warning {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ic-anom-warning-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ic-anom-warning-title {
  font-size: 13px;
  font-weight: 650;
  color: #111827;
}

.ic-anom-warning-text {
  font-size: 12px;
  color: var(--text-muted);
}

.ic-anom-warning-actions {
  display: flex;
  gap: 6px;
}

.ic-tool-btn.small {
  height: 26px;
  padding: 0 10px;
  font-size: 11px;
}

/* 语义差分看板 & 健康度 */
.ic-semantic-card {
  margin-top: 12px;
  border-radius: 18px;
}

.ic-semantic-head {
  align-items: center;
}

.ic-semantic-status .error {
  color: #ef4444;
}

.ic-semantic-body {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ic-semantic-summary {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #111827;
}

.ic-focus-shift-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.ic-focus-pill {
  display: flex;
  flex-direction: column;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-focus-pill .label {
  font-size: 11px;
  color: var(--text-muted);
}

.ic-focus-pill .value {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.ic-focus-arrow {
  font-size: 16px;
  color: var(--text-muted);
}

.ic-intent-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(249, 115, 22, 0.08);
  color: #92400e;
  box-shadow: 0 0 0 1px rgba(251, 146, 60, 0.3);
}

.ic-intent-chip .num {
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}

.ic-intent-chip.up {
  background: rgba(22, 163, 74, 0.08);
  color: #14532d;
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.35);
}

.ic-intent-chip.down {
  background: rgba(239, 68, 68, 0.06);
  color: #7f1d1d;
  box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.35);
}

.ic-focus-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.ic-semantic-dims {
  max-height: 180px;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ic-dim-row {
  padding: 6px 8px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ic-dim-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ic-dim-name {
  font-size: 12px;
  font-weight: 600;
  color: #111827;
}

.ic-dim-bars {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.ic-dim-bar .label {
  font-size: 11px;
  color: var(--text-muted);
}

.ic-dim-bar .bar {
  margin-top: 2px;
  height: 6px;
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.9);
  overflow: hidden;
}

.ic-dim-bar .fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(to right, #bfdbfe, #60a5fa);
}

.ic-dim-bar.after .fill {
  background: linear-gradient(to right, #fed7aa, #fb923c);
}

.ic-dim-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.ic-dim-meta .delta {
  font-variant-numeric: tabular-nums;
}

.ic-dim-meta .delta.up {
  color: #16a34a;
  font-weight: 650;
}

.ic-dim-meta .delta.down {
  color: #ef4444;
  font-weight: 650;
}

.ic-health-row {
  margin-top: 2px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  align-items: flex-start;
}

.ic-health-block {
  padding: 8px 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ic-health-block.suggestion {
  grid-column: span 1;
}

.ic-health-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #111827;
}

.ic-health-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #e5e7eb;
  box-shadow: 0 0 10px rgba(148, 163, 184, 0.4);
}

.ic-health-dot.status-good {
  background: radial-gradient(circle, #34d399, #16a34a);
  box-shadow: 0 0 12px rgba(34, 197, 94, 0.6);
}

.ic-health-dot.status-warning {
  background: radial-gradient(circle, #facc15, #eab308);
  box-shadow: 0 0 12px rgba(234, 179, 8, 0.55);
}

.ic-health-dot.status-bad {
  background: radial-gradient(circle, #fb7185, #ef4444);
  box-shadow: 0 0 12px rgba(248, 113, 113, 0.6);
}

.ic-health-tag {
  margin-top: 4px;
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  background: rgba(248, 250, 252, 0.9);
  color: var(--text-muted);
}

.ic-health-text {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

.ic-semantic-empty {
  margin-top: 4px;
}

@media (max-width: 1024px) {
  .ic-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .ic-filter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .ic-field-wide {
    grid-column: auto;
  }
  .ic-compare-bar {
    grid-template-columns: minmax(0, 1fr);
  }
  .ic-kpis,
  .ic-compare-summary {
    grid-template-columns: minmax(0, 1fr);
  }
  .ic-mini-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .ic-health-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>


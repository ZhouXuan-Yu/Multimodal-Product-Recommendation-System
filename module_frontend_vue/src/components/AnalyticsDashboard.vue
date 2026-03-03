<template>
  <div class="dashboard-root">
    <!-- 控制面板：分析操作按钮 + 日期范围选择 -->
    <section class="control-bar glass-panel">
      <div class="btn-group segmented">
        <button
          v-for="action in actions"
          :key="action.key"
          :class="['ctrl-btn', { active: currentAction === action.key }]"
          @click="handleActionClick(action.key)"
        >
          <span class="ctrl-label" :class="{ 'text-glow': currentAction === action.key }">
            {{ action.label }}
          </span>
        </button>
      </div>
      <div class="right-tools">
        <label class="date-label">
          日期范围
          <input
            v-model="dateRange"
            type="text"
            class="date-input"
            placeholder="例如：2025-02-01 ~ 2025-02-07"
          />
        </label>
        <button class="refresh-btn" @click="refreshData">刷新</button>
      </div>
    </section>

    <!-- 可视化区域：环形图 + 组合图 -->
    <section class="charts-grid">
      <div class="chart-card glass-elevated">
        <header class="chart-header">
          <div class="chart-title-block">
            <div class="pulse-dot"></div>
            <div>
              <h3>品类偏好分布</h3>
              <p class="sub">点击扇区可进行下钻查看子类目</p>
            </div>
          </div>
          <button
            v-if="drillStack.length"
            class="back-btn"
            @click="handleDrillBack"
          >
            返回上一级
          </button>
        </header>
        <div ref="donutRef" class="chart-body"></div>
      </div>

      <div class="chart-card glass-elevated">
        <header class="chart-header">
          <div class="chart-title-block">
            <div class="pulse-dot"></div>
            <div>
              <h3>7 日行为趋势 & 转化漏斗</h3>
              <p class="sub">活跃度、浏览次数与加购点击转化率双 Y 轴对比</p>
            </div>
          </div>
        </header>
        <div ref="comboRef" class="chart-body"></div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchUserProfile } from '../api'

const props = defineProps({
  userId: {
    type: String,
    required: true,
  },
})

// 控制栏按钮配置
const actions = [
  { key: 'basic', label: '基础图表' },
  { key: 'drill', label: '数据钻取' },
  { key: 'compare', label: '数据对比' },
  { key: 'anomaly', label: '异常检测' },
  { key: 'filter', label: '筛选' },
  { key: 'export', label: '导出' },
]

const currentAction = ref('basic')
const dateRange = ref('')

// ECharts DOM 引用
const donutRef = ref(null)
const comboRef = ref(null)

// ECharts 实例
let donutChart = null
let comboChart = null

// 原始类目偏好数据 & 下钻栈
const categoryData = ref([])
const drillStack = ref([])

// 为了示意“数据钻取”，构造一个简单的本地子类目映射
// 实际项目中建议在点击后再次请求后端获取子类目数据
const mockSubCategoryMap = {
  数码: ['手机', '相机', '音频设备', '智能穿戴'],
  服饰: ['上衣', '裤装', '鞋履', '配饰'],
  家居: ['客厅', '卧室', '厨房', '收纳'],
  美妆: ['底妆', '护肤', '香水', '彩妆'],
}

// 根据当前类目数组生成环形图 option
const buildDonutOption = (items) => {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>占比：{d}%',
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 20,
      textStyle: {
        color: '#9ca3af',
      },
    },
    series: [
      {
        name: '类目偏好',
        type: 'pie',
        radius: ['42%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#020617',
          borderWidth: 2,
        },
        label: {
          color: '#e5e7eb',
        },
        labelLine: {
          length: 12,
          length2: 8,
        },
        // 添加顺滑的入场动画
        animationEasing: 'cubicOut',
        animationDuration: 800,
        data: items,
      },
    ],
  }
}

// 构造 7 日行为趋势 & 转化率组合图 option
const buildComboOption = (days, activity, views, conversion) => {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#111827',
        },
      },
    },
    grid: {
      left: '6%',
      right: '8%',
      bottom: '10%',
      top: '16%',
      containLabel: true,
    },
    legend: {
      data: ['活跃度评分', '浏览次数', '加购/点击转化率'],
      top: 8,
      textStyle: {
        color: '#9ca3af',
      },
    },
    xAxis: [
      {
        type: 'category',
        data: days,
        axisLine: { lineStyle: { color: '#4b5563' } },
        axisLabel: { color: '#9ca3af' },
      },
    ],
    yAxis: [
      {
        type: 'value',
        name: '活跃度 / 浏览',
        axisLine: { lineStyle: { color: '#4b5563' } },
        axisLabel: { color: '#9ca3af' },
        splitLine: {
          lineStyle: {
            color: 'rgba(55, 65, 81, 0.5)',
            type: 'dashed',
          },
        },
      },
      {
        type: 'value',
        name: '转化率 %',
        axisLine: { lineStyle: { color: '#4b5563' } },
        axisLabel: { color: '#9ca3af' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '浏览次数',
        type: 'bar',
        data: views,
        barWidth: 12,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#38bdf8' },
            { offset: 1, color: '#0ea5e9' },
          ]),
          borderRadius: [6, 6, 0, 0],
        },
      },
      {
        name: '活跃度评分',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: activity,
        symbolSize: 8,
        itemStyle: {
          color: '#a855f7',
        },
        lineStyle: {
          width: 2,
        },
      },
      {
        name: '加购/点击转化率',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        data: conversion,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: {
          color: '#22c55e',
        },
        lineStyle: {
          width: 2,
          type: 'dashed',
        },
        areaStyle: {
          opacity: 0.08,
          color: '#16a34a',
        },
      },
    ],
  }
}

// 从后端加载用户画像与行为数据
const loadData = async () => {
  try {
    const { data } = await fetchUserProfile(props.userId)
    // category_preferences: { "数码": 0.3, "服饰": 0.2, ... }
    const pref = data.category_preferences || {}
    const categories = Object.keys(pref)
    const values = Object.values(pref).map((v) => Number(v))

    // 归一 + 转换为 ECharts pie 需要的数据结构
    const items = categories.map((name, idx) => ({
      name,
      value: Number((values[idx] * 100).toFixed(2)),
    }))
    categoryData.value = items

    // recent_activity 兼容两种结构：
    // 1) [{ day, activity_score, views, conversion_rate }]
    // 2) [1, 3, 2, ...] 仅有活跃度分数的简化数组（来自本地 users_profile.json）
    const rawRecent = data.recent_activity || []
    let days = []
    let activity = []
    let views = []
    let conversion = []

    if (rawRecent.length && typeof rawRecent[0] === 'number') {
      // 只有活跃度分值时，构造一个简单的 7 日时间轴
      days = rawRecent.map((_, idx) => `D${idx + 1}`)
      activity = rawRecent.map((v) => Number(v))
      // 用活跃度的缩放值模拟浏览次数和转化率，便于前端有可视曲线
      views = rawRecent.map((v) => Number(v) * 20)
      conversion = rawRecent.map((v) => Number((Math.min(0.35, 0.05 + v * 0.01)).toFixed(3)) * 100)
    } else {
      days = rawRecent.map((d, idx) => d.day || d.date || `D${idx + 1}`)
      activity = rawRecent.map((d) => d.activity_score ?? 0)
      views = rawRecent.map((d) => d.views ?? 0)
      conversion = rawRecent.map((d) => Number((d.conversion_rate ?? 0) * 100))
    }

    // 初始化 / 刷新两个图表（先使用基础模式）
    if (donutChart) {
      donutChart.setOption(buildDonutOption(items))
    }
    if (comboChart) {
      comboChart.setOption(buildComboOption(days, activity, views, conversion))
    }

    applyActionMode()
  } catch (e) {
    console.error('加载用户画像数据失败', e)
  }
}

// 根据当前选中的分析模式，对图表做不同的可视化“增强效果”
const applyActionMode = () => {
  console.debug('[AnalyticsDashboard] 切换分析模式', currentAction.value)

  if (!donutChart || !comboChart || !categoryData.value.length) return

  const baseItems = categoryData.value

  if (currentAction.value === 'basic') {
    // 基础图表：直接使用原始数据
    donutChart.setOption(buildDonutOption(baseItems), true)
    // 不额外修改组合图，仅保证最新配置
    comboChart.setOption(comboChart.getOption(), false)
    return
  }

  if (currentAction.value === 'drill') {
    // 数据钻取：高亮当前层级，并在控制台提示可点击扇区下钻
    const option = buildDonutOption(baseItems)
    option.title = {
      text: '当前层级（点击扇区继续下钻）',
      left: 'center',
      top: 6,
      textStyle: { color: '#e5e7eb', fontSize: 12 },
    }
    donutChart.setOption(option, true)
    console.info('[AnalyticsDashboard] 已进入“数据钻取”模式，点击环形图扇区即可查看子类目分布')
    return
  }

  if (currentAction.value === 'compare') {
    // 数据对比：按照占比从大到小排序，便于查看主力类目 VS 长尾类目
    const sorted = [...baseItems].sort((a, b) => b.value - a.value)
    const option = buildDonutOption(sorted)
    donutChart.setOption(option, true)
    console.info('[AnalyticsDashboard] 已按类目占比从大到小排序，便于横向对比')
    return
  }

  if (currentAction.value === 'anomaly') {
    // 异常检测：简单示意——高亮 Top1 类目，视为“异常波动点”
    if (!baseItems.length) return
    const topItem = [...baseItems].sort((a, b) => b.value - a.value)[0]
    const option = buildDonutOption(
      baseItems.map((it) => ({
        ...it,
        selected: it.name === topItem.name,
      })),
    )
    option.series[0].emphasis = {
      scale: true,
      scaleSize: 10,
    }
    donutChart.setOption(option, true)
    console.info('[AnalyticsDashboard] 已高亮占比最高的类目，作为“异常关注点”的示意')
    return
  }

  if (currentAction.value === 'filter') {
    // 筛选：过滤掉占比过低的类目，仅保留主力类目
    const threshold = 8
    const filtered = baseItems.filter((it) => it.value >= threshold)
    const option = buildDonutOption(filtered.length ? filtered : baseItems)
    donutChart.setOption(option, true)
    console.info(
      '[AnalyticsDashboard] 已过滤掉占比低于 ' + threshold + '% 的类目，仅保留主力类目进行观察',
    )
  }
}

// 将当前图表导出为图片（示意：新开窗口预览）
const exportCharts = () => {
  if (!donutChart && !comboChart) {
    console.warn('[AnalyticsDashboard] 当前没有可导出的图表实例')
    return
  }

  try {
    const donutUrl = donutChart?.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#020617',
    })
    const comboUrl = comboChart?.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#020617',
    })

    // 简单方式：在新窗口中展示两张图片，后续可接入真实下载逻辑
    const win = window.open('')
    if (win) {
      win.document.write('<title>图表导出预览</title>')
      if (donutUrl) {
        win.document.write('<h3>品类偏好分布</h3>')
        win.document.write(`<img src="${donutUrl}" style="max-width:100%;" />`)
      }
      if (comboUrl) {
        win.document.write('<h3>7 日行为趋势 & 转化漏斗</h3>')
        win.document.write(`<img src="${comboUrl}" style="max-width:100%;margin-top:12px;" />`)
      }
    }

    console.info('[AnalyticsDashboard] 图表导出完成（示意：已在新窗口中打开预览）')
  } catch (e) {
    console.error('[AnalyticsDashboard] 导出图表失败', e)
  }
}

// 控制栏按钮点击逻辑：切换 currentAction 并应用对应模式
const handleActionClick = (key) => {
  currentAction.value = key
  if (key === 'export') {
    exportCharts()
  } else {
    applyActionMode()
  }
}

const refreshData = () => {
  // 实际场景下可以将 dateRange 传回后端作为过滤条件
  loadData()
}

// 下钻逻辑：点击环形图扇区时，将当前层级推入栈，并切换为子类目视图
const handleDonutClick = (params) => {
  const clickedName = params.name
  // 记录当前层级以便“返回上一级”
  drillStack.value.push(categoryData.value)

  const subNames = mockSubCategoryMap[clickedName] || ['子类目 A', '子类目 B', '子类目 C']
  // 随机生成一个子类目分布，实际建议调用后端接口
  const subItems = subNames.map((name) => ({
    name,
    value: Math.round(Math.random() * 40 + 10),
  }))
  categoryData.value = subItems

  if (donutChart) {
    donutChart.setOption(buildDonutOption(subItems), true)
  }
}

// 返回上一级数据
const handleDrillBack = () => {
  const prev = drillStack.value.pop()
  if (!prev) return
  categoryData.value = prev
  if (donutChart) {
    donutChart.setOption(buildDonutOption(prev), true)
  }
}

// 初始化 ECharts 实例
const initCharts = () => {
  if (donutRef.value) {
    donutChart = echarts.init(donutRef.value)
    donutChart.on('click', handleDonutClick)
  }
  if (comboRef.value) {
    comboChart = echarts.init(comboRef.value)
  }
}

// 在窗口尺寸变化时自适应图表大小（添加简单防抖）
let resizeTimer = null
const handleResize = () => {
  if (resizeTimer) window.clearTimeout(resizeTimer)
  resizeTimer = window.setTimeout(() => {
    donutChart && donutChart.resize()
    comboChart && comboChart.resize()
  }, 150)
}

onMounted(() => {
  initCharts()
  loadData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (donutChart) {
    donutChart.dispose()
    donutChart = null
  }
  if (comboChart) {
    comboChart.dispose()
    comboChart = null
  }
})
</script>

<style scoped>
.dashboard-root {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.control-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border-radius: 999px;
}

.btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.btn-group.segmented {
  padding: 2px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow:
    0 8px 20px rgba(15, 23, 42, 0.04),
    0 0 0 1px rgba(229, 231, 235, 0.9);
}

.ctrl-btn {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.16s ease;
}

.ctrl-btn:hover {
  color: #c2410c;
  background: rgba(254, 243, 199, 0.6);
}

.ctrl-btn.active {
  background: linear-gradient(120deg, #fff7ed, #fffbeb);
  border-color: rgba(249, 115, 22, 0.9);
  color: #c2410c;
  box-shadow:
    0 0 0 1px rgba(254, 215, 170, 0.9),
    0 10px 24px rgba(249, 115, 22, 0.18);
}

.ctrl-label {
  position: relative;
  z-index: 1;
}

.right-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.date-label {
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #9ca3af;
}

.date-input {
  height: 28px;
  border-radius: 999px;
  border: none;
  background: rgba(248, 250, 252, 0.96);
  padding: 0 10px;
  color: #111827;
  font-size: 12px;
  min-width: 210px;
  box-shadow:
    0 0 0 1px rgba(229, 231, 235, 0.9),
    0 6px 14px rgba(15, 23, 42, 0.04);
}

.date-input::placeholder {
  color: #6b7280;
}

.refresh-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  border: none;
  background: linear-gradient(to right, #f97316, #fb923c);
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(248, 113, 22, 0.35);
}

.charts-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.2fr);
  gap: 12px;
  flex: 1;
  min-height: 320px;
}

.chart-card {
  padding: 10px;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.chart-title-block {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-header h3 {
  font-size: 14px;
  font-weight: 600;
}

.sub {
  font-size: 11px;
  color: #9ca3af;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
  box-shadow:
    0 0 0 0 rgba(34, 197, 94, 0.7),
    0 0 12px rgba(34, 197, 94, 0.9);
  animation: pulse 1.7s ease-out infinite;
}

.back-btn {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.8);
  background: transparent;
  color: #e5e7eb;
  font-size: 11px;
  cursor: pointer;
}

.chart-body {
  flex: 1;
  min-height: 260px;
}

@keyframes pulse {
  0% {
    box-shadow:
      0 0 0 0 rgba(34, 197, 94, 0.7),
      0 0 10px rgba(34, 197, 94, 0.9);
  }
  70% {
    box-shadow:
      0 0 0 12px rgba(34, 197, 94, 0),
      0 0 6px rgba(34, 197, 94, 0.6);
  }
  100% {
    box-shadow:
      0 0 0 0 rgba(34, 197, 94, 0),
      0 0 4px rgba(34, 197, 94, 0.4);
  }
}

@media (max-width: 1024px) {
  .charts-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>


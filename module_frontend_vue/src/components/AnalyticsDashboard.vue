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

    <!-- 可视化区域：视觉审美雷达 + 推荐来源环图 + 意图波峰趋势 -->
    <section class="charts-grid">
      <div class="chart-card glass-elevated">
        <header class="chart-header">
          <div class="chart-title-block">
            <div class="pulse-dot"></div>
            <div>
              <h3>视觉 DNA & 推荐来源构成</h3>
              <p class="sub">从图像向量中提取审美画像，并展示多模态推荐来源</p>
            </div>
          </div>
        </header>
        <div class="chart-body dual">
          <div class="sub-chart">
            <h4 class="mini-title">视觉审美雷达</h4>
            <p class="mini-sub">极简 / 技术感 / 商务 / 复古 / 机能</p>
            <div ref="radarRef" class="sub-chart-inner"></div>
          </div>
          <div class="sub-chart">
            <h4 class="mini-title">推荐来源占比</h4>
            <p class="mini-sub">文本搜索 / 图像浏览 / 历史交互</p>
            <div ref="contributionRef" class="sub-chart-inner"></div>
          </div>
        </div>
      </div>

      <div class="chart-card glass-elevated">
        <header class="chart-header">
          <div class="chart-title-block">
            <div class="pulse-dot"></div>
            <div>
              <h3>意图波峰 & 行为趋势</h3>
              <p class="sub">识别用户意图高峰，并结合活跃度、浏览与转化率进行洞察</p>
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
const radarRef = ref(null)
const contributionRef = ref(null)
const comboRef = ref(null)

// ECharts 实例
let radarChart = null
let contributionChart = null
let comboChart = null

// 画像与行为基础数据
const visualStyleVector = ref(null)
const contributionData = ref([])
const trendDays = ref([])
const trendActivity = ref([])
const trendViews = ref([])
const trendConversion = ref([])
const intentPeaks = ref([])

// 视觉审美雷达图 option
const buildVisualRadarOption = (vector) => {
  const dims = ['极简', '技术感', '商务', '复古', '机能']
  const safeVector = vector && typeof vector === 'object' ? vector : {}
  const values = dims.map((k) => Number(safeVector[k] ?? 0))

  return {
    backgroundColor: 'transparent',
    radar: {
      indicator: dims.map((name) => ({ name, max: 1 })),
      radius: '70%',
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.5)' } },
      splitLine: { lineStyle: { color: 'rgba(30, 64, 175, 0.55)' } },
      splitArea: {
        areaStyle: {
          color: [
            'rgba(15, 23, 42, 0.2)',
            'rgba(30, 64, 175, 0.12)',
            'rgba(59, 130, 246, 0.08)',
          ],
        },
      },
      name: {
        textStyle: {
          color: '#e5e7eb',
          fontSize: 11,
        },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: '视觉审美',
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                { offset: 0, color: 'rgba(249, 115, 22, 0.55)' },
                { offset: 1, color: 'rgba(139, 92, 246, 0.6)' },
              ]),
              opacity: 0.6,
            },
            lineStyle: {
              color: '#fb923c',
              width: 2,
            },
            itemStyle: {
              color: '#fed7aa',
              shadowBlur: 12,
              shadowColor: 'rgba(248, 250, 252, 0.4)',
            },
          },
        ],
        animationDuration: 800,
      },
    ],
  }
}

// 推荐来源贡献环形图 option
const buildContributionOption = (items) => {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>贡献占比：{d}%',
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
        name: '推荐来源',
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
        animationEasing: 'cubicOut',
        animationDuration: 800,
        data: items,
      },
    ],
  }
}

// 构造 7 日行为趋势 & 意图波峰组合图 option
const buildComboOption = (days, activity, views, conversion, peaks = []) => {
  const peakByIndex = {}
  const indexedPeaks = []
  peaks.forEach((p) => {
    const label = p.day || p.date
    if (!label) return
    const idx = days.indexOf(label)
    if (idx === -1) return
    peakByIndex[idx] = p
    indexedPeaks.push({ idx, peak: p })
  })

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
      formatter: (params) => {
        if (!params || !params.length) return ''
        const axisLabel = params[0].axisValue
        const peak = peaks.find((p) => (p.day || p.date) === axisLabel)
        const header = params
          .map(
            (p) =>
              `${p.marker} ${p.seriesName}：${
                p.seriesName.includes('转化率') ? `${p.data}%` : p.data
              }`,
          )
          .join('<br/>')
        if (!peak || !peak.summary) return `${axisLabel}<br/>${header}`
        return `${axisLabel}<br/>${header}<br/><span style="color:#f97316;">意图摘要：</span>${
          peak.summary
        }`
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
      data: ['活跃度评分', '浏览次数', '加购/点击转化率', '意图波峰'],
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
        markPoint: indexedPeaks.length
          ? {
              symbol: 'circle',
              symbolSize: 10,
              itemStyle: {
                color: '#f97316',
                shadowBlur: 16,
                shadowColor: 'rgba(248, 113, 22, 0.7)',
              },
              data: indexedPeaks.map(({ idx, peak }) => ({
                name: '意图波峰',
                xAxis: idx,
                yAxis: activity[idx] ?? 0,
                value: peak.summary || '意图波峰',
              })),
            }
          : undefined,
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
      // 占位图例系列，用于在图例中展示“意图波峰”含义
      indexedPeaks.length
        ? {
            name: '意图波峰',
            type: 'scatter',
            data: [],
          }
        : null,
    ].filter(Boolean),
  }
}

// 从后端加载用户画像与行为数据
const loadData = async () => {
  try {
    const { data } = await fetchUserProfile(props.userId)

    // 视觉审美向量（来自 ChromaDB 图像特征聚合 + DeepSeek 语义变换）
    // 期望结构：data.visual_style = { "极简": 0.78, "技术感": 0.92, ... }
    const visual = data.visual_style || data.visualStyle || null
    // 如果后端暂未提供，则回退为一个中性画像，避免图表空白
    visualStyleVector.value =
      visual && Object.keys(visual).length
        ? visual
        : {
            极简: 0.6,
            技术感: 0.7,
            商务: 0.5,
            复古: 0.4,
            机能: 0.65,
          }

    // 推荐来源贡献度结构预留
    // 期望结构：data.contribution = { text_search: 0.3, image_browse: 0.5, historical_interactions: 0.2 }
    const contribRaw = data.contribution || data.recommendation_contribution || null
    const contribution = contribRaw && Object.keys(contribRaw).length
      ? contribRaw
      : {
          text_search: 0.3,
          image_browse: 0.5,
          historical_interactions: 0.2,
        }

    const contribItems = [
      { name: '文本搜索', value: Number(((contribution.text_search ?? 0) * 100).toFixed(2)) },
      { name: '图像浏览记录', value: Number(((contribution.image_browse ?? 0) * 100).toFixed(2)) },
      {
        name: '历史交互',
        value: Number(((contribution.historical_interactions ?? 0) * 100).toFixed(2)),
      },
    ]
    contributionData.value = contribItems

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

    trendDays.value = days
    trendActivity.value = activity
    trendViews.value = views
    trendConversion.value = conversion

    // 意图波峰：来自后端 ChromaDB 偏移量 + DeepSeek 摘要（预留字段）
    // 期望结构：[{ day: '2026-03-03', peak_type: 'research', summary: '该时段用户正在深度调研 RTX 5060 相关配件', ... }]
    intentPeaks.value = Array.isArray(data.intent_peaks) ? data.intent_peaks : []

    // 初始化 / 刷新三个图表（基础模式）
    if (radarChart) {
      radarChart.setOption(buildVisualRadarOption(visualStyleVector.value))
    }
    if (contributionChart) {
      contributionChart.setOption(buildContributionOption(contributionData.value))
    }
    if (comboChart) {
      comboChart.setOption(
        buildComboOption(
          trendDays.value,
          trendActivity.value,
          trendViews.value,
          trendConversion.value,
          intentPeaks.value,
        ),
      )
    }

    applyActionMode()
  } catch (e) {
    console.error('加载用户画像数据失败', e)
  }
}

// 根据当前选中的分析模式，对图表做不同的可视化“增强效果”
const applyActionMode = () => {
  console.debug('[AnalyticsDashboard] 切换分析模式', currentAction.value)

  if (!radarChart || !contributionChart || !comboChart) return

  if (currentAction.value === 'basic') {
    // 基础图表：直接使用原始画像与贡献数据
    radarChart.setOption(buildVisualRadarOption(visualStyleVector.value), true)
    contributionChart.setOption(buildContributionOption(contributionData.value), true)
    comboChart.setOption(
      buildComboOption(
        trendDays.value,
        trendActivity.value,
        trendViews.value,
        trendConversion.value,
        intentPeaks.value,
      ),
      true,
    )
    return
  }

  if (currentAction.value === 'drill') {
    // 数据钻取：在当前阶段，将其理解为“主力推荐来源聚焦”
    const sorted = [...contributionData.value].sort((a, b) => b.value - a.value)
    const top = sorted[0]
    const enhanced = sorted.map((it) => ({
      ...it,
      selected: it.name === top.name,
    }))
    contributionChart.setOption(buildContributionOption(enhanced), true)
    console.info('[AnalyticsDashboard] 已进入“数据钻取”模式，已高亮主力推荐来源作为聚焦点')
    return
  }

  if (currentAction.value === 'compare') {
    // 数据对比：按照贡献从大到小排序，便于查看主力来源 VS 辅助来源
    const sorted = [...contributionData.value].sort((a, b) => b.value - a.value)
    const option = buildContributionOption(sorted)
    contributionChart.setOption(option, true)
    console.info('[AnalyticsDashboard] 已按推荐来源贡献从大到小排序，便于横向对比')
    return
  }

  if (currentAction.value === 'anomaly') {
    // 异常检测：简单示意——在趋势图中高亮存在意图波峰的日期
    comboChart.setOption(
      buildComboOption(
        trendDays.value,
        trendActivity.value,
        trendViews.value,
        trendConversion.value,
        intentPeaks.value,
      ),
      true,
    )
    console.info('[AnalyticsDashboard] 已高亮存在意图波峰的日期，作为“异常关注点”的示意')
    return
  }

  if (currentAction.value === 'filter') {
    // 筛选：过滤掉贡献过低的来源，仅保留主力来源
    const threshold = 8
    const filtered = contributionData.value.filter((it) => it.value >= threshold)
    const option = buildContributionOption(filtered.length ? filtered : contributionData.value)
    contributionChart.setOption(option, true)
    console.info(
      '[AnalyticsDashboard] 已过滤掉贡献低于 ' + threshold + '% 的推荐来源，仅保留主力来源进行观察',
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
    const contributionUrl = contributionChart?.getDataURL({
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
      if (contributionUrl) {
        win.document.write('<h3>推荐来源占比</h3>')
        win.document.write(`<img src="${contributionUrl}" style="max-width:100%;" />`)
      }
      if (comboUrl) {
        win.document.write('<h3>意图波峰 & 行为趋势</h3>')
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

// 初始化 ECharts 实例
const initCharts = () => {
  if (radarRef.value) {
    radarChart = echarts.init(radarRef.value)
  }
  if (contributionRef.value) {
    contributionChart = echarts.init(contributionRef.value)
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
    radarChart && radarChart.resize()
    contributionChart && contributionChart.resize()
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
  if (radarChart) {
    radarChart.dispose()
    radarChart = null
  }
  if (contributionChart) {
    contributionChart.dispose()
    contributionChart = null
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


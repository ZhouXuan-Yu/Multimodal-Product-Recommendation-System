<template>
  <div>
    <h3>用户画像分析</h3>
    <div ref="radarRef" class="chart"></div>
    <div ref="lineRef" class="chart"></div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const props = defineProps({ userId: String, baseUrl: String })
const radarRef = ref(null)
const lineRef = ref(null)

onMounted(async () => {
  const { data } = await axios.get(`${props.baseUrl}/api/user_profile/${props.userId}`)
  const pref = data.category_preferences || {}
  const categories = Object.keys(pref)
  const values = Object.values(pref).map((v) => Number(v) * 100)

  const radar = echarts.init(radarRef.value)
  radar.setOption({
    backgroundColor: 'transparent',
    radar: { indicator: categories.map((c) => ({ name: c, max: 100 })) },
    series: [{ type: 'radar', data: [{ value: values, name: '偏好' }] }],
  })

  const line = echarts.init(lineRef.value)
  line.setOption({
    backgroundColor: 'transparent',
    xAxis: { type: 'category', data: (data.recent_activity || []).map((_, i) => `${i + 1}`) },
    yAxis: { type: 'value' },
    series: [{ type: 'line', data: data.recent_activity || [], smooth: true }],
  })
})
</script>

<style scoped>
.chart { height: 260px; margin-top: 10px; border: 1px solid #1f2937; border-radius: 10px; }
</style>

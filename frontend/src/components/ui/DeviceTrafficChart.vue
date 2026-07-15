<template>
  <div class="device-traffic-chart">
    <div class="dtc-toolbar">
      <el-select v-model="selectedIf" size="small" filterable :placeholder="t('dtcSelectIface')" style="width: 280px" @change="loadTraffic">
        <el-option v-for="i in ifaceOptions" :key="i.if_index" :label="i.label" :value="i.if_index" />
      </el-select>
      <el-select v-model="limit" size="small" style="width: 120px" @change="loadTraffic">
        <el-option :value="30" :label="t('dtcLast30')" />
        <el-option :value="60" :label="t('dtcLast60')" />
        <el-option :value="120" :label="t('dtcLast120')" />
      </el-select>
      <el-button size="small" :icon="Refresh" :loading="loading" @click="loadTraffic">{{ t('dtcRefresh') }}</el-button>
      <span class="dtc-hint">{{ t('dtcHint') }}</span>
    </div>
    <div v-show="ifaceOptions.length" ref="chartRef" class="dtc-chart"></div>
    <el-empty v-if="!ifaceOptions.length && !loading" :description="t('dtcNoIface')" :image-size="60" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import axios from 'axios'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { useI18n } from '@/composables/useI18n'

const { t, currentLang } = useI18n()

const props = defineProps({
  deviceId: { type: [Number, String], required: true },
})

const chartRef = ref(null)
let chart = null
let resizeHandler = null

const ifaceOptions = ref([])
const selectedIf = ref(null)
const limit = ref(60)
const loading = ref(false)

const fmtBps = (v) => {
  v = v || 0
  if (v >= 1e9) return (v / 1e9).toFixed(2) + ' Gbps'
  if (v >= 1e6) return (v / 1e6).toFixed(2) + ' Mbps'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + ' Kbps'
  return v + ' bps'
}

const loadInterfaces = async () => {
  try {
    const res = await axios.get(`/api/devices/${props.deviceId}/interfaces`, { params: { monitored_only: true } })
    const items = res.data.items || []
    ifaceOptions.value = items.map(i => ({
      if_index: i.if_index,
      label: (i.if_name || `if${i.if_index}`) + (i.peer_device_name ? ` → ${i.peer_device_name}` : '') + (i.is_uplink ? ` [${t('dtcUplinkTag')}]` : ''),
      is_uplink: i.is_uplink,
    }))
    if (ifaceOptions.value.length) {
      const uplink = ifaceOptions.value.find(o => o.is_uplink)
      selectedIf.value = (uplink || ifaceOptions.value[0]).if_index
      await loadTraffic()
    }
  } catch (e) {
    ifaceOptions.value = []
  }
}

const loadTraffic = async () => {
  if (selectedIf.value == null) return
  loading.value = true
  try {
    const res = await axios.get(`/api/devices/${props.deviceId}/interfaces/${selectedIf.value}/traffic`, { params: { limit: limit.value } })
    const samples = res.data.samples || []
    renderChart(samples)
  } catch (e) {
    renderChart([])
  } finally {
    loading.value = false
  }
}

const renderChart = (samples) => {
  nextTick(() => {
    if (!chartRef.value) return
    if (!chart) chart = echarts.init(chartRef.value)
    const isDark = document.documentElement.classList.contains('dark')
    const textColor = isDark ? '#cbd5e1' : '#475569'
    const times = samples.map(s => (s.ts ? new Date(s.ts).toLocaleTimeString(currentLang.value === 'en' ? 'en-US' : 'zh-CN', { hour12: false }) : ''))
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', valueFormatter: (v) => fmtBps(v) },
      legend: { data: [t('dtcInbound'), t('dtcOutbound')], textStyle: { color: textColor }, top: 0 },
      grid: { left: 60, right: 20, top: 36, bottom: 30 },
      xAxis: { type: 'category', data: times, axisLabel: { color: textColor } },
      yAxis: { type: 'value', axisLabel: { color: textColor, formatter: (v) => fmtBps(v) } },
      series: [
        { name: t('dtcInbound'), type: 'line', smooth: true, showSymbol: false, areaStyle: { opacity: 0.12 }, itemStyle: { color: '#409eff' }, data: samples.map(s => s.in_bps || 0) },
        { name: t('dtcOutbound'), type: 'line', smooth: true, showSymbol: false, areaStyle: { opacity: 0.12 }, itemStyle: { color: '#67c23a' }, data: samples.map(s => s.out_bps || 0) },
      ],
    }, true)
  })
}

onMounted(() => {
  loadInterfaces()
  resizeHandler = () => chart && chart.resize()
  window.addEventListener('resize', resizeHandler)
})

watch(currentLang, () => { if (selectedIf.value != null) loadTraffic() })

onBeforeUnmount(() => {
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (chart) { chart.dispose(); chart = null }
})
</script>

<style scoped>
.device-traffic-chart { display: flex; flex-direction: column; gap: 10px; }
.dtc-toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.dtc-hint { font-size: 12px; color: #909399; margin-left: auto; }
.dtc-chart { width: 100%; height: 420px; }
</style>

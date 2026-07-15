<template>
  <div class="net-overview">
    <div class="no-stats">
      <div class="no-stat">
        <span class="no-num up">{{ data.iface_up ?? '—' }}</span>
        <span class="no-label">{{ t('noIfaceUp') }}</span>
      </div>
      <div class="no-stat">
        <span class="no-num down">{{ data.iface_down ?? '—' }}</span>
        <span class="no-label">{{ t('noIfaceDown') }}</span>
      </div>
      <div class="no-stat">
        <span class="no-num">{{ fmtBps(data.total_in_bps) }}</span>
        <span class="no-label">{{ t('noTotalIn') }}</span>
      </div>
      <div class="no-stat">
        <span class="no-num">{{ fmtBps(data.total_out_bps) }}</span>
        <span class="no-label">{{ t('noTotalOut') }}</span>
      </div>
    </div>

    <div class="no-top">
      <div class="no-top-title">{{ t('noTopTitle') }}</div>
      <div v-if="(data.top || []).length" class="no-top-list">
        <div v-for="item in data.top" :key="item.device_id + '-' + item.if_name" class="no-top-row">
          <div class="no-top-name">
            <span class="ntn-dev">{{ item.device_name }}</span>
            <span class="ntn-if">{{ item.if_name }}</span>
          </div>
          <div class="no-top-bar-wrap">
            <div class="no-top-bar" :style="{ width: barWidth(item) + '%', background: barColor(item.util) }"></div>
          </div>
          <div class="no-top-val">↓{{ fmtBps(item.in_bps) }} ↑{{ fmtBps(item.out_bps) }}</div>
        </div>
      </div>
      <div v-else class="no-top-empty">{{ t('noTopEmpty') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const data = ref({})
let timer = null

const fmtBps = (v) => {
  v = v || 0
  if (v >= 1e9) return (v / 1e9).toFixed(2) + ' Gbps'
  if (v >= 1e6) return (v / 1e6).toFixed(2) + ' Mbps'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + ' Kbps'
  return v + ' bps'
}

const maxBps = () => {
  const list = data.value.top || []
  return list.reduce((m, i) => Math.max(m, (i.in_bps || 0) + (i.out_bps || 0)), 1)
}
const barWidth = (item) => Math.max(3, Math.round(((item.in_bps || 0) + (item.out_bps || 0)) / maxBps() * 100))
const barColor = (util) => {
  util = util || 0
  if (util >= 80) return '#f97316'
  if (util >= 60) return '#facc15'
  return '#22d3ee'
}

const load = async () => {
  try {
    const res = await axios.get('/api/dashboard/network-overview')
    data.value = res.data || {}
  } catch (e) {
    data.value = {}
  }
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 30000)
})
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>

<style scoped>
.net-overview { display: flex; flex-direction: column; gap: 14px; padding: 4px; }
.no-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.no-stat { display: flex; flex-direction: column; padding: 8px 10px; background: var(--bg-secondary); border-radius: var(--radius-md, 8px); border: 1px solid var(--border-default); }
.no-num { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.no-num.up { color: #22c55e; }
.no-num.down { color: #ef4444; }
.no-label { font-size: 12px; color: var(--text-muted); }

.no-top-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.no-top-list { display: flex; flex-direction: column; gap: 6px; }
.no-top-row { display: grid; grid-template-columns: 180px 1fr 190px; align-items: center; gap: 10px; }
.no-top-name { display: flex; flex-direction: column; overflow: hidden; }
.ntn-dev { font-size: 12px; color: var(--text-primary); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ntn-if { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.no-top-bar-wrap { height: 10px; background: var(--bg-tertiary, #eef2f7); border-radius: 5px; overflow: hidden; }
.no-top-bar { height: 100%; border-radius: 5px; transition: width 0.4s; }
.no-top-val { font-size: 12px; color: var(--text-secondary); text-align: right; white-space: nowrap; }
.no-top-empty { font-size: 12px; color: var(--text-muted); padding: 12px 0; }
</style>

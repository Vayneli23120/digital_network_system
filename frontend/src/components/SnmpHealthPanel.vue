<!-- Monitor3D SNMP 采集健康（item 946 切片 7）
从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
纯展示组件：pos/collapsed/dark/summary/items/now 为 prop，start-drag/toggle/refresh 转发给父
（父持有拖拽/展开状态 useOverlayPanels 并执行 startDrag/toggleSnmpHealth/refreshTrafficHeatLayer）。
5 个格式化函数迁入组件内（依赖 t）。 -->
<template>
  <div class="snmp-health-panel" :class="{ collapsed, dark }"
       :style="{ left: pos.x + 'px', bottom: pos.y + 'px' }">
    <div class="snmp-health-head" @mousedown="e => emit('start-drag', e)">
      <el-icon class="drag-handle"><Rank /></el-icon>
      <span class="snmp-health-title">{{ t('monitorSnmpHealth') }}</span>
      <span class="snmp-health-summary">
        {{ summary.fresh || 0 }}/{{ summary.total || 0 }} {{ t('snmpStatusFresh') }}
      </span>
      <el-icon class="snmp-health-toggle" @click.stop="emit('toggle')"><ArrowDown v-if="!collapsed" /><ArrowUp v-else /></el-icon>
    </div>
    <div v-show="!collapsed" class="snmp-health-body">
      <div class="snmp-health-kpis">
        <span class="fresh">{{ t('snmpStatusFresh') }} {{ summary.fresh || 0 }}</span>
        <span class="lagging">{{ t('snmpStatusLagging') }} {{ summary.lagging || 0 }}</span>
        <span class="stale">{{ t('snmpStatusStale') }} {{ summary.stale || 0 }}</span>
        <span class="missing">{{ t('snmpStatusMissing') }} {{ summary.missing || 0 }}</span>
      </div>
      <div v-if="items.length" class="snmp-health-list">
        <div
          v-for="item in items.slice(0, 6)"
          :key="`${item.device_id}-${item.if_index}`"
          class="snmp-health-row"
          :class="item.status"
        >
          <div class="snmp-health-main">
            <span class="snmp-health-device">{{ item.device_name }}</span>
            <span class="snmp-health-if">{{ item.if_name || ('ifIndex ' + item.if_index) }}</span>
          </div>
          <div class="snmp-health-meta">
            <span>{{ snmpHealthStatusLabel(item.status) }}</span>
            <span>{{ t('monitorCheck') }} {{ formatSnmpAge(item.check_age_seconds ?? item.age_seconds) }}</span>
            <span>{{ t('monitorTraffic') }} {{ formatSnmpAge(item.sample_age_seconds) }}</span>
            <span>{{ t('monitorCollect') }} {{ collectorStatusLabel(item.collector_status) }}</span>
            <span v-if="item.collector_duration_ms != null">{{ formatDurationMs(item.collector_duration_ms) }}</span>
            <span v-if="item.collector_next_poll_in_seconds != null">{{ t('monitorNextPoll') }} {{ formatSnmpAge(item.collector_next_poll_in_seconds) }}</span>
          </div>
        </div>
      </div>
      <div v-else class="snmp-health-empty">{{ t('monitorSnmpEmpty') }}</div>
      <div class="snmp-health-server-time">{{ t('monitorServerTime') }} {{ formatSnmpServerTime(now) }}</div>
      <button class="snmp-health-refresh" @click.stop="emit('refresh')">{{ t('monitorRefreshStatus') }}</button>
    </div>
  </div>
</template>

<script setup>
import { Rank, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'

defineProps({
  pos: { type: Object, required: true },
  collapsed: { type: Boolean, default: false },
  dark: { type: Boolean, default: false },
  summary: { type: Object, default: () => ({}) },
  items: { type: Array, default: () => [] },
  now: { type: [String, Number, Date], default: null }
})

const emit = defineEmits(['start-drag', 'toggle', 'refresh'])

const { t } = useI18n()

function snmpHealthStatusLabel(status) {
  return {
    fresh: t('snmpStatusFresh'),
    lagging: t('snmpStatusLagging'),
    stale: t('snmpStatusStale'),
    missing: t('snmpStatusMissing'),
    down: t('snmpStatusDown'),
  }[status] || t('snmpStatusUnknown')
}

function collectorStatusLabel(status) {
  return {
    running: t('collectorRunning'),
    ok: t('collectorOk'),
    partial: t('collectorPartial'),
    timeout: t('collectorTimeout'),
    failed: t('collectorFailed'),
    cancelled: t('collectorCancelled'),
    stuck: t('collectorStuck'),
    no_response: t('collectorNoResponse'),
    no_interfaces: t('collectorNoInterfaces'),
  }[status] || '-'
}

function formatSnmpAge(seconds) {
  if (seconds == null) return '-'
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}min`
  return `${Math.floor(minutes / 60)}h${minutes % 60}m`
}

function formatDurationMs(ms) {
  if (ms == null) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatSnmpServerTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
/* SNMP 采集健康面板（从 Monitor3D.vue 逐字拷贝） */
.snmp-health-panel {
  position: absolute;
  z-index: 6;
  width: 260px;
  background: rgba(15, 23, 42, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 12px;
  backdrop-filter: blur(4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}
.snmp-health-panel.collapsed {
  width: 260px;
}
.snmp-health-head {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 4px;
  padding: 7px 10px;
  cursor: grab;
  user-select: none;
}
.snmp-health-head:active {
  cursor: grabbing;
}
.snmp-health-title {
  font-weight: 600;
  color: #93c5fd;
}
.snmp-health-summary {
  color: #cbd5e1;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.snmp-health-toggle {
  font-size: 13px;
  opacity: 0.8;
}

/* 拖拽手柄图标（从 Monitor3D.vue 逐字拷贝，两面板共用规则各自拷贝半边） */
.drag-handle {
  font-size: 13px;
  opacity: 0.4;
  transition: opacity 0.2s;
  flex-shrink: 0;
  line-height: 1;
}
.drag-handle:hover {
  opacity: 0.8;
}
.snmp-health-head:hover .drag-handle {
  opacity: 0.7;
}
.snmp-health-body {
  padding: 4px 10px 10px;
}
.snmp-health-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  margin-bottom: 8px;
}
.snmp-health-kpis span {
  border-radius: 4px;
  padding: 3px 4px;
  text-align: center;
  font-size: 10px;
  background: rgba(30, 41, 59, 0.72);
  white-space: nowrap;
}
.snmp-health-kpis .fresh { color: #86efac; }
.snmp-health-kpis .lagging { color: #fde68a; }
.snmp-health-kpis .stale { color: #fdba74; }
.snmp-health-kpis .missing { color: #c4b5fd; }
.snmp-health-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 176px;
  overflow: auto;
}
.snmp-health-row {
  border-left: 3px solid #64748b;
  background: rgba(30, 41, 59, 0.62);
  border-radius: 5px;
  padding: 5px 6px;
}
.snmp-health-row.fresh { border-left-color: #22c55e; }
.snmp-health-row.lagging { border-left-color: #facc15; }
.snmp-health-row.stale { border-left-color: #f97316; }
.snmp-health-row.missing { border-left-color: #8b5cf6; }
.snmp-health-row.down { border-left-color: #ef4444; }
.snmp-health-main,
.snmp-health-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.snmp-health-device {
  max-width: 132px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #e2e8f0;
}
.snmp-health-if,
.snmp-health-meta {
  color: #94a3b8;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}
.snmp-health-empty {
  color: #94a3b8;
  font-size: 11px;
  padding: 8px 0;
  text-align: center;
}
.snmp-health-server-time {
  margin-top: 8px;
  color: #94a3b8;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  text-align: center;
}
.snmp-health-refresh {
  width: 100%;
  margin-top: 8px;
  border: 1px solid rgba(147, 197, 253, 0.28);
  border-radius: 5px;
  background: rgba(30, 41, 59, 0.76);
  color: #bfdbfe;
  font-size: 11px;
  padding: 5px 8px;
  cursor: pointer;
}
.snmp-health-refresh:hover {
  background: rgba(37, 99, 235, 0.24);
}
</style>

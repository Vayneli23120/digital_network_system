<!-- Monitor3D 流量热力图例（item 946 切片 7）
从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
纯展示组件：pos/collapsed/dark/summary 为 prop，start-drag/toggle 转发给父
（父持有拖拽/展开状态 useOverlayPanels 并执行 startDrag/toggleHeatLegend）。
heatLegendLevels 由组件内 computed 生成（依赖 t）。 -->
<template>
  <div class="heat-legend" :class="{ collapsed, dark }"
       :style="{ left: pos.x + 'px', bottom: pos.y + 'px' }">
    <div class="heat-legend-head" @mousedown="e => emit('start-drag', e)">
      <el-icon class="drag-handle"><Rank /></el-icon>
      <span class="heat-legend-title">{{ t('heatLegendTitle') }}</span>
      <el-icon class="heat-legend-toggle" @click.stop="emit('toggle')"><ArrowDown v-if="!collapsed" /><ArrowUp v-else /></el-icon>
    </div>
    <div v-show="!collapsed" class="heat-legend-body">
      <div class="heat-legend-row" v-for="lv in heatLegendLevels" :key="lv.level">
        <span class="heat-swatch" :style="{ background: lv.color }"></span>
        <span class="heat-name">{{ lv.label }}</span>
        <span class="heat-range">{{ lv.range }}</span>
        <span class="heat-count">{{ summary[lv.level] || 0 }}</span>
      </div>
      <div class="heat-legend-foot">{{ t('heatLegendHint') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Rank, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  pos: { type: Object, required: true },
  collapsed: { type: Boolean, default: false },
  dark: { type: Boolean, default: false },
  summary: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['start-drag', 'toggle'])

const { t } = useI18n()

const heatLegendLevels = computed(() => [
  { level: 'critical', color: '#f97316', label: t('heatLevelCritical'), range: '≥80%' },
  { level: 'high', color: '#facc15', label: t('heatLevelHigh'), range: '60-80%' },
  { level: 'normal', color: '#22d3ee', label: t('heatLevelNormal'), range: '20-60%' },
  { level: 'low', color: '#22c55e', label: t('heatLevelLow'), range: '<20%' },
  { level: 'down', color: '#ef4444', label: t('heatLevelDown'), range: 'link down' },
  { level: 'stale', color: '#64748b', label: t('heatLevelStale'), range: '>10min' },
])
</script>

<style scoped>
/* 流量热力图例（从 Monitor3D.vue 逐字拷贝） */
.heat-legend {
  position: absolute;
  z-index: 6;
  width: 188px;
  background: rgba(15, 23, 42, 0.82);
  border: 1px solid rgba(34, 211, 238, 0.25);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 12px;
  backdrop-filter: blur(4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}
.heat-legend.collapsed {
  width: 188px;
}
.heat-legend-head {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 10px;
  cursor: grab;
  user-select: none;
}
.heat-legend-head:active {
  cursor: grabbing;
}
.heat-legend-title {
  font-weight: 600;
  color: #22d3ee;
  letter-spacing: 0.5px;
}
.heat-legend-toggle {
  font-size: 13px;
  opacity: 0.8;
}
.heat-legend-body {
  padding: 4px 10px 8px;
}
.heat-legend-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.heat-swatch {
  width: 14px;
  height: 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.heat-name {
  width: 64px;
  flex-shrink: 0;
}
.heat-range {
  flex: 1;
  color: #94a3b8;
  font-size: 11px;
}
.heat-count {
  min-width: 18px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: #e2e8f0;
}
.heat-legend-foot {
  margin-top: 6px;
  font-size: 10px;
  line-height: 1.4;
  color: #64748b;
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
.heat-legend-head:hover .drag-handle {
  opacity: 0.7;
}
</style>

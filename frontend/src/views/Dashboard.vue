<template>
  <div class="dashboard">
    <div class="dashboard-shell">
      <!-- 工具栏 -->
      <div class="dash-toolbar">
        <span class="dash-title">{{ t('navDashboard') }}</span>
        <div class="dash-actions">
          <el-button v-if="editMode" size="small" @click="paletteOpen = true">＋ {{ t('dashAddWidget') || '添加模块' }}</el-button>
          <el-button v-if="editMode" size="small" @click="resetLayout">{{ t('dashResetLayout') || '重置布局' }}</el-button>
          <el-button size="small" :type="editMode ? 'warning' : 'primary'" @click="toggleEdit">
            {{ editMode ? (t('dashDone') || '完成') : (t('dashCustomize') || '自定义') }}
          </el-button>
        </div>
      </div>

      <!-- 模块网格 -->
      <div class="widget-grid" :class="{ editing: editMode }">
        <div
          v-for="(wg, idx) in widgets"
          :key="wg.id"
          class="widget"
          :class="[`span-${wg.w}`, `h-${wg.h}`, { dragging: dragIndex === idx, over: overIndex === idx }]"
          :draggable="editMode"
          @dragstart="onDragStart(idx)"
          @dragover.prevent="onDragOver(idx)"
          @drop="onDrop(idx)"
          @dragend="onDragEnd"
        >
          <!-- 编辑控制条（仅编辑模式显示，视图模式外观不变） -->
          <div class="widget-toolbar" v-if="editMode">
            <span class="wt-name"><el-icon><Rank /></el-icon>{{ widgetTitle(wg.type) }}</span>
            <div class="wt-controls">
              <button v-for="n in 4" :key="n" class="wt-btn" :class="{ active: wg.w === n }" @click="setWidth(wg, n)">{{ n }}</button>
              <button class="wt-btn" @click="cycleHeight(wg)" :title="'高度 ' + wg.h">↕</button>
              <button class="wt-btn danger" @click="removeWidget(wg.id)" title="移除">×</button>
            </div>
          </div>

          <div class="widget-body">
            <!-- 实时状态条 -->
            <div v-if="wg.type === 'realtime'" class="realtime-strip" :class="realtime && realtime.overall_status" v-loading="!realtime">
              <div class="rt-headline">
                <span class="rt-dot" :class="realtime && realtime.overall_status"></span>
                <span class="rt-title">{{ t('rtTitle') }}</span>
              </div>
              <div class="rt-metrics" v-if="realtime">
                <div class="rt-item">
                  <span class="rt-num">{{ realtime.online }}/{{ realtime.total }}</span>
                  <span class="rt-label">{{ t('rtOnline') }}</span>
                </div>
                <div class="rt-item" :class="{ danger: realtime.offline > 0 }">
                  <span class="rt-num">{{ realtime.offline }}</span>
                  <span class="rt-label">{{ t('rtOffline') }}</span>
                </div>
                <div class="rt-item">
                  <span class="rt-num">{{ realtime.online_pct }}%</span>
                  <span class="rt-label">{{ t('rtOnlineRate') }}</span>
                </div>
                <div class="rt-item" :class="{ warning: realtime.active_faults > 0, danger: realtime.active_critical > 0 }">
                  <span class="rt-num">{{ realtime.active_faults }}</span>
                  <span class="rt-label">
                    {{ t('rtActiveFaults') }}<span v-if="realtime.active_critical > 0">（{{ realtime.active_critical }} 严重）</span>
                  </span>
                </div>
              </div>
              <router-link class="rt-link" to="/monitor-3d">{{ t('rtLiveScreen') }} →</router-link>
            </div>

            <!-- 各厂区/区域状态 -->
            <div v-else-if="wg.type === 'sites'" class="site-breakdown">
              <div class="site-title">{{ t('rtSiteTitle') }}</div>
              <div class="site-grid" v-if="realtime && realtime.sites && realtime.sites.length">
                <div v-for="s in realtime.sites" :key="s.site" class="site-card" :class="s.status">
                  <div class="site-head">
                    <span class="site-dot" :class="s.status"></span>
                    <span class="site-name">{{ s.site }}</span>
                  </div>
                  <div class="site-avail">{{ s.availability_pct }}%</div>
                  <div class="site-meta">
                    {{ s.online }}/{{ s.total }} 在线<span v-if="s.offline > 0" class="off"> · {{ s.offline }} 离线</span><span v-if="s.active_faults > 0" class="flt"> · {{ s.active_faults }} 故障</span>
                  </div>
                </div>
              </div>
              <div v-else class="widget-empty">暂无区域数据</div>
            </div>

            <!-- 态势摘要条 -->
            <div v-else-if="wg.type === 'summary'" class="summary-bar" :class="summaryBarClass" v-loading="!executiveSummary">
              <div class="summary-icon"><el-icon><DataBoard /></el-icon></div>
              <span class="summary-text">{{ executiveSummary && executiveSummary.summary_text }}</span>
              <span class="summary-range">{{ executiveSummary && executiveSummary.range }}</span>
            </div>

            <!-- KPI 概览 -->
            <div v-else-if="wg.type === 'kpis'" class="executive-kpi-grid" v-loading="!executiveSummary">
              <template v-if="executiveSummary">
                <KpiStat v-if="executiveSummary.kpis?.availability" :kpi="executiveSummary.kpis.availability" :title="t('kpiAvailability')" link="/devices" />
                <KpiStat v-if="executiveSummary.kpis?.active_faults" :kpi="executiveSummary.kpis.active_faults" :title="t('kpiActiveFaults')" link="/faults?status=open" />
                <KpiStat v-if="executiveSummary.kpis?.sla_rate" :kpi="executiveSummary.kpis.sla_rate" :title="t('kpiSlaRate')" link="/maintenance" />
                <KpiStat v-if="executiveSummary.kpis?.mttr_hours" :kpi="executiveSummary.kpis.mttr_hours" :title="t('kpiMttr')" />
                <KpiStat v-if="executiveSummary.kpis?.month_cost" :kpi="executiveSummary.kpis.month_cost" :title="t('kpiMonthCost')" />
                <KpiStat v-if="executiveSummary.kpis?.budget_variance" :kpi="executiveSummary.kpis.budget_variance" :title="t('kpiBudgetVariance')" />
                <KpiStat v-if="executiveSummary.kpis?.recurring_rate" :kpi="executiveSummary.kpis.recurring_rate" :title="t('kpiRecurringRate')" link="/faults" />
                <KpiStat v-if="executiveSummary.kpis?.spare_low_stock" :kpi="executiveSummary.kpis.spare_low_stock" :title="t('kpiSpareLowStock')" link="/spare-parts?low_stock=true" />
                <KpiStat v-if="executiveSummary.kpis?.spare_days_cover" :kpi="executiveSummary.kpis.spare_days_cover" :title="t('kpiDaysCover')" link="/spare-parts" :show-trend-value="true" />
                <KpiStat v-if="executiveSummary.kpis?.mtbf_days" :kpi="executiveSummary.kpis.mtbf_days" :title="t('kpiMtbf')" />
              </template>
            </div>

            <!-- MTTR 四段拆解 -->
            <MttrFunnel v-else-if="wg.type === 'mttr' && executiveSummary?.mttr_breakdown" :breakdown="executiveSummary.mttr_breakdown" :title="t('mttrBreakdownTitle')" />

            <!-- 根因帕累托 -->
            <ParetoChart v-else-if="wg.type === 'pareto' && executiveSummary?.root_cause_pareto?.length" :data="executiveSummary.root_cause_pareto" :title="t('paretoChartTitle')" />

            <!-- SLO 错误预算 -->
            <ErrorBudget v-else-if="wg.type === 'slo' && executiveSummary?.slo?.length" :data="executiveSummary.slo" :title="t('sloErrorBudgetTitle')" />

            <!-- 变更-故障关联 -->
            <ChangeCorrelation v-else-if="wg.type === 'change' && executiveSummary?.change_fault_correlation" :data="executiveSummary.change_fault_correlation" :title="t('changeCorrelationTitle')" />

            <!-- Grafana 网络总览（实时指标） -->
            <div v-else-if="wg.type === 'grafana'" class="grafana-widget">
              <iframe v-if="grafanaOverviewUrl" :src="grafanaOverviewUrl" frameborder="0" class="grafana-frame"></iframe>
              <div v-else class="widget-empty">未配置 Grafana 地址（系统设置 → Grafana 地址）</div>
            </div>

            <!-- 数据未就绪占位 -->
            <div v-else class="widget-empty">暂无数据</div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <footer class="dashboard-footer">
        <span class="footer-version">{{ t('dashVersion') }} v2.0.0</span>
        <span class="footer-sync">{{ t('dashLastSync') }}: {{ currentTime }}</span>
      </footer>
    </div>

    <!-- 添加模块面板 -->
    <el-dialog v-model="paletteOpen" :title="t('dashAddWidget') || '添加模块'" width="460px">
      <div class="palette-grid" v-if="availableToAdd.length">
        <div v-for="opt in availableToAdd" :key="opt.type" class="palette-item" @click="addWidget(opt.type)">
          <span class="pi-name">{{ opt.title }}</span>
          <span class="pi-add">＋</span>
        </div>
      </div>
      <div v-else class="palette-empty">所有模块都已在仪表板上</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { DataBoard, Rank } from '@element-plus/icons-vue'
import { getExecutiveSummary, getRealtimeStatus } from '@/api'
import axios from 'axios'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import KpiStat from '@/components/ui/KpiStat.vue'
import MttrFunnel from '@/components/ui/MttrFunnel.vue'
import ParetoChart from '@/components/ui/ParetoChart.vue'
import ErrorBudget from '@/components/ui/ErrorBudget.vue'
import ChangeCorrelation from '@/components/ui/ChangeCorrelation.vue'

const { t } = useI18n()
const executiveSummary = ref(null)
const realtime = ref(null)
const currentTime = ref(dayjs().format('HH:mm:ss'))
let timerId = null
let realtimeTimerId = null

const summaryBarClass = computed(() => {
  const summary = executiveSummary.value?.summary_text
  if (!summary) return 'stable'
  if (summary.includes('风险') || summary.includes('Risk')) return 'risk'
  if (summary.includes('平稳') || summary.includes('Stable')) return 'stable'
  return 'warning'
})

const loadExecutive = async (force = false) => {
  try {
    const execData = await cachedRequest(
      () => getExecutiveSummary('30d'),
      'executiveSummary',
      {},
      { forceRefresh: force }
    )
    executiveSummary.value = execData
  } catch (err) {
    console.error('Failed to load executive summary:', err)
  }
}

const loadRealtime = async () => {
  try {
    realtime.value = await getRealtimeStatus()
  } catch (err) {
    console.error('Failed to load realtime status:', err)
  }
}

onMounted(() => {
  loadExecutive()
  loadRealtime()
  loadGrafanaConfig()
  realtimeTimerId = window.setInterval(loadRealtime, 30000)
  timerId = window.setInterval(() => { currentTime.value = dayjs().format('HH:mm:ss') }, 1000)
})

onUnmounted(() => {
  if (timerId) window.clearInterval(timerId)
  if (realtimeTimerId) window.clearInterval(realtimeTimerId)
})

// ===== Grafana 网络总览嵌入 =====
const grafanaBaseUrl = ref('')
const loadGrafanaConfig = async () => {
  try {
    const res = await axios.get('/api/system/config')
    const item = (res.data.items || []).find(i => i.key === 'grafana_url')
    grafanaBaseUrl.value = (item && item.value) || ''
  } catch {
    grafanaBaseUrl.value = ''
  }
}
const grafanaOverviewUrl = computed(() => {
  if (!grafanaBaseUrl.value) return ''
  // 使用后端反向代理 /grafana/* → http://localhost:3001/*，避免混合内容拦截
  return `/grafana/d/network-overview/network-overview?kiosk&theme=light&refresh=30s`
})

// ===== 模块化仪表板（P1：拖拽/缩放/增删 + localStorage 持久化）=====
const LAYOUT_KEY = 'dashboard_layout_v1'

// 可用模块定义（类型 + 默认尺寸 w=列跨(1-4) h=高度档(1-3)）
const WIDGET_DEFS = {
  realtime: { title: '实时状态条', w: 4, h: 1 },
  sites: { title: '各厂区状态', w: 4, h: 1 },
  summary: { title: '态势摘要', w: 4, h: 1 },
  kpis: { title: 'KPI 概览', w: 4, h: 2 },
  mttr: { title: 'MTTR 拆解', w: 2, h: 2 },
  pareto: { title: '根因帕累托', w: 2, h: 2 },
  slo: { title: 'SLO 错误预算', w: 4, h: 2 },
  change: { title: '变更-故障关联', w: 4, h: 1 },
  grafana: { title: 'Grafana 网络总览', w: 4, h: 3 },
}

const DEFAULT_WIDGETS = [
  { type: 'realtime', w: 4, h: 1 },
  { type: 'sites', w: 4, h: 1 },
  { type: 'summary', w: 4, h: 1 },
  { type: 'kpis', w: 4, h: 2 },
  { type: 'mttr', w: 2, h: 2 },
  { type: 'pareto', w: 2, h: 2 },
  { type: 'slo', w: 4, h: 2 },
  { type: 'change', w: 4, h: 1 },
]

const editMode = ref(false)
const paletteOpen = ref(false)
const widgets = ref([])
const dragIndex = ref(null)
const overIndex = ref(null)
let widgetSeq = 0

const widgetTitle = (type) => WIDGET_DEFS[type]?.title || type

const availableToAdd = computed(() => {
  const present = new Set(widgets.value.map(w => w.type))
  return Object.keys(WIDGET_DEFS)
    .filter(type => !present.has(type))
    .map(type => ({ type, title: WIDGET_DEFS[type].title }))
})

const loadLayout = () => {
  let saved = null
  try {
    saved = JSON.parse(localStorage.getItem(LAYOUT_KEY) || 'null')
  } catch { saved = null }
  const source = Array.isArray(saved) && saved.length ? saved : DEFAULT_WIDGETS
  widgets.value = source
    .filter(w => WIDGET_DEFS[w.type])
    .map(w => ({
      id: `${w.type}-${++widgetSeq}`,
      type: w.type,
      w: Math.min(4, Math.max(1, w.w || WIDGET_DEFS[w.type].w)),
      h: Math.min(3, Math.max(1, w.h || WIDGET_DEFS[w.type].h)),
    }))
}

const saveLayout = () => {
  const data = widgets.value.map(w => ({ type: w.type, w: w.w, h: w.h }))
  try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(data)) } catch { /* ignore */ }
}

const toggleEdit = () => {
  editMode.value = !editMode.value
  if (!editMode.value) saveLayout()
}

const resetLayout = () => {
  localStorage.removeItem(LAYOUT_KEY)
  loadLayout()
}

const setWidth = (wg, n) => { wg.w = n; saveLayout() }
const cycleHeight = (wg) => { wg.h = (wg.h % 3) + 1; saveLayout() }
const removeWidget = (id) => {
  widgets.value = widgets.value.filter(w => w.id !== id)
  saveLayout()
}
const addWidget = (type) => {
  if (!WIDGET_DEFS[type] || widgets.value.some(w => w.type === type)) return
  widgets.value.push({ id: `${type}-${++widgetSeq}`, type, w: WIDGET_DEFS[type].w, h: WIDGET_DEFS[type].h })
  paletteOpen.value = false
  saveLayout()
}

// 拖拽重排
const onDragStart = (idx) => { dragIndex.value = idx }
const onDragOver = (idx) => { overIndex.value = idx }
const onDrop = (idx) => {
  const from = dragIndex.value
  if (from === null || from === idx) return
  const arr = widgets.value.slice()
  const [moved] = arr.splice(from, 1)
  arr.splice(idx, 0, moved)
  widgets.value = arr
  saveLayout()
}
const onDragEnd = () => { dragIndex.value = null; overIndex.value = null }

loadLayout()
</script>

<style scoped>
.dashboard {
  background:
    radial-gradient(circle at top left, rgba(9, 132, 227, 0.08), transparent 28%),
    radial-gradient(circle at top right, rgba(0, 184, 148, 0.08), transparent 24%),
    linear-gradient(180deg, #f0f4fa 0%, #f7f9fc 48%, #f0f4fa 100%);
  color: var(--text-primary);
  font-family: var(--font-body);
}

.dashboard-shell {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1600px;
  margin: 0 auto;
  min-height: 100vh;
}

/* ===== 模块化网格 ===== */
.dash-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dash-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.dash-actions { display: flex; gap: 8px; }

.widget-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.widget {
  grid-column: span 4;
  position: relative;
  min-height: 0;
}
.widget.span-1 { grid-column: span 1; }
.widget.span-2 { grid-column: span 2; }
.widget.span-3 { grid-column: span 3; }
.widget.span-4 { grid-column: span 4; }
.widget.h-1 .widget-body { min-height: 90px; }
.widget.h-2 .widget-body { min-height: 220px; }
.widget.h-3 .widget-body { min-height: 340px; }
.widget-body { height: 100%; }

/* 编辑模式：控制条 + 虚线边框，视图模式无任何额外痕迹 */
.widget-grid.editing .widget {
  outline: 1px dashed var(--border-default);
  border-radius: var(--radius-lg);
  cursor: grab;
}
.widget-grid.editing .widget.dragging { opacity: 0.5; }
.widget-grid.editing .widget.over { outline: 2px dashed var(--brand-primary, #0984e3); }

.widget-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 8px;
  background: var(--bg-tertiary, #eef2f7);
  border-radius: var(--radius-md, 8px) var(--radius-md, 8px) 0 0;
  margin-bottom: 6px;
}
.wt-name { display: flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.wt-controls { display: flex; gap: 4px; }
.wt-btn {
  width: 22px; height: 22px; line-height: 20px;
  border: 1px solid var(--border-default);
  background: var(--bg-secondary);
  border-radius: 4px; cursor: pointer;
  font-size: 12px; color: var(--text-secondary);
}
.wt-btn.active { background: var(--brand-primary, #0984e3); color: #fff; border-color: transparent; }
.wt-btn.danger { color: #ef4444; }
.wt-btn:hover { border-color: var(--brand-primary, #0984e3); }

.widget-empty {
  display: flex; align-items: center; justify-content: center;
  height: 100%; min-height: 80px;
  color: var(--text-muted); font-size: 13px;
}

.grafana-widget { height: 100%; min-height: 320px; }
.grafana-frame {
  width: 100%;
  height: 100%;
  min-height: 320px;
  border: none;
  border-radius: var(--radius-md, 8px);
  background: #fff;
}

.palette-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.palette-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
}
.palette-item:hover { border-color: var(--brand-primary, #0984e3); background: var(--bg-tertiary, #eef2f7); }
.pi-add { color: var(--brand-primary, #0984e3); font-weight: 700; }
.palette-empty { text-align: center; color: var(--text-muted); padding: 20px; }

.grafana-widget { height: 100%; min-height: 320px; }
.grafana-frame {
  width: 100%;
  height: 100%;
  min-height: 320px;
  border: none;
  border-radius: var(--radius-md, 8px);
  background: #fff;
}

/* ===== Realtime Status Section ===== */
.realtime-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.realtime-strip {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding: 14px 18px;
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-left: 4px solid #22c55e;
}
.realtime-strip.yellow { border-left-color: #facc15; }
.realtime-strip.red { border-left-color: #ef4444; }

.rt-headline { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.rt-title { font-size: 14px; color: var(--text-primary); }
.rt-dot { width: 10px; height: 10px; border-radius: 50%; background: #22c55e; }
.rt-dot.yellow { background: #facc15; }
.rt-dot.red { background: #ef4444; animation: rt-pulse 1.4s infinite; }
@keyframes rt-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.rt-metrics { display: flex; gap: 24px; flex-wrap: wrap; flex: 1; }
.rt-item { display: flex; flex-direction: column; }
.rt-num { font-size: 20px; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.rt-label { font-size: 12px; color: var(--text-muted); }
.rt-item.warning .rt-num { color: #d97706; }
.rt-item.danger .rt-num { color: #ef4444; }

.rt-link { font-size: 13px; font-weight: 600; color: var(--brand-primary, #0984e3); text-decoration: none; white-space: nowrap; }
.rt-link:hover { text-decoration: underline; }

.site-breakdown { display: flex; flex-direction: column; gap: 8px; }
.site-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.site-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.site-card {
  padding: 10px 12px;
  border-radius: var(--radius-md, 8px);
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-top: 3px solid #22c55e;
}
.site-card.yellow { border-top-color: #facc15; }
.site-card.red { border-top-color: #ef4444; }
.site-head { display: flex; align-items: center; gap: 6px; }
.site-dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }
.site-dot.yellow { background: #facc15; }
.site-dot.red { background: #ef4444; }
.site-name { font-size: 13px; font-weight: 600; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.site-avail { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 2px 0; }
.site-meta { font-size: 12px; color: var(--text-muted); }
.site-meta .off { color: #ef4444; }
.site-meta .flt { color: #d97706; }

/* ===== Executive Summary Section ===== */
.executive-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
}

.summary-bar.risk {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.summary-bar.warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
}

.summary-bar.stable {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.3);
}

.summary-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
}

.summary-bar.risk .summary-icon {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.summary-bar.warning .summary-icon {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.summary-bar.stable .summary-icon {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.summary-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.summary-range {
  font-size: 11px;
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.executive-kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

@media (max-width: 1200px) {
  .executive-kpi-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 900px) {
  .executive-kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 600px) {
  .executive-kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* ===== V2 Analytics Row ===== */
.v2-analytics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 900px) {
  .v2-analytics-row {
    grid-template-columns: 1fr;
  }
}

/* ===== V2 SLO Row ===== */
.v2-slo-row {
  margin-top: 16px;
}

/* ===== V2 Change Row ===== */
.v2-change-row {
  margin-top: 16px;
}

/* ===== Footer ===== */
.dashboard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  font-size: 12px;
  color: var(--text-muted);
}

.footer-version {
  font-family: 'JetBrains Mono', monospace;
}

.footer-sync {
  font-family: 'JetBrains Mono', monospace;
}

/* Dark mode */
.dark .dashboard {
  background:
    radial-gradient(circle at top left, rgba(9, 132, 227, 0.15), transparent 28%),
    radial-gradient(circle at top right, rgba(0, 184, 148, 0.12), transparent 24%),
    linear-gradient(180deg, #0f172a 0%, #1e293b 48%, #0f172a 100%);
}

.dark .summary-bar {
  background: rgba(30, 41, 59, 0.8);
}

.dark .executive-section {
  background: transparent;
}
</style>
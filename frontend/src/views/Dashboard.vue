<template>
  <div class="dashboard">
    <div class="dashboard-shell">
      <!-- 实时基础设施状态（现在什么状态） -->
      <section class="realtime-section" v-if="realtime">
        <div class="realtime-strip" :class="realtime.overall_status">
          <div class="rt-headline">
            <span class="rt-dot" :class="realtime.overall_status"></span>
            <span class="rt-title">{{ t('rtTitle') }}</span>
          </div>
          <div class="rt-metrics">
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
        <div class="site-breakdown" v-if="realtime.sites && realtime.sites.length">
          <div class="site-title">{{ t('rtSiteTitle') }}</div>
          <div class="site-grid">
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
        </div>
      </section>

      <!-- Executive Summary Section (管理层视角) -->
      <section class="executive-section" v-if="executiveSummary">
        <!-- Summary Bar -->
        <div class="summary-bar" :class="summaryBarClass">
          <div class="summary-icon">
            <el-icon><DataBoard /></el-icon>
          </div>
          <span class="summary-text">{{ executiveSummary.summary_text }}</span>
          <span class="summary-range">{{ executiveSummary.range }}</span>
        </div>

        <!-- KPI Grid -->
        <div class="executive-kpi-grid">
          <KpiStat
            v-if="executiveSummary.kpis?.availability"
            :kpi="executiveSummary.kpis.availability"
            :title="t('kpiAvailability')"
            link="/devices"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.active_faults"
            :kpi="executiveSummary.kpis.active_faults"
            :title="t('kpiActiveFaults')"
            link="/faults?status=open"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.sla_rate"
            :kpi="executiveSummary.kpis.sla_rate"
            :title="t('kpiSlaRate')"
            link="/maintenance"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.mttr_hours"
            :kpi="executiveSummary.kpis.mttr_hours"
            :title="t('kpiMttr')"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.month_cost"
            :kpi="executiveSummary.kpis.month_cost"
            :title="t('kpiMonthCost')"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.budget_variance"
            :kpi="executiveSummary.kpis.budget_variance"
            :title="t('kpiBudgetVariance')"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.recurring_rate"
            :kpi="executiveSummary.kpis.recurring_rate"
            :title="t('kpiRecurringRate')"
            link="/faults"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.spare_low_stock"
            :kpi="executiveSummary.kpis.spare_low_stock"
            :title="t('kpiSpareLowStock')"
            link="/spare-parts?low_stock=true"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.spare_days_cover"
            :kpi="executiveSummary.kpis.spare_days_cover"
            :title="t('kpiDaysCover')"
            link="/spare-parts"
            :show-trend-value="true"
          />
          <KpiStat
            v-if="executiveSummary.kpis?.mtbf_days"
            :kpi="executiveSummary.kpis.mtbf_days"
            :title="t('kpiMtbf')"
          />
        </div>

        <!-- V2 P0: MTTR 四段拆解 + 根因帕累托 -->
        <div class="v2-analytics-row" v-if="executiveSummary?.mttr_breakdown || executiveSummary?.root_cause_pareto">
          <MttrFunnel
            v-if="executiveSummary.mttr_breakdown"
            :breakdown="executiveSummary.mttr_breakdown"
            :title="t('mttrBreakdownTitle')"
          />
          <ParetoChart
            v-if="executiveSummary.root_cause_pareto?.length"
            :data="executiveSummary.root_cause_pareto"
            :title="t('paretoChartTitle')"
          />
        </div>

        <!-- V2 P1: SLO 错误预算 -->
        <div class="v2-slo-row" v-if="executiveSummary?.slo?.length">
          <ErrorBudget
            :data="executiveSummary.slo"
            :title="t('sloErrorBudgetTitle')"
          />
        </div>

        <!-- V2 P1: 变更-故障关联分析 -->
        <div class="v2-change-row" v-if="executiveSummary?.change_fault_correlation">
          <ChangeCorrelation
            :data="executiveSummary.change_fault_correlation"
            :title="t('changeCorrelationTitle')"
          />
        </div>
      </section>

      <!-- Footer -->
      <footer class="dashboard-footer">
        <span class="footer-version">{{ t('dashVersion') }} v2.0.0</span>
        <span class="footer-sync">{{ t('dashLastSync') }}: {{ currentTime }}</span>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { DataBoard } from '@element-plus/icons-vue'
import { getExecutiveSummary, getRealtimeStatus } from '@/api'
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
  realtimeTimerId = window.setInterval(loadRealtime, 30000)
  timerId = window.setInterval(() => { currentTime.value = dayjs().format('HH:mm:ss') }, 1000)
})

onUnmounted(() => {
  if (timerId) window.clearInterval(timerId)
  if (realtimeTimerId) window.clearInterval(realtimeTimerId)
})
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
<template>
  <div class="dashboard">
    <div class="dashboard-shell">
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
import { getExecutiveSummary } from '@/api'
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
const currentTime = ref(dayjs().format('HH:mm:ss'))
let timerId = null

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

onMounted(() => {
  loadExecutive()
  timerId = window.setInterval(() => { currentTime.value = dayjs().format('HH:mm:ss') }, 1000)
})

onUnmounted(() => {
  if (timerId) window.clearInterval(timerId)
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
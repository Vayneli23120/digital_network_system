<template>
  <div class="dashboard">
    <div class="dashboard-shell">
      <!-- KPI Cards: 每个模块只出现一次 -->
      <section class="kpi-section">
        <div class="section-heading">
          <div>
            <h2 class="section-title">{{ t('dashHeroTitle') }}</h2>
          </div>
          <p class="section-desc">{{ t('dashSectionMetricsDesc') }}</p>
        </div>

        <div class="kpi-grid">
          <!-- 1. 设备总览 -->
          <div class="kpi-card span-row" @click="navigateTo('/devices')">
            <div class="kpi-header">
              <div class="kpi-icon devices">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="2" y="3" width="20" height="14" rx="2"/>
                  <path d="M8 21h8M12 17v4"/>
                </svg>
              </div>
              <span class="kpi-title">{{ t('dashNetworkDevices') }}</span>
              <span class="device-health-score" :class="healthScoreClass">{{ healthScore }}</span>
            </div>
            <div class="kpi-body">
              <div class="noc-device-panel">
                <!-- Top: Health Ring + Key Metrics -->
                <div class="noc-top-section">
                  <div class="noc-health-gauge">
                    <svg class="noc-ring" viewBox="0 0 100 100">
                      <circle class="noc-ring-bg" cx="50" cy="50" r="42"/>
                      <circle class="noc-ring-progress" cx="50" cy="50" r="42"
                        :stroke-dasharray="263.9"
                        :stroke-dashoffset="263.9 * (1 - healthScore / 100)"
                        :class="healthScoreClass"/>
                    </svg>
                    <div class="noc-health-center">
                      <span class="noc-health-value">{{ healthScore }}</span>
                      <span class="noc-health-label">{{ t('dashHealthScore') }}</span>
                    </div>
                  </div>
                  <div class="noc-quick-stats">
                    <div class="noc-stat-box">
                      <span class="noc-stat-value reachability">{{ onlinePercent }}%</span>
                      <span class="noc-stat-label">{{ t('dashReachability') }}</span>
                    </div>
                    <div class="noc-stat-box">
                      <span class="noc-stat-value" :class="{ warning: offlineDeviceCount > 0 }">{{ offlineDeviceCount }}</span>
                      <span class="noc-stat-label">{{ t('dashUnreachable') }}</span>
                    </div>
                    <div class="noc-stat-box">
                      <span class="noc-stat-value">{{ totalDevices }}</span>
                      <span class="noc-stat-label">{{ t('dashTotalDevices') }}</span>
                    </div>
                  </div>
                </div>

                <!-- Middle: Architecture Layers -->
                <div class="noc-layers">
                  <div class="noc-layer">
                    <div class="noc-layer-header">
                      <span class="noc-layer-name">{{ t('deviceLayerCore') }}</span>
                      <span class="noc-layer-count">{{ coreTotal }} {{ t('dashDevices') }}</span>
                    </div>
                    <div class="noc-layer-bar">
                      <div class="noc-segment online" :style="{ width: (coreTotal > 0 ? coreOnline / coreTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment offline" v-if="coreOffline > 0" :style="{ width: (coreTotal > 0 ? coreOffline / coreTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment maintenance" v-if="coreMaintenance > 0" :style="{ width: (coreTotal > 0 ? coreMaintenance / coreTotal * 100 : 0) + '%' }"></div>
                    </div>
                    <div class="noc-layer-types">
                      <div class="noc-type-pill" v-for="dtype in ['core_switch', 'server_switch', 'firewall', 'router']" :key="dtype"
                        :class="{ active: deviceByType(dtype, 'total') > 0, alert: deviceByType(dtype, 'offline') > 0 }"
                        v-if="deviceByType(dtype, 'total') > 0">
                        <span class="noc-type-dot" :class="typeStatus(dtype)"></span>
                        <span class="noc-type-name">{{ typeLabel(dtype) }}</span>
                        <span class="noc-type-num">{{ deviceByType(dtype, 'total') }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="noc-layer">
                    <div class="noc-layer-header">
                      <span class="noc-layer-name">{{ t('deviceLayerWiFi') }}</span>
                      <span class="noc-layer-count">{{ wifiTotal }} {{ t('dashDevices') }}</span>
                    </div>
                    <div class="noc-layer-bar">
                      <div class="noc-segment online" :style="{ width: (wifiTotal > 0 ? wifiOnline / wifiTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment offline" v-if="wifiOffline > 0" :style="{ width: (wifiTotal > 0 ? wifiOffline / wifiTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment maintenance" v-if="wifiMaintenance > 0" :style="{ width: (wifiTotal > 0 ? wifiMaintenance / wifiTotal * 100 : 0) + '%' }"></div>
                    </div>
                    <div class="noc-layer-types">
                      <div class="noc-type-pill" v-for="dtype in ['ap', 'wlc']" :key="dtype"
                        :class="{ active: deviceByType(dtype, 'total') > 0, alert: deviceByType(dtype, 'offline') > 0 }"
                        v-if="deviceByType(dtype, 'total') > 0">
                        <span class="noc-type-dot" :class="typeStatus(dtype)"></span>
                        <span class="noc-type-name">{{ typeLabel(dtype) }}</span>
                        <span class="noc-type-num">{{ deviceByType(dtype, 'total') }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="noc-layer">
                    <div class="noc-layer-header">
                      <span class="noc-layer-name">{{ t('deviceLayerAccess') }}</span>
                      <span class="noc-layer-count">{{ accessTotal }} {{ t('dashDevices') }}</span>
                    </div>
                    <div class="noc-layer-bar">
                      <div class="noc-segment online" :style="{ width: (accessTotal > 0 ? accessOnline / accessTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment offline" v-if="accessOffline > 0" :style="{ width: (accessTotal > 0 ? accessOffline / accessTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment maintenance" v-if="accessMaintenance > 0" :style="{ width: (accessTotal > 0 ? accessMaintenance / accessTotal * 100 : 0) + '%' }"></div>
                    </div>
                    <div class="noc-layer-types">
                      <div class="noc-type-pill" v-for="dtype in ['uce', 'office_switch']" :key="dtype"
                        :class="{ active: deviceByType(dtype, 'total') > 0, alert: deviceByType(dtype, 'offline') > 0 }"
                        v-if="deviceByType(dtype, 'total') > 0">
                        <span class="noc-type-dot" :class="typeStatus(dtype)"></span>
                        <span class="noc-type-name">{{ typeLabel(dtype) }}</span>
                        <span class="noc-type-num">{{ deviceByType(dtype, 'total') }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Bottom: Configuration & Compliance Summary -->
                <div class="noc-compliance">
                  <div class="noc-compliance-header">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    <span>{{ t('dashConfigCompliance') }}</span>
                  </div>
                  <div class="noc-compliance-grid">
                    <div class="noc-compliance-item">
                      <div class="noc-compliance-bar">
                        <div class="noc-compliance-fill" :style="{ width: backupCoverage + '%' }"></div>
                      </div>
                      <span class="noc-compliance-label">{{ t('dashBackupCoverage') }}</span>
                      <span class="noc-compliance-value">{{ backupCoverage }}%</span>
                    </div>
                    <div class="noc-compliance-item" v-if="recentConfigChanges > 0">
                      <span class="noc-compliance-dot changed"></span>
                      <span class="noc-compliance-label">{{ t('dashConfigChanges7d') }}</span>
                      <span class="noc-compliance-value">{{ recentConfigChanges }}</span>
                    </div>
                    <div class="noc-compliance-item" v-if="devicesWithIssues.length > 0">
                      <span class="noc-compliance-dot issue"></span>
                      <span class="noc-compliance-label">{{ t('dashTopIssueDevice') }}</span>
                      <span class="noc-compliance-value noc-ellipsis">{{ topIssueDevice }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 2. 故障事件 -->
          <div class="kpi-card" @click="navigateTo('/faults')">
            <div class="kpi-header">
              <div class="kpi-icon faults">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 9v4M12 17h.01"/>
                  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.47a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                </svg>
              </div>
              <span class="kpi-title">{{ t('dashFaultEvents') }}</span>
              <span class="trend-badge">{{ t('dashDays30') }}</span>
            </div>
            <div class="kpi-body">
              <div class="big-number danger">{{ stats.faults?.count_30days || 0 }}</div>
              <div class="severity-row">
                <div class="severity-tag"><span class="dot critical"></span><span class="severity-label">{{ t('dashCritical') }}</span><span class="severity-num">{{ stats.faults?.critical_count || 0 }}</span></div>
                <div class="severity-tag"><span class="dot major"></span><span class="severity-label">{{ t('dashMajor') }}</span><span class="severity-num">{{ stats.faults?.major_count || 0 }}</span></div>
                <div class="severity-tag"><span class="dot minor"></span><span class="severity-label">{{ t('dashMinor') }}</span><span class="severity-num">{{ stats.faults?.minor_count || 0 }}</span></div>
              </div>
              <div class="fault-maintenance-footer">
                <span class="maint-label">{{ t('dashMaintenance') }}</span>
                <span class="maint-item warn">{{ t('dashMaintenancePending') }} {{ stats.maintenance?.pending || 0 }}</span>
                <span class="maint-item active">{{ t('dashMaintenanceInProgress') }} {{ stats.maintenance?.in_progress || 0 }}</span>
                <span class="maint-item success">{{ t('dashMaintenanceCompleted') }} {{ stats.maintenance?.completed || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 3. 运维成本 -->
          <div class="kpi-card">
            <div class="kpi-header">
              <div class="kpi-icon cost">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
                </svg>
              </div>
              <span class="kpi-title">{{ t('dashMonthlyOpEx') }}</span>
            </div>
            <div class="kpi-body">
              <div class="big-number">¥{{ formatCost(stats.costs?.month_total || 0) }}</div>
              <div class="cost-split">
                <span class="cost-item-label"><span class="cost-dot parts"></span>{{ t('dashHardware') }} ¥{{ formatCost(stats.costs?.month_maintenance || 0) }}</span>
                <span class="cost-item-label"><span class="cost-dot labor"></span>{{ t('dashLabor') }} ¥{{ formatCost(monthlyLaborCost) }}</span>
              </div>
              <div class="cost-trend" v-if="costTrend.labels?.length">
                <div class="cost-bar-chart">
                  <div class="bar-group">
                    <div v-for="(label, i) in costTrend.labels" :key="i" class="cost-bar-item">
                      <div class="cost-bar-track">
                        <div class="cost-bar-fill parts" :style="{ height: (costTrend.parts[i] / costTrendMax * 100) + '%' }"></div>
                        <div class="cost-bar-fill labor" :style="{ height: (costTrend.labor[i] / costTrendMax * 100) + '%' }"></div>
                      </div>
                      <span class="cost-bar-label">{{ label }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 5. 故障设备 Top 5 -->
          <div class="kpi-card kpi-top5" @click="navigateTo('/faults')">
            <div class="kpi-header">
              <div class="kpi-icon faults">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M18 20V10M12 20V4M6 20v-6"/>
                </svg>
              </div>
              <span class="kpi-title">{{ t('dashTopFaultDevices') }}</span>
              <span class="trend-badge">30D</span>
            </div>
            <div class="kpi-body">
              <div class="top5-list">
                <div class="top5-item" v-for="(d, i) in faultDeviceList" :key="i">
                  <span class="top5-rank">{{ i + 1 }}</span>
                  <span class="top5-name" :title="d.device_name">{{ d.device_name }}</span>
                  <span class="top5-count">{{ d.count }}</span>
                </div>
                <div v-if="faultDeviceList.length === 0" class="empty-text">{{ t('dashNoEvents') }}</div>
              </div>
            </div>
          </div>

          <!-- 6. 备件库存 -->
          <div class="kpi-card" @click="navigateTo('/spare-parts')">
            <div class="kpi-header">
              <div class="kpi-icon inventory">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
                </svg>
              </div>
              <span class="kpi-title">{{ t('dashSpareInventory') }}</span>
            </div>
            <div class="kpi-body">
              <div class="spare-row">
                <span class="spare-stat"><span class="spare-num">{{ stats.spare_parts?.total_models || 0 }}</span> {{ t('dashSpareModels') }}</span>
                <span class="spare-stat"><span class="spare-num">{{ stats.spare_parts?.total_quantity || 0 }}</span> {{ t('dashSpareTotalQty') }}</span>
                <span class="spare-stat"><span class="spare-num warning">{{ stats.spare_parts?.low_stock_count || 0 }}</span> {{ t('dashSpareLowStock') }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Charts Section: 故障时间线 + 风险面板 -->
      <section class="charts-section">
        <div class="section-heading">
          <div>
            <h2 class="section-title">{{ t('dashSectionAnalyticsTitle') }}</h2>
          </div>
          <p class="section-desc">{{ t('dashSectionAnalyticsDesc') }}</p>
        </div>

        <div class="charts-split">
          <!-- 左侧：故障时间线 -->
          <div class="chart-panel emphasis">
            <div class="panel-header">
              <h3 class="panel-title">{{ t('dashFaultTimeline') }}</h3>
              <div class="panel-controls">
                <div class="pill-tabs">
                  <button
                    v-for="opt in timeOptions"
                    :key="opt.value"
                    class="pill-tab"
                    :class="{ active: faultTimeRange === opt.value }"
                    @click="faultTimeRange = opt.value; updateFaultChart()"
                  >
                    {{ opt.label }}
                  </button>
                </div>
                <input
                  v-if="faultTimeRange === 'custom'"
                  v-model="customStartDate"
                  type="date"
                  class="date-input"
                  @change="updateFaultChart"
                />
                <span v-if="faultTimeRange === 'custom'" class="date-separator">~</span>
                <input
                  v-if="faultTimeRange === 'custom'"
                  v-model="customEndDate"
                  type="date"
                  class="date-input"
                  @change="updateFaultChart"
                />
              </div>
            </div>
            <div class="panel-body">
              <div ref="faultLineChart" class="line-chart-container"></div>
            </div>
          </div>

          <!-- 右侧：最近备份 -->
          <div class="risk-panel single-panel">
            <div class="panel-header">
              <h3 class="panel-title">{{ t('dashConfigBackups') }}</h3>
              <button class="link-btn" @click="navigateTo('/backups')">
                {{ t('dashViewAll') }}
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
              </button>
            </div>
            <div class="panel-body">
              <div class="backup-panel-list">
                <div class="backup-panel-item" v-for="(b, i) in recentBackups" :key="i">
                  <span class="backup-panel-dot" :class="{ changed: b.has_change }"></span>
                  <span class="backup-panel-name">{{ b.device_name }}</span>
                  <span class="backup-panel-time">{{ formatDate(b.backup_time) }}</span>
                </div>
                <div v-if="recentBackups.length === 0" class="empty-text">{{ t('dashNoEvents') }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Activity Section: Event Stream + Activity Feed (无重复数据) -->
      <section class="activity-section">
        <div class="section-heading">
          <div>
            <h2 class="section-title">{{ t('dashSectionActivityTitle') }}</h2>
          </div>
          <p class="section-desc">{{ t('dashSectionActivityDesc') }}</p>
        </div>

        <div class="activity-grid">
          <!-- Event Stream: 告警信息 -->
          <div class="activity-panel">
            <div class="panel-header">
              <h3 class="panel-title">{{ t('dashEventStream') }}</h3>
              <span v-if="alertCount" class="alert-badge">{{ alertCount }}</span>
            </div>
            <div class="panel-body event-stream">
              <div class="event-item" v-for="(alert, i) in alerts" :key="i">
                <div class="event-timeline-marker">
                  <span :class="['event-dot', alert.severity]"></span>
                  <span class="event-line"></span>
                </div>
                <div class="event-content">
                  <span class="event-title">{{ alert.title }}</span>
                  <span class="event-summary">{{ alert.summary }}</span>
                  <span class="event-time">{{ alert.time }}</span>
                </div>
              </div>
              <div v-if="alerts.length === 0" class="event-empty">{{ t('dashNoEvents') }}</div>
            </div>
          </div>

          <!-- Activity Feed: 操作记录 -->
          <div class="activity-panel">
            <div class="panel-header">
              <h3 class="panel-title">{{ t('dashRecentActivity') }}</h3>
            </div>
            <div class="panel-body activity-feed">
              <div class="activity-item" v-for="(item, i) in activityFeed" :key="i">
                <div :class="['activity-icon', item.type]">
                  <svg v-if="item.type === 'backup'" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 3v12M12 15l4-4M12 15l-4-4"/>
                  </svg>
                  <svg v-else-if="item.type === 'fault'" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 9v4M12 17h.01"/>
                  </svg>
                  <svg v-else-if="item.type === 'maintenance'" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 12h4l3 8 4-16 3 8h4"/>
                  </svg>
                </div>
                <div class="activity-body">
                  <span class="activity-text">{{ item.text }}</span>
                  <span class="activity-time">{{ item.time }}</span>
                </div>
              </div>
            </div>
          </div>
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
import { ref, onMounted, nextTick, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getDashboardSummary } from '@/api'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const { t, currentLang } = useI18n()
const loading = ref(false)
const stats = ref({})
const recentBackups = ref([])
const faultLineChart = ref(null)
const faultTimeRange = ref('30d')
const customStartDate = ref(dayjs().subtract(30, 'day').format('YYYY-MM-DD'))
const customEndDate = ref(dayjs().format('YYYY-MM-DD'))
const faultChartInstance = ref(null)
const faultTotal = ref(0)
const currentTime = ref(dayjs().format('HH:mm:ss'))
const costTrend = ref({ labels: [], total: [], parts: [], labor: [] })
let timerId = null

const timeOptions = computed(() => [
  { value: '7d', label: '7D' },
  { value: '30d', label: '30D' },
  { value: '3m', label: '3M' },
  { value: '1y', label: '1Y' },
  { value: 'custom', label: t('dashCustom') }
])

const onlinePercent = computed(() => {
  const total = stats.value.devices?.total || 0
  if (total === 0) return 0
  return Math.round((stats.value.devices?.online || 0) / total * 100)
})

const topFaultDeviceName = computed(() => faultDeviceList.value.length > 0 ? faultDeviceList.value[0].device_name : '—')

const coreDeviceTypes = ['core_switch', 'server_switch', 'firewall', 'router']
const accessDeviceTypes = ['uce', 'office_switch']
const wifiDeviceTypes = ['ap', 'wlc']

// Core/Access/WiFi counts
const coreTotal = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'total'), 0))
const coreOnline = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'online'), 0))
const coreOffline = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'offline'), 0))
const coreMaintenance = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'maintenance'), 0))
const coreRetired = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'retired'), 0))

const accessTotal = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'total'), 0))
const accessOnline = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'online'), 0))
const accessOffline = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'offline'), 0))
const accessMaintenance = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'maintenance'), 0))
const accessRetired = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'retired'), 0))

const wifiTotal = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'total'), 0))
const wifiOnline = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'online'), 0))
const wifiOffline = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'offline'), 0))
const wifiMaintenance = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'maintenance'), 0))
const wifiRetired = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'retired'), 0))

const totalDevices = computed(() => stats.value.devices?.total || 0)
const offlineDeviceCount = computed(() => stats.value.devices?.offline || 0)

// Health Score (0-100): online devices / total devices * 100
const healthScore = computed(() => {
  const total = stats.value.devices?.total || 0
  if (total === 0) return 100
  const online = stats.value.devices?.online || 0
  return Math.round((online / total) * 100)
})

const healthScoreClass = computed(() => {
  if (healthScore.value >= 95) return 'healthy'
  if (healthScore.value >= 80) return 'warning'
  return 'critical'
})

// Config Compliance metrics
const backupCoverage = computed(() => {
  const total = stats.value.devices?.total || 0
  if (total === 0) return 0
  // Approximate: assume recent backups cover devices with backup records
  const backedUp = recentBackups.value.length > 0 ? Math.min(recentBackups.value.length * 2, total) : Math.round(total * 0.85)
  return Math.round((backedUp / total) * 100)
})

const recentConfigChanges = computed(() => {
  // Count backups with changes in last 7 days
  const sevenDaysAgo = dayjs().subtract(7, 'day')
  return recentBackups.value.filter(b => b.has_change && dayjs(b.backup_time).isAfter(sevenDaysAgo)).length
})

const devicesWithIssues = computed(() => {
  return faultDeviceList.value.filter(d => d.count > 0)
})

const topIssueDevice = computed(() => {
  return devicesWithIssues.value.length > 0 ? devicesWithIssues.value[0].device_name : '—'
})

const deviceByType = (type, status) => {
  return stats.value.devices?.by_type?.[type]?.[status] || 0
}

const typeLabel = (dtype) => {
  const map = {
    uce: t('deviceTypeUCE'),
    core_switch: t('deviceTypeCoreSwitch'),
    server_switch: t('deviceTypeServerSwitch'),
    office_switch: t('deviceTypeOfficeSwitch'),
    firewall: t('deviceTypeFirewall'),
    ap: t('deviceTypeAP'),
    wlc: t('deviceTypeWLC'),
    router: t('deviceTypeRouter'),
    other: t('deviceTypeOther'),
  }
  return map[dtype] || dtype
}

const typeStatus = (dtype) => {
  const t2 = stats.value.devices?.by_type?.[dtype]
  if (!t2 || t2.total === 0) return 'empty'
  if ((t2.offline || 0) > 0) return 'alert'
  if ((t2.maintenance || 0) > 0) return 'warn'
  return 'ok'
}

const alerts = computed(() => [
  { severity: 'warn', title: t('dashAlertBackupTitle'), summary: t('dashAlertBackupSummary'), time: '10m' },
  { severity: 'info', title: t('dashAlertMaintenanceTitle'), summary: t('dashAlertMaintenanceSummary'), time: '2h' },
  { severity: 'success', title: t('dashAlertHealthyTitle'), summary: t('dashAlertHealthySummary'), time: '1d' }
])

const alertCount = computed(() => alerts.value.filter(a => a.severity === 'warn' || a.severity === 'danger').length)
const monthlyLaborCost = computed(() => Math.max((stats.value.costs?.month_total || 0) - (stats.value.costs?.month_maintenance || 0), 0))
const backupChangedCount = computed(() => recentBackups.value.filter(item => item.has_change).length)

const lastBackupTime = computed(() => {
  if (recentBackups.value.length > 0) return formatDate(recentBackups.value[0].backup_time)
  return 'N/A'
})

const activityFeed = computed(() => {
  const items = []
  recentBackups.value.slice(0, 4).forEach(b => {
    items.push({
      type: 'backup',
      text: `${t('dashConfigBackups')}: ${b.device_name} — ${b.has_change ? t('dashModified') : t('dashClean')}`,
      time: formatDate(b.backup_time)
    })
  })
  if (stats.value.faults?.count_30days > 0) {
    items.push({
      type: 'fault',
      text: `${stats.value.faults.count_30days} ${t('dashFaultEvents')} (${t('dashDays30')})`,
      time: dayjs().format('MM-DD HH:mm')
    })
  }
  if (stats.value.maintenance?.completed > 0) {
    items.push({
      type: 'maintenance',
      text: `${stats.value.maintenance.completed} ${t('dashMaintenanceCompleted')}`,
      time: dayjs().format('MM-DD HH:mm')
    })
  }
  return items.slice(0, 8)
})

const formatCost = (val) => val.toLocaleString()
const formatDate = (dateStr) => dayjs(dateStr).format('MM-DD HH:mm')

const costTrendMax = computed(() => Math.max(...costTrend.value.total, 1))

// Top fault devices — from API
const faultDeviceList = ref([])

const loadFaultDeviceList = async () => {
  try {
    const res = await fetch('/api/dashboard/top-fault-devices?days=30&limit=5')
    const data = await res.json()
    const max = Math.max(...data.map(d => d.count), 1)
    faultDeviceList.value = data.map(d => ({
      device_id: d.device_id,
      device_name: d.device_name,
      count: d.count,
      barWidth: (d.count / max * 100) + '%',
    }))
  } catch (err) {
    console.error('Failed to load top fault devices:', err)
  }
}

const navigateTo = (path) => router.push(path)

const refreshData = async () => {
  loading.value = true
  await loadDashboardData()
  loading.value = false
  ElMessage.success(t('dashDataRefreshed'))
}

const loadDashboardData = async () => {
  try {
    const data = await getDashboardSummary()
    stats.value = data
    recentBackups.value = data.backups?.recent || []
    nextTick(() => {
      initFaultLineChart()
      updateFaultChart()
    })
    // Load cost trend
    try {
      const trendRes = await fetch('/api/dashboard/cost-trend?months=6')
      costTrend.value = await trendRes.json()
    } catch (err) {
      console.error('Failed to load cost trend:', err)
    }
    // Load top fault devices
    await loadFaultDeviceList()
  } catch (error) {
    ElMessage.error(t('dashLoadFailed'))
  }
}

const initFaultLineChart = () => {
  if (!faultLineChart.value) return
  if (faultChartInstance.value) faultChartInstance.value.dispose()
  faultChartInstance.value = echarts.init(faultLineChart.value)
  const isDark = document.documentElement.classList.contains('dark')
  const textColor = isDark ? '#e6edf3' : '#0f172a'
  const axisColor = isDark ? '#8b949e' : '#6B7A8D'
  const gridColor = isDark ? '#30363d' : '#E2E8F2'
  const splitColor = isDark ? '#21262d' : '#f1f5f9'

  faultChartInstance.value.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark ? 'rgba(15,23,42,0.92)' : 'rgba(255,255,255,0.95)',
      borderColor: isDark ? '#30363d' : '#E2E8F2',
      borderWidth: 1,
      textStyle: { color: textColor, fontFamily: 'JetBrains Mono', fontSize: 12 },
      axisPointer: { type: 'cross', lineStyle: { color: gridColor } }
    },
    legend: {
      data: [t('dashCritical'), t('dashMajor'), t('dashMinor'), t('dashWarning')],
      bottom: 0, itemWidth: 10, itemHeight: 10,
      textStyle: { color: axisColor, fontFamily: 'Geist', fontSize: 11 }
    },
    grid: { left: '3%', right: '4%', bottom: '18%', top: '5%', containLabel: true },
    xAxis: {
      type: 'category', boundaryGap: false, data: [],
      axisLine: { lineStyle: { color: gridColor } }, axisTick: { show: false },
      axisLabel: { color: axisColor, fontFamily: 'JetBrains Mono', fontSize: 10 }, splitLine: { show: false }
    },
    yAxis: {
      type: 'value', minInterval: 1,
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: axisColor, fontFamily: 'JetBrains Mono', fontSize: 10 },
      splitLine: { lineStyle: { color: splitColor, type: 'dashed' } }
    },
    series: [
      {
        name: t('dashCritical'), type: 'line', stack: 'Total', smooth: true,
        symbol: 'circle', symbolSize: 4, showSymbol: false,
        itemStyle: { color: '#d63031' }, lineStyle: { width: 2.5 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(214,48,49,0.35)' }, { offset: 1, color: 'rgba(214,48,49,0.02)' }] } },
        data: []
      },
      {
        name: t('dashMajor'), type: 'line', stack: 'Total', smooth: true,
        symbol: 'circle', symbolSize: 4, showSymbol: false,
        itemStyle: { color: '#e17055' }, lineStyle: { width: 2.5 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(225,112,85,0.3)' }, { offset: 1, color: 'rgba(225,112,85,0.02)' }] } },
        data: []
      },
      {
        name: t('dashMinor'), type: 'line', stack: 'Total', smooth: true,
        symbol: 'circle', symbolSize: 4, showSymbol: false,
        itemStyle: { color: '#0984e3' }, lineStyle: { width: 2.5 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(9,132,227,0.25)' }, { offset: 1, color: 'rgba(9,132,227,0.02)' }] } },
        data: []
      },
      {
        name: t('dashWarning'), type: 'line', stack: 'Total', smooth: true,
        symbol: 'circle', symbolSize: 4, showSymbol: false,
        itemStyle: { color: '#636e72' }, lineStyle: { width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(99,110,114,0.15)' }, { offset: 1, color: 'rgba(99,110,114,0.02)' }] } },
        data: []
      }
    ]
  })
}

const updateFaultChart = async () => {
  if (!faultChartInstance.value) return
  try {
    const range = faultTimeRange.value
    let url = `/api/dashboard/fault-trend?time_range=${range}`
    if (range === 'custom' && customStartDate.value && customEndDate.value) {
      url = `/api/dashboard/fault-trend?time_range=custom&start_date=${customStartDate.value}&end_date=${customEndDate.value}`
    }
    const response = await fetch(url)
    const data = await response.json()
    const severityData = { critical: [], major: [], minor: [], warning: [] }
    ;(data.labels || []).forEach((label) => {
      const counts = data.by_severity?.[label] || {}
      severityData.critical.push(counts.critical || 0)
      severityData.major.push(counts.major || 0)
      severityData.minor.push(counts.minor || 0)
      severityData.warning.push(counts.warning || 0)
    })
    faultChartInstance.value.setOption({
      xAxis: { data: data.labels || [] },
      series: [{ data: severityData.critical }, { data: severityData.major }, { data: severityData.minor }, { data: severityData.warning }]
    })
    let total = 0
    ;(data.labels || []).forEach((label) => {
      const counts = data.by_severity?.[label] || {}
      total += (counts.critical || 0) + (counts.major || 0) + (counts.minor || 0) + (counts.warning || 0)
    })
    faultTotal.value = total
  } catch (error) {
    ElMessage.error(t('dashFaultTrendFailed'))
  }
}

const handleResize = () => {
  faultChartInstance.value?.resize()
}

const handleThemeChange = () => {
  initFaultLineChart()
  updateFaultChart()
}

watch(currentLang, () => {
  nextTick(() => { handleThemeChange() })
})

onMounted(() => {
  loadDashboardData()
  window.addEventListener('resize', handleResize)
  window.addEventListener('theme-change', handleThemeChange)
  timerId = window.setInterval(() => { currentTime.value = dayjs().format('HH:mm:ss') }, 1000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('theme-change', handleThemeChange)
  if (timerId) window.clearInterval(timerId)
  faultChartInstance.value?.dispose()
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
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
}

/* ===== Section Heading ===== */
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 18px;
  margin-bottom: 16px;
}

.section-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.03em;
}

.section-desc {
  margin: 0;
  max-width: 460px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
  text-align: right;
}

/* ===== KPI Cards (single grid, 6 cards) ===== */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.kpi-card {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
  padding: 20px;
  transition: all 0.25s ease;
  cursor: pointer;
}

.kpi-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 18px 48px rgba(9, 132, 227, 0.1);
}
.kpi-card.span-row { grid-row: span 2; }

.kpi-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.kpi-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  flex-shrink: 0;
}

.kpi-icon svg { width: 16px; height: 16px; }
.kpi-icon.devices { background: rgba(9, 132, 227, 0.12); color: #0984e3; }
.kpi-icon.faults { background: rgba(214, 48, 49, 0.12); color: #d63031; }
.kpi-icon.cost { background: rgba(225, 112, 85, 0.12); color: #e17055; }
.kpi-icon.maintenance { background: rgba(245, 158, 11, 0.12); color: #d97706; }
.kpi-icon.backups { background: rgba(0, 184, 148, 0.12); color: #059669; }
.kpi-icon.inventory { background: rgba(46, 139, 87, 0.12); color: #2e8b57; }

.kpi-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.03em;
}

.kpi-total {
  margin-left: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #94a3b8;
}

.trend-badge {
  margin-left: auto;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(0, 184, 148, 0.08);
  color: #059669;
  font-size: 11px;
  font-weight: 600;
}

.big-number {
  font-family: 'JetBrains Mono', monospace;
  font-size: 32px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.03em;
  margin-bottom: 10px;
}

.big-number.danger { color: #d63031; }

/* NOC Device Panel - DNA Center / ServiceNow inspired */
.noc-device-panel { display: flex; flex-direction: column; gap: 16px; }

/* Top Section: Health Gauge + Quick Stats */
.noc-top-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}
.noc-health-gauge {
  position: relative;
  width: 80px;
  height: 80px;
  flex-shrink: 0;
}
.noc-ring {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.noc-ring-bg {
  fill: none;
  stroke: rgba(148, 163, 184, 0.12);
  stroke-width: 8;
}
.noc-ring-progress {
  fill: none;
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.6s ease;
}
.noc-ring-progress.healthy { stroke: #00b894; }
.noc-ring-progress.warning { stroke: #f59e0b; }
.noc-ring-progress.critical { stroke: #ef4444; }
.noc-health-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.noc-health-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1;
}
.noc-health-label {
  font-size: 9px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.noc-quick-stats {
  flex: 1;
  display: flex;
  gap: 8px;
}
.noc-stat-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 6px;
  border-radius: 10px;
  background: rgba(248, 250, 252, 0.92);
}
.noc-stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}
.noc-stat-value.reachability { color: #00b894; }
.noc-stat-value.warning { color: #f59e0b; }
.noc-stat-label {
  font-size: 10px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Health Score Badge in Header */
.device-health-score {
  margin-left: auto;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
}
.device-health-score.healthy { background: rgba(0, 184, 148, 0.12); color: #00b894; }
.device-health-score.warning { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
.device-health-score.critical { background: rgba(239, 68, 68, 0.12); color: #ef4444; }

/* Architecture Layers */
.noc-layers { display: flex; flex-direction: column; gap: 12px; }
.noc-layer {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.noc-layer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.noc-layer-name {
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.noc-layer-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
}
.noc-layer-bar {
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  background: rgba(148, 163, 184, 0.1);
  display: flex;
}
.noc-segment { transition: width 0.4s ease; }
.noc-segment.online { background: #00b894; }
.noc-segment.offline { background: #ef4444; }
.noc-segment.maintenance { background: #f59e0b; }
.noc-layer-types {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}
.noc-type-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.92);
  font-size: 11px;
  opacity: 0.4;
}
.noc-type-pill.active { opacity: 1; }
.noc-type-pill.alert { background: rgba(239, 68, 68, 0.08); }
.noc-type-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.noc-type-dot.ok { background: #00b894; }
.noc-type-dot.warn { background: #f59e0b; }
.noc-type-dot.alert { background: #ef4444; }
.noc-type-name { color: #475569; }
.noc-type-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #0f172a;
}

/* Compliance Section */
.noc-compliance {
  background: rgba(9, 132, 227, 0.04);
  border: 1px solid rgba(9, 132, 227, 0.1);
  border-radius: 10px;
  padding: 10px 12px;
}
.noc-compliance-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #0984e3;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.noc-compliance-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.noc-compliance-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.noc-compliance-bar {
  width: 60px;
  height: 4px;
  border-radius: 2px;
  background: rgba(148, 163, 184, 0.1);
  overflow: hidden;
}
.noc-compliance-fill {
  height: 100%;
  border-radius: 2px;
  background: #00b894;
}
.noc-compliance-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.noc-compliance-dot.changed { background: #f59e0b; }
.noc-compliance-dot.issue { background: #ef4444; }
.noc-compliance-label {
  color: #64748b;
  flex: 1;
}
.noc-compliance-value {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #0f172a;
}
.noc-compliance-value.noc-ellipsis {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Severity Row */
.severity-row { display: flex; gap: 10px; }
.severity-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.92);
}
.severity-tag .dot { flex-shrink: 0; }
.severity-label {
  font-size: 12px;
  font-weight: 500;
  color: #475569;
}
.severity-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

/* Fault maintenance footer */
.fault-maintenance-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}
.maint-label {
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.maint-item {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(248, 250, 252, 0.6);
}
.maint-item.warn { color: #d97706; }
.maint-item.active { color: #0984e3; }
.maint-item.success { color: #059669; }

.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.critical { background: #d63031; }
.dot.major { background: #e17055; }
.dot.minor { background: #0984e3; }

/* Status Pills (Maintenance) */
.status-pills { display: flex; flex-direction: column; gap: 6px; }
.status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(248, 250, 252, 0.92);
}

.status-pill.warning { color: #d97706; }
.status-pill.active { color: #0984e3; }
.status-pill.success { color: #059669; }

/* Cost Split */
.cost-split { display: flex; gap: 12px; }
.cost-item-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.92);
  font-size: 12px;
  color: #475569;
}
.cost-dot {
  width: 8px;
  height: 8px;
  border-radius: 3px;
  flex-shrink: 0;
}
.cost-dot.parts { background: rgba(225, 112, 85, 0.9); }
.cost-dot.labor { background: rgba(9, 132, 227, 0.9); }

/* Cost Trend Bar Chart */
.cost-trend { margin-top: 12px; }
.cost-bar-chart { height: 70px; }
.bar-group {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 56px;
  padding: 0 2px;
  gap: 4px;
}
.cost-bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
}
.cost-bar-track {
  width: 100%;
  height: 50px;
  position: relative;
  background: rgba(148, 163, 184, 0.08);
  border-radius: 4px;
  overflow: hidden;
}
.cost-bar-fill {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  border-radius: 4px;
  transition: height 0.4s ease;
}
.cost-bar-fill.parts { background: rgba(225, 112, 85, 0.7); }
.cost-bar-fill.labor { background: rgba(9, 132, 227, 0.7); }
.cost-bar-label {
  font-size: 9px;
  color: #94a3b8;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
}

/* Backup Row */
.backup-row { display: flex; flex-direction: column; gap: 6px; }
.backup-stat {
  font-size: 12px;
  color: #475569;
  padding: 6px 10px;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.92);
}
.backup-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}
.backup-num.success { color: #059669; }
.backup-num.warning { color: #d97706; }

/* Spare Row */
.spare-row { display: flex; gap: 8px; }
.spare-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(248, 250, 252, 0.92);
  font-size: 11px;
  color: #64748b;
  text-align: center;
}
.spare-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}
.spare-num.warning { color: #d97706; }

/* Top 5 List in KPI card */
.kpi-card.kpi-top5 .kpi-body { padding-top: 12px; }
.top5-list { display: flex; flex-direction: column; gap: 6px; }
.top5-item {
  display: grid;
  grid-template-columns: 18px 1fr 28px;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.92);
  transition: background 0.15s;
}
.top5-item:hover { background: rgba(148, 163, 184, 0.12); }
.top5-rank {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-align: center;
}
.top5-name {
  font-size: 12px;
  font-weight: 500;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.top5-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #d63031;
  text-align: right;
}

/* Backup Panel List (in charts section) */
.backup-panel-list { display: flex; flex-direction: column; gap: 0; }
.backup-panel-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  font-size: 12px;
}
.backup-panel-item:last-child { border-bottom: none; }
.backup-panel-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00b894;
  flex-shrink: 0;
}
.backup-panel-dot.changed { background: #f59e0b; }
.backup-panel-name { flex: 1; color: #0f172a; font-weight: 500; }
.backup-panel-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #94a3b8;
}

/* ===== Charts ===== */
.chart-panel {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
  overflow: hidden;
}

.chart-panel.emphasis {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(243, 248, 252, 0.92));
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.panel-body { padding: 20px; }

.panel-controls { display: flex; align-items: center; gap: 8px; }

.link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #0984e3;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.link-btn:hover { color: #0b6ec2; }

/* Pill Tabs */
.pill-tabs {
  display: flex;
  gap: 4px;
  padding: 3px;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 10px;
}

.pill-tab {
  padding: 5px 12px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: 'JetBrains Mono', monospace;
}

.pill-tab:hover { color: #0f172a; }
.pill-tab.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.date-input {
  padding: 5px 8px;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #334155;
  font-family: 'JetBrains Mono', monospace;
  width: 110px;
}

.date-separator { color: #64748b; font-size: 11px; }

.line-chart-container { height: 220px; }

/* ===== Charts Split: 2/3 + 1/3 ===== */
.charts-split {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.risk-panel {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
  overflow: hidden;
}

/* Risk panel - single full height */
.risk-panel.single-panel {
  align-self: stretch;
  min-height: 260px;
}

.empty-text {
  padding: 20px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

/* Risk panel - single full height */
.risk-panel.single-panel {
  align-self: stretch;
}

/* ===== Activity Section ===== */
.activity-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.activity-panel {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
  overflow: hidden;
}

.alert-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  background: #d63031;
  border-radius: 999px;
}

/* Event Stream */
.event-stream { display: flex; flex-direction: column; gap: 0; }
.event-item { display: flex; gap: 12px; padding: 14px 20px; transition: background 0.2s; }
.event-item:hover { background: rgba(248, 250, 252, 0.6); }

.event-timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  padding-top: 4px;
}

.event-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.event-dot.warn { background: #e17055; }
.event-dot.info { background: #0984e3; }
.event-dot.success { background: #00b894; }
.event-dot.danger { background: #d63031; }

.event-line { width: 2px; flex: 1; background: rgba(148, 163, 184, 0.15); margin-top: 4px; }
.event-item:last-child .event-line { display: none; }

.event-content { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.event-title { font-size: 13px; font-weight: 600; color: #0f172a; }
.event-summary { font-size: 12px; color: #64748b; }
.event-time { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: #94a3b8; }

.event-empty {
  padding: 32px 20px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

/* Activity Feed */
.activity-feed { display: flex; flex-direction: column; gap: 0; }
.activity-item { display: flex; gap: 12px; padding: 14px 20px; transition: background 0.2s; }
.activity-item:hover { background: rgba(248, 250, 252, 0.6); }

.activity-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.activity-icon.backup { background: rgba(0, 184, 148, 0.1); color: #059669; }
.activity-icon.fault { background: rgba(214, 48, 49, 0.1); color: #d63031; }
.activity-icon.maintenance { background: rgba(245, 158, 11, 0.1); color: #d97706; }
.activity-icon.health { background: rgba(71, 85, 105, 0.08); color: #475569; }

.activity-body { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.activity-text { font-size: 13px; color: #0f172a; line-height: 1.4; }
.activity-time { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: #94a3b8; }

/* ===== Footer ===== */
.dashboard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 24px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.footer-version { font-size: 11px; color: rgba(203, 213, 225, 0.35); }
.footer-sync { font-size: 12px; color: rgba(203, 213, 225, 0.55); }

/* ===== Responsive ===== */
@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpi-card.span-row { grid-row: span 1; }
}

@media (max-width: 1024px) {
  .dashboard-shell { padding: 16px; }
  .kpi-grid { grid-template-columns: 1fr; }
  .kpi-card.span-row { grid-row: span 1; }
  .charts-split { grid-template-columns: 1fr; }
  .risk-panel { min-height: 200px; }
  .activity-grid { grid-template-columns: 1fr; }
  .section-heading { flex-direction: column; align-items: flex-start; }
  .section-desc { text-align: left; }
}

@media (max-width: 640px) {
  .severity-row { flex-wrap: wrap; }
  .spare-row { flex-direction: column; }
  .cost-split { flex-direction: column; }
  .dashboard-footer { flex-direction: column; gap: 8px; align-items: flex-start; }
}

/* ===== Dark Mode ===== */
.dark .dashboard {
  background:
    radial-gradient(circle at top left, rgba(9, 132, 227, 0.1), transparent 28%),
    radial-gradient(circle at top right, rgba(0, 184, 148, 0.08), transparent 24%),
    linear-gradient(180deg, #070b14 0%, #0a0e14 48%, #070b14 100%);
}

.dark .kpi-card,
.dark .chart-panel,
.dark .activity-panel {
  background: rgba(15, 23, 42, 0.72);
  border-color: rgba(71, 85, 105, 0.28);
  box-shadow: 0 16px 48px rgba(2, 6, 23, 0.3);
}

.dark .chart-panel.emphasis {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(13, 17, 23, 0.82));
}

.dark .section-title,
.dark .panel-title,
.dark .big-number,
.dark .event-title,
.dark .activity-text,
.dark .spare-num,
.dark .backup-num,
.dark .kpi-total {
  color: #f8fafc;
}

.dark .section-desc,
.dark .kpi-title,
.dark .event-summary,
.dark .event-time,
.dark .activity-time,
.dark .cost-item-label,
.dark .spare-stat,
.dark .backup-stat {
  color: rgba(203, 213, 225, 0.65);
}

.dark .severity-tag,
.dark .status-pill,
.dark .cost-item-label,
.dark .maint-item,
.dark .backup-stat,
.dark .spare-stat {
  background: rgba(30, 41, 59, 0.6);
}
.dark .severity-label { color: rgba(203, 213, 225, 0.6); }
.dark .severity-num { color: #f8fafc; }
.dark .fault-maintenance-footer { border-top-color: rgba(71, 85, 105, 0.2); }
.dark .maint-label { color: rgba(203, 213, 225, 0.4); }

.dark .event-item:hover,
.dark .activity-item:hover {
  background: rgba(30, 41, 59, 0.4);
}

.dark .event-line { background: rgba(71, 85, 105, 0.2); }

.dark .pill-tabs { background: rgba(71, 85, 105, 0.15); }
.dark .pill-tab { color: rgba(203, 213, 225, 0.6); }
.dark .pill-tab.active {
  background: rgba(30, 41, 59, 0.8);
  color: #f8fafc;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.dark .date-input {
  background: rgba(30, 41, 59, 0.7);
  border-color: rgba(71, 85, 105, 0.3);
  color: #e2e8f0;
}

.dark .date-separator { color: rgba(203, 213, 225, 0.5); }

/* Cost trend bar chart dark mode */
.dark .cost-bar-track { background: rgba(71, 85, 105, 0.15); }
.dark .cost-bar-label { color: rgba(203, 213, 225, 0.4); }
.dark .cost-bar-fill.parts { background: rgba(225, 112, 85, 0.5); }
.dark .cost-bar-fill.labor { background: rgba(9, 132, 227, 0.5); }

/* NOC Device Panel dark mode */
.dark .noc-health-value { color: #f8fafc; }
.dark .noc-health-label { color: rgba(203, 213, 225, 0.4); }
.dark .noc-stat-box { background: rgba(30, 41, 59, 0.5); }
.dark .noc-stat-value { color: #f8fafc; }
.dark .noc-stat-label { color: rgba(203, 213, 225, 0.5); }
.dark .device-health-score.healthy { background: rgba(0, 184, 148, 0.15); color: #55efc4; }
.dark .device-health-score.warning { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.dark .device-health-score.critical { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.dark .noc-layer-name { color: rgba(203, 213, 225, 0.6); }
.dark .noc-layer-count { color: rgba(203, 213, 225, 0.4); }
.dark .noc-layer-bar { background: rgba(71, 85, 105, 0.15); }
.dark .noc-type-pill { background: rgba(30, 41, 59, 0.5); }
.dark .noc-type-pill.alert { background: rgba(239, 68, 68, 0.08); }
.dark .noc-type-name { color: rgba(203, 213, 225, 0.6); }
.dark .noc-type-num { color: #f8fafc; }
.dark .noc-compliance { background: rgba(9, 132, 227, 0.06); border-color: rgba(9, 132, 227, 0.15); }
.dark .noc-compliance-header { color: #74b9ff; }
.dark .noc-compliance-bar { background: rgba(71, 85, 105, 0.15); }
.dark .noc-compliance-fill { background: #55efc4; }
.dark .noc-compliance-label { color: rgba(203, 213, 225, 0.5); }
.dark .noc-compliance-value { color: #f8fafc; }

/* Cost trend bar chart dark mode */

.dark .dashboard-footer { background: rgba(2, 6, 23, 0.85); }

/* Top 5 list dark mode */
.dark .top5-item { background: rgba(30, 41, 59, 0.5); }
.dark .top5-item:hover { background: rgba(71, 85, 105, 0.25); }
.dark .top5-name { color: #f8fafc; }
.dark .top5-count { color: #ef4444; }
.dark .top5-rank { color: rgba(203, 213, 225, 0.4); }

/* Backup panel dark mode */
.dark .backup-panel-item { border-bottom-color: rgba(71, 85, 105, 0.2); }
.dark .backup-panel-name { color: #f8fafc; }
.dark .backup-panel-dot { background: rgba(0, 184, 148, 0.6); }
.dark .backup-panel-dot.changed { background: rgba(245, 158, 11, 0.6); }

/* Risk panels dark mode */
.dark .risk-panel {
  background: rgba(15, 23, 42, 0.72);
  border-color: rgba(71, 85, 105, 0.28);
}
.dark .risk-panel.single-panel { min-height: 220px; }
</style>

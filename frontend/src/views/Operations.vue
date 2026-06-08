<template>
  <div class="dashboard">
    <div class="dashboard-shell">
      <!-- KPI Cards: 每个模块只出现一次 -->
      <section class="kpi-section">
        <div class="section-heading">
          <div>
            <h2 class="section-title">{{ t('operationsTitle') }}</h2>
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
                <div class="noc-layers">
                  <div class="noc-layer">
                    <div class="noc-layer-header">
                      <span class="noc-layer-name">{{ t('deviceLayerCore') }}</span>
                      <span class="noc-layer-count">{{ coreTotal }} {{ t('dashDevices') }}</span>
                    </div>
                    <div class="noc-layer-bar">
                      <div class="noc-segment reachable" :style="{ width: (coreTotal > 0 ? coreReachable / coreTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment unreachable" v-if="coreUnreachable > 0" :style="{ width: (coreTotal > 0 ? coreUnreachable / coreTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment maintenance" v-if="coreMaintenance > 0" :style="{ width: (coreTotal > 0 ? coreMaintenance / coreTotal * 100 : 0) + '%' }"></div>
                    </div>
                    <div class="noc-layer-types">
                      <div class="noc-type-pill" v-for="dtype in ['core_switch', 'server_switch', 'router']" :key="dtype"
                        :class="{ active: deviceByType(dtype, 'total') > 0, alert: deviceByType(dtype, 'unreachable') > 0 }"
                        v-if="deviceByType(dtype, 'total') > 0">
                        <span class="noc-type-dot" :class="typeStatus(dtype)"></span>
                        <span class="noc-type-name">{{ typeLabel(dtype) }}</span>
                        <span class="noc-type-num">{{ deviceByType(dtype, 'total') }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="noc-layer">
                    <div class="noc-layer-header">
                      <span class="noc-layer-name">{{ t('deviceLayerFirewall') }}</span>
                      <span class="noc-layer-count">{{ firewallTotal }} {{ t('dashDevices') }}</span>
                    </div>
                    <div class="noc-layer-bar">
                      <div class="noc-segment reachable" :style="{ width: (firewallTotal > 0 ? firewallReachable / firewallTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment unreachable" v-if="firewallUnreachable > 0" :style="{ width: (firewallTotal > 0 ? firewallUnreachable / firewallTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment maintenance" v-if="firewallMaintenance > 0" :style="{ width: (firewallTotal > 0 ? firewallMaintenance / firewallTotal * 100 : 0) + '%' }"></div>
                    </div>
                    <div class="noc-layer-types">
                      <div class="noc-type-pill" v-for="dtype in ['pa', 'ftd']" :key="dtype"
                        :class="{ active: deviceByType(dtype, 'total') > 0, alert: deviceByType(dtype, 'unreachable') > 0 }"
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
                      <div class="noc-segment reachable" :style="{ width: (wifiTotal > 0 ? wifiReachable / wifiTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment unreachable" v-if="wifiUnreachable > 0" :style="{ width: (wifiTotal > 0 ? wifiUnreachable / wifiTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment maintenance" v-if="wifiMaintenance > 0" :style="{ width: (wifiTotal > 0 ? wifiMaintenance / wifiTotal * 100 : 0) + '%' }"></div>
                    </div>
                    <div class="noc-layer-types">
                      <div class="noc-type-pill" v-for="dtype in ['ap', 'wlc']" :key="dtype"
                        :class="{ active: deviceByType(dtype, 'total') > 0, alert: deviceByType(dtype, 'unreachable') > 0 }"
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
                      <div class="noc-segment reachable" :style="{ width: (accessTotal > 0 ? accessReachable / accessTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment unreachable" v-if="accessUnreachable > 0" :style="{ width: (accessTotal > 0 ? accessUnreachable / accessTotal * 100 : 0) + '%' }"></div>
                      <div class="noc-segment maintenance" v-if="accessMaintenance > 0" :style="{ width: (accessTotal > 0 ? accessMaintenance / accessTotal * 100 : 0) + '%' }"></div>
                    </div>
                    <div class="noc-layer-types">
                      <div class="noc-type-pill" v-for="dtype in ['uce', 'office_switch']" :key="dtype"
                        :class="{ active: deviceByType(dtype, 'total') > 0, alert: deviceByType(dtype, 'unreachable') > 0 }"
                        v-if="deviceByType(dtype, 'total') > 0">
                        <span class="noc-type-dot" :class="typeStatus(dtype)"></span>
                        <span class="noc-type-name">{{ typeLabel(dtype) }}</span>
                        <span class="noc-type-num">{{ deviceByType(dtype, 'total') }}</span>
                      </div>
                    </div>
                  </div>
                </div>
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
              <div class="kpi-icon faults" :class="{ 'has-alert': activeFaults > 0 }">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 9v4M12 17h.01"/>
                  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.47a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                </svg>
              </div>
              <span class="kpi-title">{{ t('dashFaultEvents') }}</span>
              <span class="trend-badge" :class="{ 'alert': activeFaults > 0 }">{{ activeFaults > 0 ? t('dashActive') : t('dashAllResolved') }}</span>
            </div>
            <div class="kpi-body">
              <div class="fault-active-section" :class="{ 'has-active': activeFaults > 0 }">
                <div class="big-number" :class="{ danger: activeFaults > 0, success: activeFaults === 0 }">
                  {{ activeFaults }}
                </div>
                <div class="active-label">{{ t('dashActiveFaults') }}</div>
                <div class="severity-row" v-if="activeFaults > 0">
                  <div class="severity-tag" v-if="activeCritical > 0"><span class="dot critical"></span><span class="severity-label">{{ t('dashCritical') }}</span><span class="severity-num">{{ activeCritical }}</span></div>
                  <div class="severity-tag" v-if="activeMajor > 0"><span class="dot major"></span><span class="severity-label">{{ t('dashMajor') }}</span><span class="severity-num">{{ activeMajor }}</span></div>
                  <div class="severity-tag" v-if="activeMinor > 0"><span class="dot minor"></span><span class="severity-label">{{ t('dashMinor') }}</span><span class="severity-num">{{ activeMinor }}</span></div>
                </div>
              </div>
              <div class="fault-resolved-section" v-if="resolvedFaults > 0">
                <span class="resolved-label">{{ t('dashResolvedFaults') }}</span>
                <span class="resolved-num">{{ resolvedFaults }}</span>
                <span class="resolved-period">{{ t('dashDays30') }}</span>
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
              <span class="kpi-title">{{ t('dashCostTrend') }}</span>
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

      <!-- Activity Section: Event Stream + Activity Feed -->
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
              <div class="event-item" v-for="(alert, i) in alerts" :key="i"
                   @click="alert.link && router.push(alert.link)" :style="{ cursor: alert.link ? 'pointer' : 'default' }">
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
              <div class="activity-item" v-for="(item, i) in activityFeed" :key="i"
                   @click="item.link && router.push(item.link)" :style="{ cursor: item.link ? 'pointer' : 'default' }">
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
import { getDashboardSummary, getAlerts } from '@/api'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'

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
const currentTime = ref(dayjs().format('HH:mm:ss'))
const costTrend = ref({ labels: [], total: [], parts: [], labor: [] })
const faultDeviceList = ref([])
const realAlerts = ref([])
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
  return Math.round((stats.value.devices?.reachable || 0) / total * 100)
})

const totalDevices = computed(() => stats.value.devices?.total || 0)
const offlineDeviceCount = computed(() => stats.value.devices?.unreachable || 0)

const healthScore = computed(() => {
  const total = totalDevices.value
  const reachable = stats.value.devices?.reachable || 0
  const issues = stats.value.faults?.active || 0
  if (total === 0) return 100
  const base = Math.round((reachable / total) * 80)
  const penalty = Math.min(issues * 5, 20)
  return Math.max(base - penalty, 0)
})

const healthScoreClass = computed(() => {
  const score = healthScore.value
  if (score >= 90) return 'good'
  if (score >= 70) return 'warn'
  return 'critical'
})

const activeFaults = computed(() => stats.value.faults?.active || 0)
const activeCritical = computed(() => stats.value.faults?.active_critical || 0)
const activeMajor = computed(() => stats.value.faults?.active_major || 0)
const activeMinor = computed(() => stats.value.faults?.active_minor || 0)
const resolvedFaults = computed(() => stats.value.faults?.resolved || 0)

const coreDeviceTypes = ['core_switch', 'server_switch', 'router']
const accessDeviceTypes = ['uce', 'office_switch']
const wifiDeviceTypes = ['ap', 'wlc']
const firewallDeviceTypes = ['pa', 'ftd']

const deviceByType = (type, field) => {
  const devices = stats.value.devices_by_type?.[type] || {}
  return devices[field] || 0
}

const coreTotal = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'total'), 0))
const coreReachable = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'reachable'), 0))
const coreUnreachable = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'unreachable'), 0))
const coreMaintenance = computed(() => coreDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'maintenance'), 0))

const accessTotal = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'total'), 0))
const accessReachable = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'reachable'), 0))
const accessUnreachable = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'unreachable'), 0))
const accessMaintenance = computed(() => accessDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'maintenance'), 0))

const wifiTotal = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'total'), 0))
const wifiReachable = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'reachable'), 0))
const wifiUnreachable = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'unreachable'), 0))
const wifiMaintenance = computed(() => wifiDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'maintenance'), 0))

const firewallTotal = computed(() => firewallDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'total'), 0))
const firewallReachable = computed(() => firewallDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'reachable'), 0))
const firewallUnreachable = computed(() => firewallDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'unreachable'), 0))
const firewallMaintenance = computed(() => firewallDeviceTypes.reduce((sum, t) => sum + deviceByType(t, 'maintenance'), 0))

const typeLabel = (type) => {
  const labels = {
    uce: 'UCE',
    core_switch: 'Core SW',
    server_switch: 'Server SW',
    office_switch: 'Office SW',
    firewall: 'FW',
    ap: 'AP',
    wlc: 'WLC',
    router: 'Router',
    pa: 'PA',
    ftd: 'FTD',
    other: 'Other'
  }
  return labels[type] || type
}

const typeStatus = (type) => {
  const unreachable = deviceByType(type, 'unreachable')
  const maintenance = deviceByType(type, 'maintenance')
  if (unreachable > 0) return 'unreachable'
  if (maintenance > 0) return 'maintenance'
  return 'reachable'
}

const backupCoverage = computed(() => {
  const total = stats.value.devices?.total || 0
  const backedUp = stats.value.backups?.backed_up_devices || 0
  return total > 0 ? Math.round((backedUp / total) * 100) : 0
})

const recentConfigChanges = computed(() => recentBackups.value.filter(b => b.has_change).length)

const devicesWithIssues = computed(() => {
  return Object.entries(stats.value.devices_by_type || {})
    .filter(([type, data]) => data.unreachable > 0)
    .map(([type]) => type)
})

const topIssueDevice = computed(() => {
  if (faultDeviceList.value.length > 0) return faultDeviceList.value[0].device_name
  if (devicesWithIssues.value.length > 0) return typeLabel(devicesWithIssues.value[0])
  return '—'
})

const monthlyLaborCost = computed(() => stats.value.costs?.month_labor || 0)

const costTrendMax = computed(() => {
  const allValues = [...(costTrend.value.parts || []), ...(costTrend.value.labor || [])]
  return Math.max(...allValues, 1)
})

const alerts = computed(() => realAlerts.value)

const alertCount = computed(() => alerts.value.filter(a => a.severity === 'warn' || a.severity === 'danger').length)

const activityFeed = computed(() => {
  const items = []
  recentBackups.value.slice(0, 4).forEach(b => {
    items.push({
      type: 'backup',
      text: `${t('dashConfigBackups')}: ${b.device_name} — ${b.has_change ? t('dashModified') : t('dashClean')}`,
      time: formatDate(b.backup_time),
      link: '/backups'
    })
  })
  if (stats.value.faults?.count_30days > 0) {
    items.push({
      type: 'fault',
      text: `${stats.value.faults.count_30days} ${t('dashFaultEvents')} (${t('dashDays30')})`,
      time: dayjs().format('MM-DD HH:mm'),
      link: '/faults'
    })
  }
  if (stats.value.maintenance?.completed > 0) {
    items.push({
      type: 'maintenance',
      text: `${stats.value.maintenance.completed} ${t('dashMaintenanceCompleted')}`,
      time: dayjs().format('MM-DD HH:mm'),
      link: '/maintenance'
    })
  }
  return items.slice(0, 8)
})

const formatCost = (val) => val.toLocaleString()
const formatDate = (dateStr) => dayjs(dateStr).format('MM-DD HH:mm')

const navigateTo = (path) => router.push(path)

const loadAlerts = async () => {
  try {
    const res = await getAlerts()
    realAlerts.value = res.data || []
  } catch (e) {
    console.error('Failed to load alerts:', e)
    realAlerts.value = []
  }
}

const loadFaultDeviceList = async (force = false) => {
  try {
    const res = await cachedRequest(
      () => fetch('/api/dashboard/top-fault-devices?days=30&limit=5').then(r => r.json()),
      'dashboardTopFaults',
      {},
      { forceRefresh: force }
    )
    faultDeviceList.value = res || []
  } catch (err) {
    console.error('Failed to load top fault devices:', err)
    faultDeviceList.value = []
  }
}

const loadData = async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getDashboardSummary(),
      'dashboard',
      {},
      { forceRefresh: force }
    )
    stats.value = data
    recentBackups.value = data.backups?.recent || []
    nextTick(() => {
      initFaultLineChart()
      updateFaultChart()
    })
    try {
      const trendRes = await cachedRequest(
        () => fetch('/api/dashboard/cost-trend?months=6').then(r => r.json()),
        'dashboardCostTrend',
        {},
        { forceRefresh: force }
      )
      costTrend.value = trendRes
    } catch (err) {
      console.error('Failed to load cost trend:', err)
    }
    await loadFaultDeviceList(force)
    loadAlerts()
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
      { name: t('dashCritical'), type: 'line', stack: 'Total', smooth: true, symbol: 'circle', symbolSize: 4, showSymbol: false, itemStyle: { color: '#d63031' }, lineStyle: { width: 2.5 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(214,48,49,0.35)' }, { offset: 1, color: 'rgba(214,48,49,0.02)' }] } }, data: [] },
      { name: t('dashMajor'), type: 'line', stack: 'Total', smooth: true, symbol: 'circle', symbolSize: 4, showSymbol: false, itemStyle: { color: '#e17055' }, lineStyle: { width: 2.5 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(225,112,85,0.3)' }, { offset: 1, color: 'rgba(225,112,85,0.02)' }] } }, data: [] },
      { name: t('dashMinor'), type: 'line', stack: 'Total', smooth: true, symbol: 'circle', symbolSize: 4, showSymbol: false, itemStyle: { color: '#0984e3' }, lineStyle: { width: 2.5 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(9,132,227,0.25)' }, { offset: 1, color: 'rgba(9,132,227,0.02)' }] } }, data: [] },
      { name: t('dashWarning'), type: 'line', stack: 'Total', smooth: true, symbol: 'circle', symbolSize: 4, showSymbol: false, itemStyle: { color: '#636e72' }, lineStyle: { width: 2 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(99,110,114,0.15)' }, { offset: 1, color: 'rgba(99,110,114,0.02)' }] } }, data: [] }
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
  loadData()
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
/* 继承 Dashboard.vue 的样式 */
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

/* 复用 Dashboard.vue 中 kpi/charts/activity 的样式 */
.kpi-section,
.charts-section,
.activity-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* 复用其他样式... (需要从 Dashboard.vue 复制完整样式) */
</style>
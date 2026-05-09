<template>
  <div class="dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-left">
        <div class="logo-section">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"/>
            </svg>
          </div>
          <div class="logo-text">
            <span class="title">{{ t('brandName') }}</span>
            <span class="subtitle">{{ t('brandSubtitle') }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <div class="live-indicator">
          <span class="pulse"></span>
          <span class="label">{{ t('statusLive') }}</span>
        </div>
        <span class="timestamp">{{ currentTime }}</span>
        <button class="btn-refresh" @click="refreshData" :disabled="loading">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 11-2.64-6.36"/>
            <path d="M21 3v6h-6"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- Network Status Overview -->
    <section class="network-overview">
      <div class="overview-grid">
        <!-- Device Status -->
        <div class="status-card clickable" @click="navigateTo('/devices')">
          <div class="card-header">
            <div class="card-icon devices">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
              </svg>
            </div>
            <span class="card-label">{{ t('dashNetworkDevices') }}</span>
          </div>
          <div class="card-body">
            <div class="metric-main">
              <span class="metric-value">{{ stats.devices?.total || 0 }}</span>
              <span class="metric-unit">{{ t('dashNodes') }}</span>
            </div>
            <div class="metric-bars">
              <div class="bar-item">
                <span class="bar-label">{{ t('dashOnline') }}</span>
                <div class="bar-track">
                  <div class="bar-fill online" :style="{ width: onlinePercent + '%' }"></div>
                </div>
                <span class="bar-value">{{ stats.devices?.online || 0 }}</span>
              </div>
              <div class="bar-item">
                <span class="bar-label">{{ t('dashOffline') }}</span>
                <div class="bar-track">
                  <div class="bar-fill offline" :style="{ width: offlinePercent + '%' }"></div>
                </div>
                <span class="bar-value">{{ stats.devices?.offline || 0 }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Fault Status -->
        <div class="status-card clickable" @click="navigateTo('/faults')">
          <div class="card-header">
            <div class="card-icon faults">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 9v4M12 17h.01"/>
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.47a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
            </div>
            <span class="card-label">{{ t('dashFaultEvents') }}</span>
          </div>
          <div class="card-body">
            <div class="metric-main">
              <span class="metric-value danger">{{ stats.faults?.count_30days || 0 }}</span>
              <span class="metric-unit">{{ t('dashEvents') }}</span>
            </div>
            <div class="severity-grid">
              <div class="severity-item critical">
                <span class="severity-dot"></span>
                <span class="severity-count">{{ stats.faults?.critical_count || 0 }}</span>
                <span class="severity-label">{{ t('dashCritical') }}</span>
              </div>
              <div class="severity-item major">
                <span class="severity-dot"></span>
                <span class="severity-count">{{ stats.faults?.major_count || 0 }}</span>
                <span class="severity-label">{{ t('dashMajor') }}</span>
              </div>
              <div class="severity-item minor">
                <span class="severity-dot"></span>
                <span class="severity-count">{{ stats.faults?.minor_count || 0 }}</span>
                <span class="severity-label">{{ t('dashMinor') }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Backup Status -->
        <div class="status-card clickable" @click="navigateTo('/backups')">
          <div class="card-header">
            <div class="card-icon backups">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 3v12M12 15l4-4M12 15l-4-4"/>
                <path d="M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <span class="card-label">{{ t('dashConfigBackups') }}</span>
          </div>
          <div class="card-body">
            <div class="metric-main">
              <span class="metric-value success">{{ recentBackups.length || 0 }}</span>
              <span class="metric-unit">{{ t('dashRecent') }}</span>
            </div>
            <div class="backup-status">
              <div class="status-row">
                <span class="status-indicator success"></span>
                <span class="status-text">{{ t('dashBackupActive') }}</span>
              </div>
              <div class="status-row">
                <span class="status-indicator success"></span>
                <span class="status-text">{{ t('dashLastRun') }}: {{ lastBackupTime }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Cost Overview -->
        <div class="status-card clickable" @click="navigateTo('/maintenance')">
          <div class="card-header">
            <div class="card-icon cost">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
              </svg>
            </div>
            <span class="card-label">{{ t('dashMonthlyOpEx') }}</span>
          </div>
          <div class="card-body">
            <div class="metric-main">
              <span class="metric-value">¥{{ formatCost(stats.costs?.month_total || 0) }}</span>
            </div>
            <div class="cost-breakdown">
              <div class="cost-item">
                <span class="cost-label">{{ t('dashHardware') }}</span>
                <span class="cost-amount">¥{{ formatCost(stats.costs?.month_maintenance || 0) }}</span>
              </div>
              <div class="cost-item">
                <span class="cost-label">{{ t('dashLabor') }}</span>
                <span class="cost-amount">¥{{ formatCost((stats.costs?.month_total || 0) - (stats.costs?.month_maintenance || 0)) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Maintenance Tasks -->
        <div class="status-card clickable" @click="navigateTo('/planned-maintenance')">
          <div class="card-header">
            <div class="card-icon maintenance">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
              </svg>
            </div>
            <span class="card-label">{{ t('dashMaintenance') }}</span>
          </div>
          <div class="card-body">
            <div class="metric-main">
              <span class="metric-value warning">{{ stats.maintenance?.in_progress || 0 }}</span>
              <span class="metric-unit">{{ t('dashMaintenanceInProgress') }}</span>
            </div>
            <div class="inventory-stats">
              <div class="inventory-row">
                <span class="inventory-label">{{ t('dashMaintenancePending') }}</span>
                <span class="inventory-value">{{ stats.maintenance?.pending || 0 }}</span>
              </div>
              <div class="inventory-row">
                <span class="inventory-label">{{ t('dashMaintenanceCompleted') }}</span>
                <span class="inventory-value">{{ stats.maintenance?.completed || 0 }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Spare Inventory -->
        <div class="status-card clickable" @click="navigateTo('/spare-parts')">
          <div class="card-header">
            <div class="card-icon inventory">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/>
              </svg>
            </div>
            <span class="card-label">{{ t('dashSpareInventory') }}</span>
          </div>
          <div class="card-body">
            <div class="metric-main">
              <span class="metric-value">{{ stats.spare_parts?.total_models || 0 }}</span>
              <span class="metric-unit">{{ t('dashSpareModels') }}</span>
            </div>
            <div class="inventory-stats">
              <div class="inventory-row">
                <span class="inventory-label">{{ t('dashSpareTotalQty') }}</span>
                <span class="inventory-value">{{ stats.spare_parts?.total_quantity || 0 }}</span>
              </div>
              <div class="inventory-row">
                <span class="inventory-label">{{ t('dashSpareLowStock') }}</span>
                <span class="inventory-value warning">{{ stats.spare_parts?.low_stock_count || 0 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Charts Section -->
    <section class="charts-section">
      <div class="charts-grid">
        <!-- Device Topology Chart -->
        <div class="chart-panel">
          <div class="panel-header">
            <div class="panel-title-group">
              <span class="panel-icon">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="6" cy="6" r="3"/>
                  <circle cx="18" cy="6" r="3"/>
                  <circle cx="6" cy="18" r="3"/>
                  <circle cx="18" cy="18" r="3"/>
                  <path d="M6 9v6M9 6h6M9 18h6M18 9v6"/>
                </svg>
              </span>
              <h3 class="panel-title">{{ t('dashTopologyStatus') }}</h3>
            </div>
            <button class="link-btn" @click="navigateTo('/devices')">
              {{ t('dashViewAll') }}
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </button>
          </div>
          <div class="panel-body">
            <div class="topology-chart">
              <div ref="devicePieChart" class="pie-container"></div>
              <div class="status-legend">
                <div class="legend-card" @click="highlightPieSegment('online')" :class="{ active: selectedStatus === 'online' }">
                  <div class="legend-header">
                    <span class="legend-dot online"></span>
                    <span class="legend-name">{{ t('statusOnline') }}</span>
                  </div>
                  <div class="legend-stats">
                    <span class="legend-count">{{ stats.devices?.online || 0 }}</span>
                    <span class="legend-rate">{{ onlinePercent }}%</span>
                  </div>
                </div>
                <div class="legend-card" @click="highlightPieSegment('offline')" :class="{ active: selectedStatus === 'offline' }">
                  <div class="legend-header">
                    <span class="legend-dot offline"></span>
                    <span class="legend-name">{{ t('statusOffline') }}</span>
                  </div>
                  <div class="legend-stats">
                    <span class="legend-count">{{ stats.devices?.offline || 0 }}</span>
                    <span class="legend-rate">{{ offlinePercent }}%</span>
                  </div>
                </div>
                <div class="legend-card" @click="highlightPieSegment('maintenance')" :class="{ active: selectedStatus === 'maintenance' }">
                  <div class="legend-header">
                    <span class="legend-dot maintenance"></span>
                    <span class="legend-name">{{ t('statusMaintenance') }}</span>
                  </div>
                  <div class="legend-stats">
                    <span class="legend-count">{{ stats.devices?.maintenance || 0 }}</span>
                    <span class="legend-rate">{{ maintenancePercent }}%</span>
                  </div>
                </div>
                <div class="legend-card" @click="highlightPieSegment('retired')" :class="{ active: selectedStatus === 'retired' }">
                  <div class="legend-header">
                    <span class="legend-dot retired"></span>
                    <span class="legend-name">{{ t('statusRetired') }}</span>
                  </div>
                  <div class="legend-stats">
                    <span class="legend-count">{{ stats.devices?.retired || 0 }}</span>
                    <span class="legend-rate">{{ retiredPercent }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Fault Timeline Chart -->
        <div class="chart-panel">
          <div class="panel-header">
            <div class="panel-title-group">
              <span class="panel-icon">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M3 3v18h18"/>
                  <path d="M7 16l4-8 4 6 5-10"/>
                </svg>
              </span>
              <h3 class="panel-title">{{ t('dashFaultTimeline') }}</h3>
            </div>
            <div class="panel-controls">
              <div class="total-badge">
                <span class="badge-icon">
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 9v4M12 17h.01"/>
                  </svg>
                </span>
                <span class="badge-value">{{ faultTotal }}</span>
                <span class="badge-unit">{{ t('dashTotal') }}</span>
              </div>
              <select class="time-selector" v-model="faultTimeRange" @change="updateFaultChart">
                <option value="7d">{{ t('dashDays7') }}</option>
                <option value="30d">{{ t('dashDays30') }}</option>
                <option value="3m">{{ t('dashMonths3') }}</option>
                <option value="1y">{{ t('dashYears1') }}</option>
                <option value="custom">{{ t('dashCustom') }}</option>
              </select>
              <input
                type="date"
                class="date-input"
                v-if="faultTimeRange === 'custom'"
                v-model="customStartDate"
                @change="updateFaultChart"
              />
              <span class="date-separator" v-if="faultTimeRange === 'custom'">~</span>
              <input
                type="date"
                class="date-input"
                v-if="faultTimeRange === 'custom'"
                v-model="customEndDate"
                @change="updateFaultChart"
              />
            </div>
          </div>
          <div class="panel-body">
            <div ref="faultLineChart" class="line-chart-container"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- Data Tables Section -->
    <section class="data-section">
      <div class="data-grid">
        <!-- Recent Backups -->
        <div class="data-panel">
          <div class="panel-header">
            <div class="panel-title-group">
              <span class="panel-icon success">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M9 12l2 2 4-4"/>
                  <circle cx="12" cy="12" r="10"/>
                </svg>
              </span>
              <h3 class="panel-title">{{ t('dashRecentBackups') }}</h3>
            </div>
            <button class="link-btn" @click="navigateTo('/backups')">
              {{ t('dashViewAll') }}
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </button>
          </div>
          <div class="panel-body">
            <div class="data-table">
              <div class="table-header">
                <span class="col device">{{ t('menuDevices') }}</span>
                <span class="col time">{{ t('dashTimestamp') }}</span>
                <span class="col change">{{ t('dashChange') }}</span>
                <span class="col action">{{ t('dashAction') }}</span>
              </div>
              <div class="table-body">
                <div class="table-row" v-for="b in recentBackups.slice(0, 6)" :key="b.id || b.backup_time" @click="viewBackup(b)">
                  <span class="col device">
                    <span class="device-icon">
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="2" y="3" width="20" height="14" rx="2"/>
                      </svg>
                    </span>
                    <span class="device-name">{{ b.device_name }}</span>
                  </span>
                  <span class="col time">{{ formatDate(b.backup_time) }}</span>
                  <span class="col change">
                    <span :class="['change-tag', b.has_change ? 'modified' : 'clean']">
                      {{ b.has_change ? t('dashModified') : t('dashClean') }}
                    </span>
                  </span>
                  <span class="col action">
                    <span class="action-btn">{{ t('dashView') }}</span>
                  </span>
                </div>
                <div class="table-empty" v-if="recentBackups.length === 0">
                  {{ t('dashNoRecords') }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- System Alerts -->
        <div class="data-panel alerts">
          <div class="panel-header">
            <div class="panel-title-group">
              <span class="panel-icon warn">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 9v4M12 17h.01"/>
                  <circle cx="12" cy="12" r="10"/>
                </svg>
              </span>
              <h3 class="panel-title">{{ t('dashSystemAlerts') }}</h3>
            </div>
            <span class="alert-badge" v-if="alertCount">{{ alertCount }}</span>
          </div>
          <div class="panel-body">
            <div class="alert-list">
              <div class="alert-item" v-for="(alert, i) in alerts" :key="i">
                <span :class="['alert-marker', alert.severity]"></span>
                <div class="alert-content">
                  <span class="alert-title">{{ alert.title }}</span>
                  <span class="alert-summary">{{ alert.summary }}</span>
                </div>
                <span class="alert-time">{{ alert.time }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer Stats -->
    <footer class="dashboard-footer">
      <div class="footer-stats">
        <div class="stat-item">
          <span class="stat-label">{{ t('dashUptime') }}</span>
          <span class="stat-value">99.97%</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ t('dashApiResponse') }}</span>
          <span class="stat-value">42ms</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ t('dashActiveSessions') }}</span>
          <span class="stat-value">3</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">{{ t('dashLastSync') }}</span>
          <span class="stat-value">{{ currentTime }}</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, onUnmounted } from 'vue'
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
const devicePieChart = ref(null)
const faultLineChart = ref(null)
const faultTimeRange = ref('30d')
const customStartDate = ref(dayjs().subtract(30, 'day').format('YYYY-MM-DD'))
const customEndDate = ref(dayjs().format('YYYY-MM-DD'))
const faultChartInstance = ref(null)
const deviceChartInstance = ref(null)
const faultTotal = ref(0)
const faultData = ref({ labels: [], by_severity: {} })
const selectedLegends = ref([t('dashCritical'), t('dashMajor'), t('dashMinor'), t('dashWarning')])
const selectedStatus = ref(null)

const currentTime = ref(dayjs().format('HH:mm:ss'))
const lastBackupTime = computed(() => {
  if (recentBackups.value.length > 0) {
    return formatDate(recentBackups.value[0].backup_time)
  }
  return 'N/A'
})

const onlinePercent = computed(() => {
  const total = stats.value.devices?.total || 0
  if (total === 0) return 0
  return Math.round((stats.value.devices?.online || 0) / total * 100)
})

const offlinePercent = computed(() => {
  const total = stats.value.devices?.total || 0
  if (total === 0) return 0
  return Math.round((stats.value.devices?.offline || 0) / total * 100)
})

const maintenancePercent = computed(() => {
  const total = stats.value.devices?.total || 0
  if (total === 0) return 0
  return Math.round((stats.value.devices?.maintenance || 0) / total * 100)
})

const retiredPercent = computed(() => {
  const total = stats.value.devices?.total || 0
  if (total === 0) return 0
  return Math.round((stats.value.devices?.retired || 0) / total * 100)
})

const alerts = computed(() => [
  { severity: 'warn', title: t('dashAlertBackupTitle'), summary: t('dashAlertBackupSummary'), time: '10m' },
  { severity: 'info', title: t('dashAlertMaintenanceTitle'), summary: t('dashAlertMaintenanceSummary'), time: '2h' },
  { severity: 'success', title: t('dashAlertHealthyTitle'), summary: t('dashAlertHealthySummary'), time: '1d' }
])

const alertCount = computed(() => alerts.value.filter(a => a.severity === 'warn' || a.severity === 'danger').length)

const formatCost = (val) => val.toLocaleString()
const formatDate = (dateStr) => dayjs(dateStr).format('MM-DD HH:mm')

const navigateTo = (path) => router.push(path)

const refreshData = async () => {
  loading.value = true
  await loadDashboardData()
  loading.value = false
  ElMessage.success(t('msgDataRefreshed'))
}

const loadDashboardData = async () => {
  try {
    const data = await getDashboardSummary()
    stats.value = data
    recentBackups.value = data.backups?.recent || []

    nextTick(() => {
      initDevicePieChart(data.devices)
      initFaultLineChart()
      updateFaultChart()
    })
  } catch (error) {
    ElMessage.error(t('dashLoadFailed'))
  }
}

const initDevicePieChart = (devices) => {
  if (!devicePieChart.value) return
  if (deviceChartInstance.value) deviceChartInstance.value.dispose()

  deviceChartInstance.value = echarts.init(devicePieChart.value)

  const isDark = document.documentElement.classList.contains('dark')
  const bgColor = isDark ? '#1a1f26' : '#ffffff'
  const borderColor = isDark ? '#30363d' : '#e2e8f0'
  const textColor = isDark ? '#e6edf3' : '#0D1B2A'
  const total = (devices?.online || 0) + (devices?.offline || 0) + (devices?.maintenance || 0) + (devices?.retired || 0)

  // 定义颜色
  const colors = ['#00d4aa', '#6b7280', '#ffb800', isDark ? '#484f58' : '#9BAABB']

  deviceChartInstance.value.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: bgColor,
      borderColor: borderColor,
      textStyle: { color: textColor, fontFamily: 'JetBrains Mono' },
      formatter: (params) => `${params.name}: ${params.value} ${t('dashDevices')} (${total > 0 ? Math.round(params.value / total * 100) : 0}%)`
    },
    series: [{
      type: 'pie',
      radius: ['50%', '75%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: isDark ? '#21262d' : '#f8fafc',
        borderWidth: 2
      },
      label: { show: false },
      labelLine: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 5,
        itemStyle: {
          shadowBlur: 15,
          shadowOffsetX: 0,
          shadowOffsetY: 0,
          shadowColor: 'rgba(0, 212, 170, 0.4)'
        }
      },
      data: [
        { value: devices?.online || 0, name: t('statusOnline'), itemStyle: { color: colors[0] } },
        { value: devices?.offline || 0, name: t('statusOffline'), itemStyle: { color: colors[1] } },
        { value: devices?.maintenance || 0, name: t('statusMaintenance'), itemStyle: { color: colors[2] } },
        { value: devices?.retired || 0, name: t('statusRetired'), itemStyle: { color: colors[3] } }
      ]
    }],
    // 添加中心文字图形
    graphic: [{
      type: 'group',
      left: 'center',
      top: 'center',
      children: [
        {
          type: 'text',
          z: 100,
          left: 'center',
          top: '-15',
          style: {
            fill: textColor,
            text: total.toString(),
            font: 'bold 32px JetBrains Mono',
            textAlign: 'center'
          }
        },
        {
          type: 'text',
          z: 100,
          left: 'center',
          top: '15',
          style: {
            fill: isDark ? '#8b949e' : '#6B7A8D',
            text: t('dashDevices'),
            font: '13px Geist',
            textAlign: 'center'
          }
        }
      ]
    }]
  })
}

const highlightPieSegment = (status) => {
  if (!deviceChartInstance.value) return

  // 状态名称映射（使用翻译后的名称）
  const nameMap = {
    'online': t('statusOnline'),
    'offline': t('statusOffline'),
    'maintenance': t('statusMaintenance'),
    'retired': t('statusRetired')
  }

  // 如果点击同一个状态，取消高亮
  if (selectedStatus.value === status) {
    selectedStatus.value = null
    deviceChartInstance.value.dispatchAction({
      type: 'downplay',
      seriesIndex: 0
    })
    return
  }

  selectedStatus.value = status

  // 先取消所有高亮，再高亮当前选中的
  deviceChartInstance.value.dispatchAction({
    type: 'downplay',
    seriesIndex: 0
  })
  deviceChartInstance.value.dispatchAction({
    type: 'highlight',
    seriesIndex: 0,
    name: nameMap[status]
  })
}

const initFaultLineChart = () => {
  if (!faultLineChart.value) return
  if (faultChartInstance.value) faultChartInstance.value.dispose()

  faultChartInstance.value = echarts.init(faultLineChart.value)

  const isDark = document.documentElement.classList.contains('dark')
  const bgColor = isDark ? '#1a1f26' : '#ffffff'
  const borderColor = isDark ? '#30363d' : '#e2e8f0'
  const textColor = isDark ? '#e6edf3' : '#0D1B2A'
  const axisColor = isDark ? '#8b949e' : '#6B7A8D'
  const gridColor = isDark ? '#30363d' : '#E2E8F2'
  const splitColor = isDark ? '#21262d' : '#f1f5f9'

  faultChartInstance.value.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: bgColor,
      borderColor: borderColor,
      textStyle: { color: textColor, fontFamily: 'JetBrains Mono' },
      axisPointer: {
        type: 'cross',
        lineStyle: { color: gridColor }
      }
    },
    legend: {
      data: [t('dashCritical'), t('dashMajor'), t('dashMinor'), t('dashWarning')],
      bottom: 0,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: axisColor, fontFamily: 'Geist', fontSize: 12 }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '5%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [],
      axisLine: { lineStyle: { color: gridColor } },
      axisTick: { show: false },
      axisLabel: { color: axisColor, fontFamily: 'JetBrains Mono', fontSize: 10 },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: axisColor, fontFamily: 'JetBrains Mono', fontSize: 10 },
      splitLine: { lineStyle: { color: splitColor, type: 'dashed' } }
    },
    series: [
      {
        name: t('dashCritical'),
        type: 'line',
        stack: 'Total',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        itemStyle: { color: '#ff4757' },
        lineStyle: { width: 2, color: '#ff4757' },
        areaStyle: { color: 'rgba(255, 71, 87, 0.1)' },
        data: []
      },
      {
        name: t('dashMajor'),
        type: 'line',
        stack: 'Total',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        itemStyle: { color: '#ffb800' },
        lineStyle: { width: 2, color: '#ffb800' },
        areaStyle: { color: 'rgba(255, 184, 0, 0.1)' },
        data: []
      },
      {
        name: t('dashMinor'),
        type: 'line',
        stack: 'Total',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        itemStyle: { color: '#00a8ff' },
        lineStyle: { width: 2, color: '#00a8ff' },
        areaStyle: { color: 'rgba(0, 168, 255, 0.1)' },
        data: []
      },
      {
        name: t('dashWarning'),
        type: 'line',
        stack: 'Total',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: false,
        itemStyle: { color: '#6b7280' },
        lineStyle: { width: 2, color: '#6b7280' },
        areaStyle: { color: 'rgba(107, 114, 128, 0.1)' },
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

    // 如果是自定义时间区间，添加日期参数
    if (range === 'custom' && customStartDate.value && customEndDate.value) {
      url = `/api/dashboard/fault-trend?time_range=custom&start_date=${customStartDate.value}&end_date=${customEndDate.value}`
    }

    const response = await fetch(url)
    const data = await response.json()

    faultData.value = { labels: data.labels || [], by_severity: data.by_severity || {} }

    const severityData = { critical: [], major: [], minor: [], warning: [] }
    data.labels.forEach((label) => {
      const counts = data.by_severity?.[label] || {}
      severityData.critical.push(counts.critical || 0)
      severityData.major.push(counts.major || 0)
      severityData.minor.push(counts.minor || 0)
      severityData.warning.push(counts.warning || 0)
    })

    faultChartInstance.value.setOption({
      xAxis: { data: data.labels || [] },
      series: [
        { data: severityData.critical },
        { data: severityData.major },
        { data: severityData.minor },
        { data: severityData.warning }
      ]
    })

    // Calculate total
    let total = 0
    data.labels.forEach((label) => {
      const counts = data.by_severity?.[label] || {}
      total += (counts.critical || 0) + (counts.major || 0) + (counts.minor || 0) + (counts.warning || 0)
    })
    faultTotal.value = total
  } catch (error) {
    ElMessage.error(t('dashFaultTrendFailed'))
  }
}

const viewBackup = (b) => {
  // 跳转到设备详情页面，通过设备名称查询
  router.push({ path: '/devices', query: { name: b.device_name } })
}

const handleResize = () => {
  deviceChartInstance.value?.resize()
  faultChartInstance.value?.resize()
}

const handleThemeChange = () => {
  // 重新初始化图表以应用新主题颜色
  if (stats.value.devices) {
    initDevicePieChart(stats.value.devices)
  }
  initFaultLineChart()
  updateFaultChart()
}

onMounted(() => {
  loadDashboardData()
  window.addEventListener('resize', handleResize)
  window.addEventListener('theme-change', handleThemeChange)

  // Update time every second
  setInterval(() => {
    currentTime.value = dayjs().format('HH:mm:ss')
  }, 1000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('theme-change', handleThemeChange)
  deviceChartInstance.value?.dispose()
  faultChartInstance.value?.dispose()
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-body);
}

/* ===== Header ===== */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-default);
}

.header-left {
  display: flex;
  align-items: center;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 8px;
}

.logo-icon svg {
  width: 20px;
  height: 20px;
  color: #fff;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-text .title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.logo-text .subtitle {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.05em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--success-bg);
  border: 1px solid var(--accent-primary);
  border-radius: 4px;
}

.live-indicator .pulse {
  width: 8px;
  height: 8px;
  background: var(--accent-primary);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.live-indicator .label {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-primary);
}

.timestamp {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--text-secondary);
}

.btn-refresh {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== Network Overview ===== */
.network-overview {
  padding: 20px 24px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
}

.status-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
  transition: all 0.2s;
}

.status-card.clickable {
  cursor: pointer;
}

.status-card.clickable:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 20px var(--glow-primary);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.card-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--bg-tertiary);
}

.card-icon svg {
  width: 16px;
  height: 16px;
}

.card-icon.devices { background: rgba(0, 168, 255, 0.15); color: var(--accent-secondary); }
.card-icon.faults { background: rgba(255, 71, 87, 0.15); color: var(--accent-danger); }
.card-icon.backups { background: rgba(0, 212, 170, 0.15); color: var(--accent-primary); }
.card-icon.cost { background: rgba(255, 184, 0, 0.15); color: var(--accent-warning); }
.card-icon.maintenance { background: rgba(138, 43, 226, 0.15); color: #8a2be2; }
.card-icon.inventory { background: rgba(46, 139, 87, 0.15); color: #2e8b57; }

.card-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.metric-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.metric-value.success { color: var(--accent-primary); }
.metric-value.danger { color: var(--accent-danger); }

.metric-unit {
  font-size: 12px;
  color: var(--text-tertiary);
}

.metric-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 11px;
  color: var(--text-tertiary);
  width: 40px;
}

.bar-track {
  flex: 1;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s;
}

.bar-fill.online { background: var(--accent-primary); }
.bar-fill.offline { background: var(--accent-danger); }

.bar-value {
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--text-secondary);
  width: 20px;
  text-align: right;
}

.severity-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.severity-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.severity-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.severity-item.critical .severity-dot { background: var(--severity-critical); }
.severity-item.major .severity-dot { background: var(--severity-major); }
.severity-item.minor .severity-dot { background: var(--severity-minor); }

.severity-count {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.severity-label {
  font-size: 10px;
  color: var(--text-tertiary);
}

.backup-status {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-indicator.success { background: var(--accent-primary); }
.status-indicator.warn { background: var(--accent-warning); }

.status-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.cost-breakdown {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cost-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
}

.cost-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.cost-amount {
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--text-secondary);
}

/* ===== Charts Section ===== */
.charts-section {
  padding: 0 24px 20px;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-icon {
  color: var(--text-tertiary);
}

.panel-icon.success { color: var(--accent-primary); }
.panel-icon.warn { color: var(--accent-warning); }

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.link-btn:hover {
  color: var(--accent-primary);
}

.total-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid rgba(255, 71, 87, 0.2);
  border-radius: 4px;
}

.badge-icon {
  color: var(--accent-danger);
}

.badge-value {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-danger);
}

.badge-unit {
  font-size: 10px;
  color: var(--text-tertiary);
}

.time-selector {
  padding: 4px 8px;
  font-size: 12px;
  font-family: var(--font-body);
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  cursor: pointer;
}

.date-input {
  padding: 4px 8px;
  font-size: 12px;
  font-family: var(--font-display);
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  width: 120px;
}

.date-separator {
  color: var(--text-tertiary);
  font-size: 12px;
}

.panel-body {
  padding: 16px;
}

.topology-chart {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 8px 0;
}

.pie-container {
  width: 180px;
  height: 180px;
}

.status-legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  flex: 1;
}

.legend-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.legend-card:hover {
  background: var(--bg-hover);
  border-color: var(--border-default);
}

.legend-card.active {
  border-color: var(--accent-primary);
  background: var(--bg-hover);
  box-shadow: 0 0 8px var(--glow-primary);
}

.legend-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.online { background: #00d4aa; }
.legend-dot.offline { background: #6b7280; }
.legend-dot.maintenance { background: #ffb800; }
.legend-dot.retired { background: var(--text-muted); }

.legend-name {
  font-size: 12px;
  color: var(--text-tertiary);
}

.legend-stats {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.legend-count {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.legend-rate {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--accent-primary);
}

.line-chart-container {
  height: 200px;
}

/* ===== Data Section ===== */
.data-section {
  padding: 0 24px 20px;
}

.data-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.data-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
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
  color: #fff;
  background: var(--accent-danger);
  border-radius: 4px;
}

.data-table {
  display: flex;
  flex-direction: column;
}

.table-header {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.table-header .col {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
}

.table-body {
  display: flex;
  flex-direction: column;
}

.table-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.2s;
}

.table-row:hover {
  background: var(--bg-hover);
}

.table-row:last-child {
  border-bottom: none;
}

.col {
  display: flex;
  align-items: center;
}

.col.device {
  flex: 1;
  gap: 8px;
}

.device-icon {
  color: var(--accent-secondary);
}

.device-name {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--text-primary);
}

.col.time {
  width: 100px;
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--text-secondary);
}

.col.change {
  width: 80px;
}

.change-tag {
  display: inline-flex;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
}

.change-tag.modified {
  background: rgba(255, 184, 0, 0.15);
  color: var(--accent-warning);
}

.change-tag.clean {
  background: rgba(0, 212, 170, 0.15);
  color: var(--accent-primary);
}

.col.action {
  width: 60px;
  justify-content: flex-end;
}

.action-btn {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-secondary);
}

.table-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-tertiary);
}

.alert-list {
  display: flex;
  flex-direction: column;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  transition: background 0.2s;
}

.alert-item:last-child {
  border-bottom: none;
}

.alert-item:hover {
  background: var(--bg-hover);
}

.alert-marker {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
}

.alert-marker.danger { background: var(--severity-critical); }
.alert-marker.warn { background: var(--severity-major); }
.alert-marker.info { background: var(--severity-minor); }
.alert-marker.success { background: var(--status-active); }

.alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.alert-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.alert-summary {
  font-size: 12px;
  color: var(--text-secondary);
}

.alert-time {
  font-family: var(--font-display);
  font-size: 11px;
  color: var(--text-tertiary);
}

/* ===== Footer ===== */
.dashboard-footer {
  padding: 12px 24px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-default);
}

.footer-stats {
  display: flex;
  justify-content: space-between;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-primary);
}

/* ===== Responsive ===== */
@media (max-width: 1200px) {
  .overview-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1024px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-grid,
  .data-grid {
    grid-template-columns: 1fr;
  }

  .topology-chart {
    flex-direction: column;
    align-items: center;
  }

  .status-legend {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: center;
  }
}

@media (max-width: 640px) {
  .dashboard-header {
    flex-direction: column;
    gap: 12px;
  }

  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .footer-stats {
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
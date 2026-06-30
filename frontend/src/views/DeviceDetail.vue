<template>
  <div class="device-detail-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">{{ device?.name || t('deviceDetail') }}</h1>
        <el-tag v-if="device" :type="getStatusType(device.status)" size="large">
          {{ getStatusText(device.status) }}
        </el-tag>
        <el-select v-if="device" :model-value="device.monitor_tier || 'normal'" @change="setMonitorTier" size="small" style="width: 132px; margin-left: 8px" placeholder="监控分级">
          <el-option label="核心 critical" value="critical" />
          <el-option label="普通 normal" value="normal" />
          <el-option label="低优先 low" value="low" />
        </el-select>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="showEditDialog = true">
          <el-icon><Setting /></el-icon>
          {{ t('deviceEdit') }}
        </el-button>
      </div>
    </div>

    <!-- 主体：设备健康仪表盘 -->
    <div class="device-dashboard">
      <!-- 设备状态卡片 -->
      <div class="status-card" :class="healthStatusClass" v-loading="loading">
        <!-- 状态头部：一目了然的健康状态 -->
        <div class="status-header">
          <div class="status-indicator">
            <div class="status-dot" :class="healthDotClass"></div>
            <span class="status-label">{{ healthStatusLabel }}</span>
          </div>
          <div class="device-identity">
            <span class="device-ip-large">{{ device?.ip || '--' }}</span>
            <span class="device-name-sub">{{ device?.name || '' }}</span>
          </div>
          <div class="header-actions">
            <el-button class="action-btn-refresh" @click="refreshMetrics" :loading="metricsLoading" circle>
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button class="action-btn-edit" @click="showEditDialog = true" circle>
              <el-icon><Setting /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- 核心指标：四个关键数据 -->
        <div class="core-metrics">
          <div class="metric-block">
            <div class="metric-ring" :style="{ borderColor: getMetricColor(metricsData.cpu?.value) }">
              <span class="metric-number" :style="{ color: getMetricColor(metricsData.cpu?.value) }">{{ metricsData.cpu?.value || '--' }}</span>
              <span class="metric-unit">%</span>
            </div>
            <span class="metric-name">{{ t('metricCpu') }}</span>
            <span class="metric-status" :class="getMetricStatus(metricsData.cpu?.value)">{{ getMetricStatusText(metricsData.cpu?.value) }}</span>
          </div>
          <div class="metric-block">
            <div class="metric-ring" :style="{ borderColor: getMetricColor(metricsData.memory?.used_percent) }">
              <span class="metric-number" :style="{ color: getMetricColor(metricsData.memory?.used_percent) }">{{ metricsData.memory?.used_percent || '--' }}</span>
              <span class="metric-unit">%</span>
            </div>
            <span class="metric-name">{{ t('metricMemory') }}</span>
            <span class="metric-status" :class="getMetricStatus(metricsData.memory?.used_percent)">{{ getMetricStatusText(metricsData.memory?.used_percent) }}</span>
          </div>
          <div class="metric-block">
            <div class="metric-ring" :style="{ borderColor: getTempColor(metricsData.temperature?.value) }">
              <span class="metric-number" :style="{ color: getTempColor(metricsData.temperature?.value) }">{{ metricsData.temperature?.value || '--' }}</span>
              <span class="metric-unit">°C</span>
            </div>
            <span class="metric-name">{{ t('metricTemperature') }}</span>
            <span class="metric-status" :class="getTempStatus(metricsData.temperature?.value)">{{ getTempStatusText(metricsData.temperature?.value) }}</span>
          </div>
          <div class="metric-block uptime-block">
            <div class="uptime-display">
              <el-icon class="uptime-icon"><Timer /></el-icon>
              <span class="uptime-value">{{ metricsData.uptime?.uptime_days || '--' }}</span>
              <span class="uptime-unit">{{ t('metricDays') }}</span>
            </div>
            <span class="metric-name">{{ t('metricUptime') }}</span>
            <span class="metric-status uptime-detail">{{ metricsData.uptime?.uptime_hours || 0 }}h</span>
          </div>
        </div>

        <!-- 网络健康状态 -->
        <div class="network-health">
          <div class="health-item" :class="{ 'health-ok': metricsData.interfaces?.down === 0 }">
            <el-icon><Connection /></el-icon>
            <span class="health-value">{{ metricsData.interfaces?.up || '--' }}/{{ metricsData.interfaces?.total || '--' }}</span>
            <span class="health-label">{{ t('metricPortsOnline') }}</span>
            <el-tag v-if="metricsData.interfaces?.down > 0" type="danger" size="small" effect="dark" class="health-alert">
              {{ metricsData.interfaces?.down }} {{ t('metricDown') }}
            </el-tag>
            <el-tag v-else type="success" size="small" effect="dark" class="health-ok-tag">{{ t('metricAllOk') }}</el-tag>
          </div>
          <div class="health-item" :class="{ 'health-ok': !metricsData.errors?.has_errors }">
            <el-icon><WarningFilled /></el-icon>
            <span class="health-value">{{ formatErrorCount(metricsData.errors?.total_errors) }}</span>
            <span class="health-label">{{ t('metricErrors') }}</span>
            <el-tag v-if="metricsData.errors?.has_errors" type="warning" size="small" effect="dark" class="health-alert">{{ t('metricHasIssues') }}</el-tag>
            <el-tag v-else type="success" size="small" effect="dark" class="health-ok-tag">{{ t('metricClean') }}</el-tag>
          </div>
          <div class="health-item" :class="{ 'health-ok': metricsData.uplinks?.length > 0 }">
            <el-icon><Promotion /></el-icon>
            <span class="health-value">{{ metricsData.uplinks?.length || 0 }}</span>
            <span class="health-label">{{ t('metricUplinks') }}</span>
          </div>
        </div>

        <!-- 设备基本信息（可折叠） -->
        <el-collapse class="info-collapse">
          <el-collapse-item :title="t('deviceInfoDetails')" name="info">
            <div class="info-compact-grid">
              <div class="info-row-item">
                <span class="info-key">{{ t('labelModel') }}</span>
                <span class="info-val">{{ device?.model || '--' }}</span>
              </div>
              <div class="info-row-item">
                <span class="info-key">{{ t('labelLocation') }}</span>
                <span class="info-val">{{ device?.location || '--' }}</span>
              </div>
              <div class="info-row-item">
                <span class="info-key">{{ t('deviceRole') }}</span>
                <span class="info-val">{{ getRoleText(device?.role) }}</span>
              </div>
              <div class="info-row-item">
                <span class="info-key">{{ t('deviceLastBackup') }}</span>
                <span class="info-val">{{ device?.last_backup_time ? formatDateTime(device.last_backup_time) : '--' }}</span>
              </div>
            </div>
          </el-collapse-item>
          <el-collapse-item v-if="metricsData.uplinks?.length > 0" :title="t('metricUplinkBandwidth')" name="uplinks">
            <div class="uplinks-detail">
              <div class="uplink-row" v-for="link in metricsData.uplinks" :key="link.index">
                <span class="uplink-interface">{{ link.alias || link.interface }}</span>
                <div class="uplink-util-visual">
                  <div class="uplink-bar-bg">
                    <div class="uplink-bar-fill" :style="{ width: (link.utilization || 0) + '%', background: getUtilizationColor(link.utilization) }"></div>
                  </div>
                  <span class="uplink-percent">{{ link.utilization ? link.utilization + '%' : '--' }}</span>
                </div>
                <span class="uplink-speed">{{ link.speed_mbps }}M</span>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>

        <!-- 快捷操作 -->
        <div class="quick-actions-bar">
          <el-button type="success" @click="backupNow" :icon="Download" round size="default">{{ t('deviceBackupNow') }}</el-button>
          <el-button @click="viewLatestConfig" :icon="View" round size="default">{{ t('backupViewConfig') }}</el-button>
          <el-button type="warning" @click="openFaultDialog" :icon="Warning" round size="default">{{ t('faultAddRecord') }}</el-button>
          <el-button type="danger" @click="confirmDeleteDevice" :icon="Delete" round v-if="device">{{ t('deviceDelete') }}</el-button>
        </div>
      </div>
    </div>

    <!-- Tabs 区域 -->
    <div class="tabs-wrapper">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="接口监控" name="interfaces">
          <div class="iface-toolbar">
            <el-button type="primary" size="small" :icon="Connection" @click="discoverInterfaces" :loading="ifaceDiscovering">发现接口</el-button>
            <el-button size="small" :icon="Tools" @click="discoverNeighbors" :loading="ifaceNeighborLoading">发现邻居</el-button>
            <el-button size="small" :icon="Refresh" @click="loadInterfaces(true)" :loading="ifacesLoading">刷新</el-button>
            <el-checkbox v-model="ifaceMonitoredOnly" @change="loadInterfaces(true)" style="margin-left: 10px">仅看监控接口</el-checkbox>
            <el-checkbox v-model="ifaceAutoRefresh" style="margin-left: 8px">自动刷新(30s)</el-checkbox>
            <span v-if="interfaces.length" style="margin-left: auto; font-size: 12px; color: #909399">共 {{ interfaces.length }} 口 · 在线 {{ ifaceUpCount }} · 上行 {{ ifaceUplinkCount }} · 监控 {{ ifaceMonitoredCount }}</span>
          </div>
          <el-table :data="interfaces" v-loading="ifacesLoading" size="small" border stripe row-key="if_index" @expand-change="onIfaceExpand" style="margin-top: 8px">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="iface-traffic-panel">
                  <div v-if="trafficLoading[row.if_index]" style="color: #909399; padding: 8px">加载流量中…</div>
                  <div v-else-if="(trafficData[row.if_index] || []).length" class="spark-wrap">
                    <div class="spark-line">
                      <span class="spark-tag in">入向</span>
                      <svg :viewBox="`0 0 240 40`" preserveAspectRatio="none" class="spark-svg">
                        <polyline :points="sparkPoints(trafficData[row.if_index], 'in_bps')" fill="none" stroke="#409eff" stroke-width="1.5" />
                      </svg>
                      <span class="spark-val">{{ formatBps(row.last_in_bps) }} <em>{{ row.last_in_util != null ? row.last_in_util + '%' : '' }}</em></span>
                    </div>
                    <div class="spark-line">
                      <span class="spark-tag out">出向</span>
                      <svg :viewBox="`0 0 240 40`" preserveAspectRatio="none" class="spark-svg">
                        <polyline :points="sparkPoints(trafficData[row.if_index], 'out_bps')" fill="none" stroke="#67c23a" stroke-width="1.5" />
                      </svg>
                      <span class="spark-val">{{ formatBps(row.last_out_bps) }} <em>{{ row.last_out_util != null ? row.last_out_util + '%' : '' }}</em></span>
                    </div>
                    <div class="spark-meta">最近 {{ (trafficData[row.if_index] || []).length }} 个采样 · 更新于 {{ row.last_sample_at ? formatDateTime(row.last_sample_at) : '--' }}</div>
                  </div>
                  <el-empty v-else description="暂无流量样本（需开启监控并等待下一次轮询）" :image-size="50" />
                </div>
              </template>
            </el-table-column>
            <el-table-column label="接口" min-width="150">
              <template #default="{ row }">
                <span style="font-weight: 600">{{ row.if_name || row.if_descr || ('if' + row.if_index) }}</span>
                <el-tag v-if="row.is_uplink" type="warning" size="small" effect="plain" style="margin-left: 4px">上行</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="88" align="center">
              <template #default="{ row }">
                <el-tag :type="row.oper_status === 'up' ? 'success' : (row.oper_status === 'down' ? 'danger' : 'info')" size="small" effect="dark">{{ row.oper_status || 'unknown' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="速率" width="72" align="center">
              <template #default="{ row }">{{ row.speed_mbps ? row.speed_mbps + 'M' : '--' }}</template>
            </el-table-column>
            <el-table-column label="入向" width="160">
              <template #default="{ row }">
                <div class="util-cell">
                  <div class="util-bar-bg"><div class="util-bar-fill" :style="{ width: Math.min(row.last_in_util || 0, 100) + '%', background: getUtilizationColor(row.last_in_util) }"></div></div>
                  <span class="util-text">{{ formatBps(row.last_in_bps) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="出向" width="160">
              <template #default="{ row }">
                <div class="util-cell">
                  <div class="util-bar-bg"><div class="util-bar-fill" :style="{ width: Math.min(row.last_out_util || 0, 100) + '%', background: getUtilizationColor(row.last_out_util) }"></div></div>
                  <span class="util-text">{{ formatBps(row.last_out_bps) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="错误" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ color: ((row.last_in_errors || 0) + (row.last_out_errors || 0)) > 0 ? '#f56c6c' : '#67c23a' }">{{ (row.last_in_errors || 0) + (row.last_out_errors || 0) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="对端" min-width="160">
              <template #default="{ row }">
                <span v-if="row.peer_device_name">{{ row.peer_device_name }}<span v-if="row.peer_if_name" style="color: #909399"> / {{ row.peer_if_name }}</span></span>
                <span v-else style="color: #c0c4cc">--</span>
              </template>
            </el-table-column>
            <el-table-column label="上行口" width="68" align="center">
              <template #default="{ row }"><el-switch :model-value="row.is_uplink" @change="v => toggleUplink(row, v)" size="small" /></template>
            </el-table-column>
            <el-table-column label="监控" width="60" align="center">
              <template #default="{ row }"><el-switch :model-value="row.monitored" @change="v => toggleMonitored(row, v)" size="small" /></template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!interfaces.length && !ifacesLoading" description="尚未发现接口，点击「发现接口」进行 SNMP 扫描" :image-size="60" />
        </el-tab-pane>
        <el-tab-pane :label="t('tabBackupRecords')" name="backups">
          <el-table :data="device?.recent_backups || []" style="width: 100%">
            <el-table-column prop="backup_time" :label="t('backupTime')" width="180">
              <template #default="{ row }">{{ formatDateTime(row.backup_time) }}</template>
            </el-table-column>
            <el-table-column prop="has_change" :label="t('backupConfigChange')" width="100">
              <template #default="{ row }">
                <el-tag :type="row.has_change ? 'warning' : 'success'" size="small">
                  {{ row.has_change ? t('dashModified') : t('dashClean') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="triggered_by" :label="t('backupTriggeredBy')" width="100">
              <template #default="{ row }">{{ row.triggered_by || t('backupTriggeredAuto') }}</template>
            </el-table-column>
            <el-table-column :label="t('deviceAction')" width="150">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewConfig(row.id)">{{ t('backupViewConfig') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="t('tabFaultRecords')" name="faults">
          <el-table :data="device?.recent_faults || []" style="width: 100%">
            <el-table-column prop="fault_no" :label="t('faultNo')" width="180">
              <template #default="{ row }">
                <router-link :to="`/faults/${row.id}`" class="fault-link">{{ row.fault_no }}</router-link>
              </template>
            </el-table-column>
            <el-table-column prop="severity" :label="t('faultLevel')" width="80">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small">{{ getSeverityText(row.severity) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="t('faultStatus')" width="80">
              <template #default="{ row }">
                <el-tag :type="getFaultStatusType(row.status)" size="small">{{ getFaultStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="t('faultOccurTime')" width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column :label="t('deviceAction')" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="editFaultInDetail(row)">{{ t('deviceEdit') }}</el-button>
                <el-button v-if="row.status !== 'closed'" size="small" type="success" @click="closeFaultInDetail(row)">{{ t('faultClose') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" size="small" style="margin-top: 10px" @click="openFaultDialog">{{ t('faultAddRecord') }}</el-button>
        </el-tab-pane>

        <el-tab-pane :label="t('tabMaintenanceRecords')" name="maintenance">
          <el-table :data="device?.recent_maintenances || []" style="width: 100%">
            <el-table-column prop="maint_no" :label="t('maintNo')" width="180">
              <template #default="{ row }">
                <router-link :to="`/maintenance/${row.id}`" class="maint-link">{{ row.maint_no }}</router-link>
              </template>
            </el-table-column>
            <el-table-column prop="maint_type" :label="t('maintType')" width="100">
              <template #default="{ row }">
                <el-tag :type="getMaintTypeType(row.maint_type)" size="small">{{ getMaintTypeText(row.maint_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="maint_time" :label="t('maintTime')" width="160">
              <template #default="{ row }">{{ formatDateTime(row.maint_time || row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="description" :label="t('maintDescription')" min-width="200" />
            <el-table-column :label="t('deviceAction')" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="editMaintInDetail(row)">{{ t('deviceEdit') }}</el-button>
                <el-button type="danger" size="small" @click="deleteMaintInDetail(row.id)">{{ t('deviceDelete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" size="small" style="margin-top: 10px" @click="openMaintDialog">{{ t('maintAddRecord') }}</el-button>
        </el-tab-pane>

        <el-tab-pane :label="t('tabDeviceInventory')" name="inventory">
          <div v-if="deviceInventory.length > 0" class="compact-header">
            <span>{{ t('inventoryInstalledParts') }}: <strong class="text-success">{{ deviceInventory.length }}</strong> {{ t('inventoryParts') }}</span>
            <span>{{ t('inventoryTotalValue') }}: <strong class="text-success">¥{{ inventoryTotalValue.toFixed(2) }}</strong></span>
          </div>
          <el-table :data="deviceInventory" v-loading="inventoryLoading" stripe border size="small" style="margin-top: 8px">
            <el-table-column prop="serial_number" :label="t('spareSerialNumber')" width="120">
              <template #default="{ row }"><span class="text-primary">{{ row.serial_number || '-' }}</span></template>
            </el-table-column>
            <el-table-column prop="part_number" :label="t('sparePartNumber')" width="120" />
            <el-table-column prop="part_name" :label="t('spareName')" width="150" />
            <el-table-column prop="category" :label="t('spareCategory')" width="80" />
            <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="80">
              <template #default="{ row }"><span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span></template>
            </el-table-column>
            <el-table-column prop="installed_at" :label="t('inventoryInstalledAt')" width="160">
              <template #default="{ row }">{{ formatDateTime(row.installed_at) }}</template>
            </el-table-column>
            <el-table-column prop="installed_by" :label="t('inventoryInstalledBy')" width="80" />
          </el-table>
          <el-empty v-if="deviceInventory.length === 0 && !inventoryLoading" :description="t('inventoryNoParts')" :image-size="60" />
        </el-tab-pane>

        <el-tab-pane :label="t('tabCostStats')" name="costs">
          <div class="cost-summary">
            <el-statistic :title="t('purchaseCost')" :value="device?.purchase_cost || 0" prefix="¥" />
            <el-statistic :title="t('maintCost')" :value="calculateMaintCost()" :precision="2" prefix="¥" />
            <el-statistic :title="t('maintTotalCost')" :value="(device?.purchase_cost || 0) + calculateMaintCost()" :precision="2" prefix="¥" />
          </div>
        </el-tab-pane>

        <el-tab-pane :label="t('devicePhotos')" name="photos">
          <div class="photo-toolbar">
            <el-upload
              :action="uploadUrl"
              :headers="uploadHeaders"
              :data="{ photo_type: 'other' }"
              :on-success="handlePhotoUploadSuccess"
              :on-error="handlePhotoUploadError"
              show-upload
            >
              <el-button type="primary" size="small">
                <el-icon><Upload /></el-icon>
                {{ t('deviceUploadPhoto') }}
              </el-button>
            </el-upload>
          </div>
          <div v-if="device?.photos?.length" class="photo-grid">
            <div v-for="photo in device.photos" :key="photo.id" class="photo-item">
              <el-image :src="`/assets${photo.photo_path}`" fit="cover" :preview-src-list="[`/assets${photo.photo_path}`]" class="photo-image">
                <template #error>
                  <div class="image-error"><el-icon><Picture /></el-icon></div>
                </template>
              </el-image>
              <div class="photo-actions">
                <span class="photo-type">{{ getPhotoTypeText(photo.photo_type) }}</span>
                <el-button type="danger" size="small" @click="deletePhoto(photo.id)">{{ t('deviceDelete') }}</el-button>
              </div>
            </div>
          </div>
          <el-empty v-else :description="t('deviceNoPhotos')" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 编辑设备对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('editDeviceTitle')" width="600px" append-to-body draggable align-center class="edit-device-dialog">
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Monitor /></el-icon>
            {{ t('deviceBasicInfo') }}
          </div>
          <el-form :model="editForm" label-width="100px">
            <el-form-item :label="t('deviceName')" required>
              <el-input v-model="editForm.name" :placeholder="t('editDeviceNamePlaceholder')" :disabled="true" />
            </el-form-item>
            <el-form-item :label="t('deviceIp')" required>
              <div class="input-with-btn">
                <el-input v-model="editForm.ip" :placeholder="t('editDeviceIpPlaceholder')" />
                <el-button size="small" @click="testReachability" :loading="probeLoading.ip" :disabled="!editForm.ip">
                  测试连通
                </el-button>
              </div>
              <div v-if="probeResult.ip" class="probe-result">
                <el-tag :type="probeResult.ip.reachable ? 'success' : 'danger'" size="small">
                  {{ probeResult.ip.message }}
                </el-tag>
              </div>
            </el-form-item>
            <el-form-item :label="t('deviceModel')">
              <el-input v-model="editForm.model" :placeholder="t('editDeviceModelPlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('deviceLocation')">
              <el-input v-model="editForm.location" :placeholder="t('editDeviceLocationPlaceholder')" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 模块序列号 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Box /></el-icon>
            {{ t('deviceModules') }}
            <el-button
              size="small"
              type="primary"
              style="margin-left: auto;"
              @click="fetchDeviceInfoHandler"
              :loading="probeLoading.fetch"
              :disabled="!editForm.ip || !editForm.credential_group || sshDisabled"
            >
              一键获取设备信息
            </el-button>
          </div>
          <!-- SSH能力提示 -->
          <div v-if="sshDisabled" class="ssh-warning">
            <el-tag type="warning" size="small">AP设备不支持SSH，无法自动获取信息</el-tag>
          </div>
          <div v-if="sshSpecialPermission" class="ssh-warning">
            <el-tag type="info" size="small">防火墙需要GoVault权限才能SSH连接</el-tag>
          </div>
          <div class="modules-container">
            <div v-for="(module, index) in editForm.modules" :key="index" class="module-row">
              <el-select v-model="module.type" :placeholder="t('deviceModuleType')" size="small" style="width: 120px;">
                <el-option :label="t('deviceMainModule')" value="main" />
                <el-option :label="t('deviceExpansionModule')" value="expansion" />
                <el-option :label="t('devicePowerModule')" value="power" />
                <el-option :label="t('deviceSfpModule')" value="sfp" />
                <el-option :label="t('deviceFanModule')" value="fan" />
                <el-option :label="t('deviceTypeOther')" value="other" />
              </el-select>
              <el-input v-model="module.pid" placeholder="型号 (如 C9300-24P)" size="small" style="width: 150px;" />
              <el-input v-model="module.serial_number" :placeholder="t('deviceModuleSn')" size="small" style="width: 160px;" />
              <el-button type="danger" size="small" :icon="Close" circle @click="removeModule(index)" v-if="editForm.modules && editForm.modules.length > 1" />
            </div>
            <el-button type="primary" size="small" :icon="Plus" @click="addModule">{{ t('deviceAddModule') }}</el-button>
          </div>
        </div>

        <!-- 分类与状态 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Setting /></el-icon>
            {{ t('deviceCategoryStatus') }}
          </div>
          <el-form :model="editForm" label-width="100px">
            <el-form-item :label="t('deviceType')" required>
              <el-select v-model="editForm.device_type" :placeholder="t('deviceSelectType')">
                <el-option-group :label="t('deviceLayerDatacenter')">
                  <el-option :label="t('deviceTypeCoreSwitch')" value="core_switch" />
                  <el-option :label="t('deviceTypeServerSwitch')" value="server_switch" />
                  <el-option :label="t('deviceTypeRouter')" value="router" />
                  <el-option :label="t('deviceTypePA')" value="pa" />
                  <el-option :label="t('deviceTypeFTD')" value="ftd" />
                </el-option-group>
                <el-option-group :label="t('deviceLayerWiFi')">
                  <el-option :label="t('deviceTypeAP')" value="ap" />
                  <el-option :label="t('deviceTypeWLC')" value="wlc" />
                </el-option-group>
                <el-option-group :label="t('deviceLayerAccess')">
                  <el-option :label="t('deviceTypeUCE')" value="uce" />
                  <el-option :label="t('deviceTypeOfficeSwitch')" value="office_switch" />
                </el-option-group>
                <el-option-group :label="t('deviceTypeOther')">
                  <el-option :label="t('deviceTypeOther')" value="other" />
                </el-option-group>
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceVendor')">
              <el-select v-model="editForm.vendor">
                <el-option v-for="v in vendors" :key="v.key" :label="v.name" :value="v.key" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceRole')">
              <el-select v-model="editForm.role">
                <el-option :label="t('deviceRoleAccess')" value="access" />
                <el-option :label="t('deviceRoleDistribution')" value="distribution" />
                <el-option :label="t('deviceRoleCore')" value="core" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceDeploymentStatus')">
              <el-select v-model="editForm.deployment_status">
                <el-option :label="t('statusInUse')" value="in-use" />
                <el-option :label="t('statusUnUsed')" value="un-used" />
                <el-option :label="t('statusMaintenance')" value="maintenance" />
                <el-option :label="t('statusRetired')" value="retired" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceStatus')">
              <el-select v-model="editForm.status">
                <el-option :label="t('statusOnline')" value="online" />
                <el-option :label="t('statusOffline')" value="offline" />
                <el-option :label="t('statusMaintenance')" value="maintenance" />
                <el-option :label="t('statusRetired')" value="retired" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceCredentialGroup')">
              <div class="input-with-btn">
                <el-select v-model="editForm.credential_group" :placeholder="t('deviceSelectCredential')">
                  <el-option label="default" value="default" />
                  <el-option v-for="cred in credentialGroups" :key="cred.id" :label="cred.name" :value="cred.name" />
                </el-select>
                <el-button size="small" @click="testConnection" :loading="probeLoading.connection" :disabled="!editForm.ip || !editForm.credential_group || sshDisabled">
                  测试连接
                </el-button>
              </div>
              <div v-if="probeResult.connection" class="probe-result">
                <el-tag :type="probeResult.connection.connected ? 'success' : 'danger'" size="small">
                  {{ probeResult.connection.message }}
                </el-tag>
              </div>
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateDevice">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 查看配置对话框 -->
    <el-dialog v-model="showConfigDialog" :title="t('backupConfigContent')" width="800px" append-to-body draggable align-center>
      <el-card v-if="configContent"><pre class="config-content">{{ configContent }}</pre></el-card>
      <el-empty v-else :description="t('backupNoConfig')" />
    </el-dialog>

    <!-- 添加故障记录对话框 -->
    <el-dialog v-model="showFaultDialog" :title="editMode ? t('faultEditRecord') : t('faultAddRecord')" width="650px" class="edit-fault-dialog" append-to-body draggable align-center>
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Warning /></el-icon>
            {{ t('faultBasicInfo') || '基础信息' }}
          </div>
          <el-form :model="faultForm" label-width="120px">
            <el-form-item :label="t('faultAssignTo')">
              <el-select v-model="faultForm.assigned_to" :placeholder="t('faultAssignPlaceholder')" style="width: 100%" clearable>
                <el-option v-for="user in users" :key="user" :label="user" :value="user" />
              </el-select>
              <div class="assign-tip">{{ t('faultAssignTip') || '指派后将自动通知负责人' }}</div>
            </el-form-item>
            <el-form-item :label="t('faultType')">
              <el-select v-model="faultForm.fault_type" clearable style="width: 100%">
                <el-option :label="t('faultTypeHardware')" value="hardware" />
                <el-option :label="t('faultTypeSoftware')" value="software" />
                <el-option :label="t('faultTypeConfig')" value="config" />
                <el-option :label="t('faultTypeNetwork')" value="network" />
                <el-option :label="t('faultTypeOther')" value="other" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('faultPriority')" required>
              <el-select v-model="faultForm.severity" style="width: 100%">
                <el-option label="P1 - Critical" value="critical" />
                <el-option label="P2 - Major" value="major" />
                <el-option label="P3 - Minor" value="minor" />
                <el-option label="P4 - Warning" value="warning" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('faultStatus')" v-if="editMode">
              <el-select v-model="faultForm.status" style="width: 100%">
                <el-option :label="t('faultStatusOpen')" value="open" />
                <el-option :label="t('faultStatusAssigned')" value="assigned" />
                <el-option :label="t('faultStatusDiagnosing')" value="diagnosing" />
                <el-option :label="t('faultStatusTransferred')" value="transferred" />
                <el-option :label="t('faultStatusResolved')" value="resolved" />
                <el-option :label="t('faultStatusClosed')" value="closed" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('faultDowntimeMinutes')">
              <el-input-number v-model="faultForm.downtime_minutes" :min="0" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 影响与描述 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Document /></el-icon>
            {{ t('faultImpactDesc') || '影响与描述' }}
          </div>
          <el-form :model="faultForm" label-width="120px">
            <el-form-item :label="t('faultImpact')">
              <el-input v-model="faultForm.impact" type="textarea" :rows="2" :placeholder="t('faultImpactPlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('faultDescription')" required>
              <el-input v-model="faultForm.description" type="textarea" :rows="4" :placeholder="t('faultDescPlaceholder')" />
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showFaultDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateFaultInDetail() : addFault()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 添加维修记录对话框 -->
    <!-- 维修表单对话框（使用共享组件） -->
    <MaintenanceFormDialog
      v-model="showMaintDialog"
      :presetDeviceId="device?.id"
      :presetDeviceName="device?.name"
      :editData="editMaintData"
      :showScanButton="true"
      :showReturnParts="true"
      @success="handleMaintSuccess"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Download, Upload, Picture, View, Tools, Delete, Monitor, Box, Setting, Plus, Close, Warning, Document, Refresh, Timer, WarningFilled, Promotion } from '@element-plus/icons-vue'
import { getDeviceDetail, createFault, createMaintenance, updateMaintenance, deleteMaintenance, updateFault, updateDevice as updateDeviceApi, getDeviceInventory, deleteDevice, getCredentials, getVendors, testDeviceReachability, testDeviceConnection, fetchDeviceInfo, getUsers, getDeviceMetrics, listDeviceInterfaces, updateDeviceInterface, getInterfaceTraffic, discoverDeviceInterfaces, discoverDeviceNeighbors } from '@/api'
import { formatDateTime, formatDate } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import MaintenanceFormDialog from '@/components/MaintenanceFormDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const device = ref(null)
const loading = ref(false)
const activeTab = ref('backups')
const showFaultDialog = ref(false)
const showMaintDialog = ref(false)
const showEditDialog = ref(false)
const showConfigDialog = ref(false)
const editMode = ref(false)
const editMaintData = ref(null)  // 维修编辑数据
const configContent = ref('')
const credentialGroups = ref([])
const vendors = ref([])
const users = ref([])

// 设备探测状态
const probeLoading = ref({
  ip: false,
  connection: false,
  fetch: false
})

const probeResult = ref({
  ip: null,
  connection: null
})

// 设备性能指标
const metricsLoading = ref(false)
const metricsData = ref({
  cpu: { value: null, status: 'unknown' },
  memory: { used_percent: null, status: 'unknown' },
  temperature: { value: null, status: 'unknown' },
  uptime: { uptime_days: null, human: null },
  interfaces: { up: null, down: null, total: null },
  errors: { total_errors: null, has_errors: false },
  uplinks: [],
  timestamp: null,
  snmp_available: false
})

// 接口监控状态（SNMP）
const interfaces = ref([])
const ifacesLoading = ref(false)
const ifaceDiscovering = ref(false)
const ifaceNeighborLoading = ref(false)
const ifaceMonitoredOnly = ref(false)
const ifaceAutoRefresh = ref(false)
const trafficData = ref({})
const trafficLoading = ref({})
let autoRefreshTimer = null

const ifaceUpCount = computed(() => interfaces.value.filter(i => i.oper_status === 'up').length)
const ifaceUplinkCount = computed(() => interfaces.value.filter(i => i.is_uplink).length)
const ifaceMonitoredCount = computed(() => interfaces.value.filter(i => i.monitored).length)

// 设备整体健康状态计算
const healthStatusClass = computed(() => {
  const cpu = metricsData.value.cpu?.value
  const mem = metricsData.value.memory?.used_percent
  const temp = metricsData.value.temperature?.value
  const hasDownPorts = metricsData.value.interfaces?.down > 0
  const hasErrors = metricsData.value.errors?.has_errors

  if (cpu >= 90 || mem >= 90 || temp >= 70) return 'status-critical'
  if (cpu >= 75 || mem >= 75 || temp >= 55 || hasDownPorts || hasErrors) return 'status-warning'
  return 'status-healthy'
})

const healthDotClass = computed(() => {
  return healthStatusClass.value.replace('status-', '')
})

const healthStatusLabel = computed(() => {
  const status = healthStatusClass.value
  const labels = {
    'status-healthy': t('healthGood'),
    'status-warning': t('healthWarning'),
    'status-critical': t('healthCritical')
  }
  return labels[status] || '--'
})

// 状态辅助函数
const getMetricStatus = (value) => {
  if (value === null || value === undefined) return 'status-unknown'
  if (value < 50) return 'status-ok'
  if (value < 75) return 'status-warn'
  if (value < 90) return 'status-danger'
  return 'status-critical'
}

const getMetricStatusText = (value) => {
  if (value === null || value === undefined) return '--'
  if (value < 50) return t('statusOk')
  if (value < 75) return t('statusWarn')
  return t('statusHigh')
}

const getTempStatus = (value) => {
  if (value === null || value === undefined) return 'status-unknown'
  if (value < 40) return 'status-ok'
  if (value < 55) return 'status-warn'
  return 'status-danger'
}

const getTempStatusText = (value) => {
  if (value === null || value === undefined) return '--'
  if (value < 40) return t('statusOk')
  if (value < 55) return t('statusWarm')
  return t('statusHot')
}

const formatErrorCount = (count) => {
  if (count === null || count === undefined) return '0'
  if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M'
  if (count >= 1000) return (count / 1000).toFixed(1) + 'K'
  return count.toString()
}

// SSH能力判断
const sshDisabled = computed(() => {
  // AP设备不支持SSH
  return editForm.value.device_type === 'ap'
})

const sshSpecialPermission = computed(() => {
  // 防火墙需要GoVault权限
  return ['pa', 'ftd'].includes(editForm.value.device_type)
})

// 设备资产
const deviceInventory = ref([])
const inventoryLoading = ref(false)
const inventoryTotalValue = computed(() => deviceInventory.value.reduce((sum, item) => sum + (item.unit_price || 0), 0))

const faultForm = ref({
  id: null,
  severity: 'major',
  fault_type: '',
  downtime_minutes: 0,
  impact: '',
  description: '',
  status: 'open',
  assigned_to: ''
})

const editForm = ref({})

const uploadUrl = computed(() => `/api/devices/${route.params.id}/photos`)
const uploadHeaders = computed(() => ({}))

const getStatusType = (status) => ({ online: 'success', offline: 'danger', maintenance: 'warning', retired: 'info' }[status] || 'info')
const getStatusText = (status) => ({ online: t('statusOnline'), offline: t('statusOffline'), maintenance: t('statusMaintenance'), retired: t('statusRetired') }[status] || status)
const getFaultStatusType = (status) => ({ open: 'info', investigating: 'warning', resolved: 'success', closed: 'info' }[status] || 'info')
const getFaultStatusText = (status) => ({ open: t('faultStatusOpen'), investigating: t('faultStatusInvestigating'), resolved: t('faultStatusResolved'), closed: t('faultStatusClosed') }[status] || status)
const getRoleText = (role) => ({ access: t('deviceRoleAccess'), distribution: t('deviceRoleDistribution'), core: t('deviceRoleCore') }[role] || role)
const getVendorText = (vendor) => ({ cisco: 'Cisco', huawei: t('vendorHuawei'), '华为': t('vendorHuawei'), h3c: 'H3C', juniper: 'Juniper' }[vendor?.toLowerCase()] || vendor || 'Cisco')
const getVendorTagType = (vendor) => ({ cisco: '', huawei: 'success', h3c: 'warning', juniper: 'danger' }[vendor?.toLowerCase()] || '')
const getSeverityType = (severity) => ({ critical: 'danger', major: 'warning', minor: '', warning: 'info' }[severity] || 'info')
const getSeverityText = (severity) => ({ critical: t('dashCritical'), major: t('dashMajor'), minor: t('dashMinor'), warning: t('dashWarning') }[severity] || severity)
const getPhotoTypeText = (type) => ({ front: t('devicePhotoFront'), back: t('devicePhotoBack'), label: t('devicePhotoLabel'), rack: t('devicePhotoRack'), other: t('devicePhotoOther') }[type] || type)
const getMaintTypeText = (type) => ({ preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }[type] || type)
const getMaintTypeType = (type) => ({ preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }[type] || '')

// 获取利用率颜色
const getUtilizationColor = (value) => {
  if (value === null || value === undefined) return '#b0b0b0'
  if (value < 50) return '#00b894'
  if (value < 75) return '#fdcb6e'
  if (value < 90) return '#e17055'
  return '#d63031'
}

// 获取指标颜色（CPU/内存）
const getMetricColor = (value) => {
  if (value === null || value === undefined) return '#94a3b8'
  if (value < 50) return '#22c55e'
  if (value < 75) return '#eab308'
  if (value < 90) return '#f97316'
  return '#ef4444'
}

// 获取温度颜色
const getTempColor = (value) => {
  if (value === null || value === undefined) return '#94a3b8'
  if (value < 40) return '#22c55e'
  if (value < 55) return '#eab308'
  if (value < 70) return '#f97316'
  return '#ef4444'
}

const calculateMaintCost = () => {
  if (!device.value?.recent_maintenances) return 0
  return device.value.recent_maintenances.reduce((sum, m) => sum + (parseFloat(m.parts_cost) || 0) + (parseFloat(m.labor_cost) || 0), 0)
}

const loadDevice = debounce(async (force = false) => {
  loading.value = true
  try {
    const data = await cachedRequest(
      () => getDeviceDetail(route.params.id),
      'device_detail',
      { id: route.params.id },
      { forceRefresh: force }
    )
    device.value = data
    // 解析 modules 数据（兼容旧数据无 pid 字段）
    const modules = data.modules || [{ type: 'main', pid: '', serial_number: '' }]
    // 确保每个模块都有 pid 字段
    const normalizedModules = modules.map(m => ({
      type: m.type || 'other',
      pid: m.pid || '',
      serial_number: m.serial_number || ''
    }))
    editForm.value = {
      ...data,
      modules: Array.isArray(normalizedModules) && normalizedModules.length > 0 ? normalizedModules : [{ type: 'main', pid: '', serial_number: '' }]
    }
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('msgDeviceDetailFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

const loadCredentialGroups = async () => {
  try {
    const data = await cachedRequest(
      () => getCredentials(),
      'credentials',
      {},
      { ttl: 60000 }
    )
    credentialGroups.value = data.items || data || []
  } catch (error) {
    // Silent fail
  }
}

const loadVendors = async () => {
  try {
    const res = await getVendors()
    vendors.value = res.vendors || []
  } catch (error) {
    // Silent fail
  }
}

const loadUsers = async () => {
  try {
    const res = await getUsers()
    users.value = res || []
  } catch (error) {
    // Silent fail
  }
}

const addModule = () => {
  if (!editForm.value.modules) {
    editForm.value.modules = [{ type: 'main', pid: '', serial_number: '' }]
  }
  editForm.value.modules.push({ type: 'other', pid: '', serial_number: '' })
}

const removeModule = (index) => {
  if (editForm.value.modules && editForm.value.modules.length > 1) {
    editForm.value.modules.splice(index, 1)
  }
}

// 设备探测函数
const testReachability = async () => {
  if (!editForm.value.ip) return
  probeLoading.value.ip = true
  probeResult.value.ip = null
  try {
    const result = await testDeviceReachability(editForm.value.ip)
    probeResult.value.ip = result
  } catch (error) {
    probeResult.value.ip = { reachable: false, message: '测试失败: ' + (error.response?.data?.detail || error.message) }
  } finally {
    probeLoading.value.ip = false
  }
}

const testConnection = async () => {
  if (!editForm.value.ip || !editForm.value.credential_group) return
  probeLoading.value.connection = true
  probeResult.value.connection = null
  try {
    const result = await testDeviceConnection(
      editForm.value.ip,
      editForm.value.credential_group,
      editForm.value.vendor,
      editForm.value.device_type
    )
    probeResult.value.connection = result
  } catch (error) {
    probeResult.value.connection = { connected: false, message: '连接失败: ' + (error.response?.data?.detail || error.message) }
  } finally {
    probeLoading.value.connection = false
  }
}

const fetchDeviceInfoHandler = async () => {
  if (!editForm.value.ip || !editForm.value.credential_group) return
  probeLoading.value.fetch = true
  try {
    const result = await fetchDeviceInfo(
      editForm.value.ip,
      editForm.value.credential_group,
      editForm.value.vendor,
      editForm.value.device_type
    )
    if (result.success) {
      // 自动填充设备信息
      if (result.model) editForm.value.model = result.model
      if (result.serial_number && editForm.value.modules.length > 0) {
        editForm.value.modules[0].serial_number = result.serial_number
      }
      if (result.location) editForm.value.location = result.location
      // 添加获取到的模块信息
      if (result.modules && result.modules.length > 0) {
        // 清空现有模块，用获取到的模块替换
        editForm.value.modules = result.modules
      }
      ElMessage.success('设备信息获取成功')
    } else {
      ElMessage.warning(result.message || '获取设备信息失败')
    }
  } catch (error) {
    ElMessage.error('获取设备信息失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    probeLoading.value.fetch = false
  }
}

const loadDeviceInventory = debounce(async (force = false) => {
  if (!route.params.id) return
  inventoryLoading.value = true
  try {
    const data = await cachedRequest(
      () => getDeviceInventory(route.params.id),
      'device_inventory',
      { id: route.params.id },
      { forceRefresh: force }
    )
    deviceInventory.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('msgDeviceInventoryFailed'))
    }
  } finally {
    inventoryLoading.value = false
  }
}, 300)

watch(activeTab, (newTab) => {
  if (newTab === 'inventory') loadDeviceInventory()
  if (newTab === 'interfaces') loadInterfaces()
})

// ===== 接口监控（SNMP）=====
const loadInterfaces = async (force = false) => {
  if (!route.params.id) return
  ifacesLoading.value = true
  try {
    const data = await listDeviceInterfaces(route.params.id, ifaceMonitoredOnly.value)
    interfaces.value = data.items || []
  } catch (error) {
    ElMessage.error('接口列表加载失败')
  } finally {
    ifacesLoading.value = false
  }
}

const discoverInterfaces = async () => {
  ifaceDiscovering.value = true
  try {
    const res = await discoverDeviceInterfaces(route.params.id)
    if (res && res.ok === false) {
      ElMessage.warning(res.error || '发现失败')
    } else {
      ElMessage.success(`发现完成，共 ${res.count != null ? res.count : ''} 个接口`)
      await loadInterfaces(true)
    }
  } catch (error) {
    ElMessage.error('发现接口失败（检查 SNMP 是否开启）')
  } finally {
    ifaceDiscovering.value = false
  }
}

const discoverNeighbors = async () => {
  ifaceNeighborLoading.value = true
  try {
    await discoverDeviceNeighbors(route.params.id)
    ElMessage.success('邻居发现完成')
    await loadInterfaces(true)
  } catch (error) {
    ElMessage.error('发现邻居失败')
  } finally {
    ifaceNeighborLoading.value = false
  }
}

const toggleUplink = async (row, val) => {
  try {
    await updateDeviceInterface(route.params.id, row.if_index, { is_uplink: val })
    row.is_uplink = val
    ElMessage.success('已更新')
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const toggleMonitored = async (row, val) => {
  try {
    await updateDeviceInterface(route.params.id, row.if_index, { monitored: val })
    row.monitored = val
    ElMessage.success('已更新')
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const onIfaceExpand = async (row, expandedRows) => {
  const isExpanded = Array.isArray(expandedRows) && expandedRows.some(r => r.if_index === row.if_index)
  if (isExpanded) await loadTraffic(row.if_index)
}

const loadTraffic = async (ifIndex) => {
  trafficLoading.value = { ...trafficLoading.value, [ifIndex]: true }
  try {
    const data = await getInterfaceTraffic(route.params.id, ifIndex, 60)
    trafficData.value = { ...trafficData.value, [ifIndex]: data.samples || [] }
  } catch (error) {
    trafficData.value = { ...trafficData.value, [ifIndex]: [] }
  } finally {
    trafficLoading.value = { ...trafficLoading.value, [ifIndex]: false }
  }
}

const sparkPoints = (samples, key, width = 240, height = 40) => {
  if (!samples || !samples.length) return ''
  const vals = samples.map(s => s[key] || 0)
  const max = Math.max(...vals, 1)
  const n = vals.length
  return vals.map((v, i) => {
    const x = n === 1 ? width : (i / (n - 1)) * width
    const y = height - (v / max) * (height - 2) - 1
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

const formatBps = (bps) => {
  if (bps == null) return '--'
  if (bps >= 1e9) return (bps / 1e9).toFixed(2) + ' Gbps'
  if (bps >= 1e6) return (bps / 1e6).toFixed(2) + ' Mbps'
  if (bps >= 1e3) return (bps / 1e3).toFixed(1) + ' Kbps'
  return bps + ' bps'
}

const setMonitorTier = async (tier) => {
  try {
    await updateDeviceApi(route.params.id, { monitor_tier: tier })
    if (device.value) device.value.monitor_tier = tier
    clearCache('device_detail')
    ElMessage.success('监控分级已更新为 ' + tier)
  } catch (error) {
    ElMessage.error('更新监控分级失败')
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  autoRefreshTimer = setInterval(() => {
    refreshMetrics()
    if (activeTab.value === 'interfaces') loadInterfaces(true)
  }, 30000)
}
const stopAutoRefresh = () => {
  if (autoRefreshTimer) { clearInterval(autoRefreshTimer); autoRefreshTimer = null }
}
watch(ifaceAutoRefresh, (on) => { on ? startAutoRefresh() : stopAutoRefresh() })

// 刷新设备性能指标
const refreshMetrics = async () => {
  if (!route.params.id) return
  metricsLoading.value = true
  try {
    const data = await getDeviceMetrics(route.params.id)
    metricsData.value = data
    if (data && data.snmp_available === false) {
      ElMessage.warning(data.error || '设备未启用 SNMP，无法获取性能指标')
    } else if (data && data.error) {
      ElMessage.warning(data.error)
    }
  } catch (error) {
    if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')) {
      ElMessage.error('性能指标请求超时，设备 SNMP 可能未配置或网络不可达')
    } else {
      ElMessage.error(t('msgMetricsLoadFailed') || '性能指标获取失败')
    }
  } finally {
    metricsLoading.value = false
  }
}

const backupNow = async () => {
  try {
    const { backupDevice } = await import('@/api')
    await backupDevice(route.params.id, 'Web')
    ElMessage.success(t('msgBackupSuccessShort'))
    clearCache('device_detail')
    loadDevice(true)
  } catch (error) {
    // 错误已在请求拦截器中显示，这里只需清理缓存
    clearCache('device_detail')
  }
}
const viewLatestConfig = async () => {
  if (!device.value?.recent_backups?.length) { ElMessage.warning(t('backupNoConfig')); return }
  viewConfig(device.value.recent_backups[0].id)
}
const viewConfig = async (backupId) => {
  try {
    const { getBackupContent } = await import('@/api')
    const data = await getBackupContent(backupId)
    configContent.value = data.content
    showConfigDialog.value = true
  } catch (error) { ElMessage.error(t('msgConfigLoadFailed')) }
}

const handlePhotoUploadSuccess = () => { ElMessage.success(t('msgPhotoUploadSuccess')); clearCache('device_detail'); loadDevice(true) }
const handlePhotoUploadError = () => { ElMessage.error(t('msgPhotoUploadFailed')) }
const deletePhoto = async (photoId) => {
  try {
    await ElMessageBox.confirm(t('confirmDeletePhoto'), t('msgConfirmDelete'), { type: 'warning' })
    const api = await import('@/api')
    await api.deletePhoto(route.params.id, photoId)
    clearCache('device_detail')
    ElMessage.success(t('msgPhotoDeleteSuccess'))
    loadDevice(true)
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgPhotoDeleteFailed')) }
}

const updateDevice = async () => {
  try {
    await updateDeviceApi(route.params.id, {
      ...editForm.value,
      modules: editForm.value.modules
    })
    clearCache('device_detail')
    clearCache('device_inventory')
    ElMessage.success(t('msgDeviceUpdateSuccess'))
    showEditDialog.value = false
    loadDevice(true)
    loadDeviceInventory(true)  // 刷新设备资产
  } catch (error) { ElMessage.error(t('msgDeviceUpdateFailed')) }
}

const confirmDeleteDevice = async () => {
  try {
    await ElMessageBox.confirm(t('confirmDeleteDevice'), t('msgConfirmDelete'), { type: 'warning' })
    await deleteDevice(route.params.id)
    clearCache('devices')
    clearCache('device_detail')
    ElMessage.success(t('msgDeviceDeleteSuccess'))
    router.push('/devices')
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgDeviceDeleteFailed')) }
}

const openFaultDialog = () => {
  editMode.value = false
  faultForm.value = {
    id: null,
    severity: 'major',
    fault_type: '',
    downtime_minutes: 0,
    impact: '',
    description: '',
    status: 'open',
    assigned_to: ''
  }
  showFaultDialog.value = true
}
const addFault = async () => {
  try {
    const status = faultForm.value.assigned_to ? 'assigned' : 'open'
    await createFault({
      device_id: device.value.id,
      device_name: device.value.name,
      ...faultForm.value,
      status,
      reporter: 'Web'
    })
    clearCache('device_detail')
    ElMessage.success(t('msgFaultAddSuccess'))
    showFaultDialog.value = false
    loadDevice(true)
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) { ElMessage.error(t('msgFaultAddFailed')) }
}
const editFaultInDetail = (row) => {
  editMode.value = true
  faultForm.value = {
    id: row.id,
    severity: row.severity,
    fault_type: row.fault_type || '',
    downtime_minutes: row.downtime_minutes || 0,
    impact: row.impact || '',
    description: row.description,
    status: row.status,
    assigned_to: row.assigned_to || ''
  }
  showFaultDialog.value = true
}
const updateFaultInDetail = async () => {
  try {
    await updateFault(faultForm.value.id, faultForm.value)
    clearCache('device_detail')
    ElMessage.success(t('msgFaultUpdateSuccess'))
    showFaultDialog.value = false
    editMode.value = false
    loadDevice(true)
  } catch (error) { ElMessage.error(t('msgFaultUpdateFailed')) }
}
const closeFaultInDetail = async (row) => {
  try {
    await ElMessageBox.confirm(t('faultCloseConfirm', { id: row.fault_no }), t('faultCloseTitle'), { type: 'warning' })
    await updateFault(row.id, { status: 'closed' })
    clearCache('device_detail')
    ElMessage.success(t('msgFaultCloseSuccess'))
    loadDevice(true)
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgFaultCloseFailed')) }
}

// 维修表单相关 - 使用共享组件
const openMaintDialog = () => {
  editMaintData.value = null
  showMaintDialog.value = true
}

const editMaintInDetail = (row) => {
  editMaintData.value = {
    id: row.id,
    device_id: device.value?.id,
    maint_type: row.maint_type,
    spare_parts: row.spare_parts || [],
    parts_cost: row.parts_cost || 0,
    labor_hours: row.labor_hours || 0,
    labor_cost: row.labor_cost || 0,
    vendor: row.vendor || '',
    description: row.description
  }
  showMaintDialog.value = true
}

const handleMaintSuccess = () => {
  clearCache('device_detail')
  loadDevice(true)
}

const deleteMaintInDetail = async (maintId) => {
  try {
    await ElMessageBox.confirm(t('confirmDeleteMaint'), t('msgConfirmDelete'), { type: 'warning' })
    await deleteMaintenance(maintId)
    clearCache('device_detail')
    ElMessage.success(t('msgMaintDeleteSuccess'))
    loadDevice(true)
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgMaintDeleteFailed')) }
}

onMounted(() => { loadDevice(); loadCredentialGroups(); loadVendors(); loadUsers(); refreshMetrics() })
onUnmounted(() => { stopAutoRefresh() })
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════════════
   设备详情页 - 现代极简设计 (OpenAI/SpaceX风格)
   设计理念: 状态优先、数据驱动、简洁高效
   ═══════════════════════════════════════════════════════════════════════════ */

.device-detail-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
}

/* ─────────────────────────────────────────────────────────────────────────
   页面头部 - 精简
   ───────────────────────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 0;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-actions {
  display: flex;
  gap: 8px;
}

/* ─────────────────────────────────────────────────────────────────────────
   设备健康仪表盘 - 核心组件
   ───────────────────────────────────────────────────────────────────────── */
.device-dashboard {
  margin-bottom: 24px;
}

.status-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

/* 健康状态边框指示 */
.status-card.status-healthy {
  border-color: rgba(34, 197, 94, 0.3);
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
}

.status-card.status-warning {
  border-color: rgba(234, 179, 8, 0.4);
  box-shadow: 0 0 0 1px rgba(234, 179, 8, 0.12), 0 1px 3px rgba(0, 0, 0, 0.04);
}

.status-card.status-critical {
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.12), 0 2px 8px rgba(239, 68, 68, 0.08);
}

/* ─────────────────────────────────────────────────────────────────────────
   状态头部 - 一目了然的健康状态
   ───────────────────────────────────────────────────────────────────────── */
.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-dot.healthy {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
}

.status-dot.warning {
  background: #eab308;
  box-shadow: 0 0 8px rgba(234, 179, 8, 0.6);
}

.status-dot.critical {
  background: #ef4444;
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.8);
  animation: pulse-critical 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(0.95); }
}

@keyframes pulse-critical {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
}

.status-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.02em;
}

.device-identity {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.device-ip-large {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.device-name-sub {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 400;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn-refresh,
.action-btn-edit {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--border-default);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.action-btn-refresh:hover,
.action-btn-edit:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
  color: var(--text-primary);
}

/* ─────────────────────────────────────────────────────────────────────────
   核心指标 - 四个关键数据（CPU、内存、温度、运行时长）
   ───────────────────────────────────────────────────────────────────────── */
.core-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.metric-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 16px;
  background: var(--bg-tertiary);
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-block:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

/* 环形指标显示 */
.metric-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 4px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 12px;
}

.metric-number {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.metric-unit {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 1px;
}

.metric-name {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  margin-bottom: 4px;
}

.metric-status {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  letter-spacing: 0.02em;
}

.metric-status.status-ok {
  background: rgba(34, 197, 94, 0.12);
  color: #16a34a;
}

.metric-status.status-warn {
  background: rgba(234, 179, 8, 0.12);
  color: #a16207;
}

.metric-status.status-danger {
  background: rgba(249, 115, 22, 0.12);
  color: #ea580c;
}

.metric-status.status-critical {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}

.metric-status.status-unknown {
  background: rgba(148, 163, 184, 0.12);
  color: #64748b;
}

/* 运行时长特殊样式 */
.uptime-block {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(22, 163, 74, 0.04) 100%);
}

.uptime-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-bottom: 12px;
}

.uptime-icon {
  font-size: 20px;
  color: #22c55e;
}

.uptime-value {
  font-size: 28px;
  font-weight: 700;
  color: #22c55e;
  letter-spacing: -0.03em;
}

.uptime-unit {
  font-size: 14px;
  color: var(--text-muted);
  font-weight: 500;
}

.metric-status.uptime-detail {
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
}

/* ─────────────────────────────────────────────────────────────────────────
   网络健康状态 - 端口、错误、上行链路
   ───────────────────────────────────────────────────────────────────────── */
.network-health {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.health-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-tertiary);
  border-radius: 10px;
  transition: background 0.2s ease;
}

.health-item:hover {
  background: var(--bg-hover);
}

.health-item.health-ok {
  background: rgba(34, 197, 94, 0.06);
}

.health-item .el-icon {
  font-size: 18px;
  color: var(--text-secondary);
}

.health-item.health-ok .el-icon {
  color: #22c55e;
}

.health-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 40px;
}

.health-label {
  font-size: 12px;
  color: var(--text-muted);
  flex: 1;
}

.health-alert,
.health-ok-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
}

/* ─────────────────────────────────────────────────────────────────────────
   折叠信息区
   ───────────────────────────────────────────────────────────────────────── */
.info-collapse {
  margin-bottom: 20px;
  border: none;
}

.info-collapse .el-collapse-item__header {
  background: var(--bg-tertiary);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  border: none;
  margin-bottom: 8px;
}

.info-collapse .el-collapse-item__wrap {
  border: none;
}

.info-collapse .el-collapse-item__content {
  padding: 0 8px 8px 8px;
}

.info-compact-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-row-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.info-key {
  font-size: 12px;
  color: var(--text-muted);
}

.info-val {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 上行链路详情 */
.uplinks-detail {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.uplink-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.uplink-interface {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.uplink-util-visual {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.uplink-bar-bg {
  width: 100px;
  height: 6px;
  background: rgba(148, 163, 184, 0.2);
  border-radius: 3px;
  overflow: hidden;
}

.uplink-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease, background 0.5s ease;
}

.uplink-percent {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 36px;
}

.uplink-speed {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
}

/* ─────────────────────────────────────────────────────────────────────────
   快捷操作栏
   ───────────────────────────────────────────────────────────────────────── */
.quick-actions-bar {
  display: flex;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
  margin-top: 4px;
}

.quick-actions-bar .el-button {
  flex: 1;
  height: 40px;
  font-weight: 500;
  border-radius: 10px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.quick-actions-bar .el-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* ─────────────────────────────────────────────────────────────────────────
   Tabs 区域
   ───────────────────────────────────────────────────────────────────────── */
.tabs-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.tabs-wrapper .el-tabs__header {
  margin-bottom: 20px;
}

.tabs-wrapper .el-tabs__nav-wrap::after {
  height: 1px;
  background: var(--border-subtle);
}

.tabs-wrapper .el-tabs__item {
  font-size: 14px;
  font-weight: 500;
}

.tabs-wrapper .el-tabs__item.is-active {
  font-weight: 600;
}

/* ─────────────────────────────────────────────────────────────────────────
   配置内容
   ───────────────────────────────────────────────────────────────────────── */
.config-content {
  background: #1a1a2e;
  color: #e0e0e0;
  padding: 16px;
  border-radius: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 500px;
  overflow-y: auto;
}

/* ─────────────────────────────────────────────────────────────────────────
   其他组件样式
   ───────────────────────────────────────────────────────────────────────── */
.fault-link, .maint-link {
  color: var(--accent-secondary);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s ease;
}

.fault-link:hover, .maint-link:hover {
  color: var(--accent-primary);
}

.cost-summary {
  display: flex;
  justify-content: space-around;
  padding: 20px;
}

.photo-toolbar {
  margin-bottom: 16px;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.photo-item {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.photo-image {
  width: 100%;
  height: 140px;
  object-fit: cover;
}

.photo-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: var(--bg-tertiary);
}

.photo-type {
  font-size: 12px;
  color: var(--text-secondary);
}

.image-error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.compact-header {
  display: flex;
  gap: 16px;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  font-size: 13px;
}

.text-primary {
  color: var(--accent-secondary);
  font-weight: 500;
}

.text-success {
  color: var(--accent-success);
  font-weight: 600;
}

/* ─────────────────────────────────────────────────────────────────────────
   编辑对话框样式
   ───────────────────────────────────────────────────────────────────────── */
.edit-device-dialog .edit-dialog-content,
.edit-fault-dialog .edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.edit-device-dialog .form-section,
.edit-fault-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

.edit-device-dialog .form-section-title,
.edit-fault-dialog .form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}

.edit-device-dialog .form-section-title .el-icon,
.edit-fault-dialog .form-section-title .el-icon {
  color: var(--accent-primary);
}

.edit-device-dialog .el-form-item,
.edit-fault-dialog .el-form-item {
  margin-bottom: 12px;
}

.edit-fault-dialog .assign-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}

/* 模块容器 */
.modules-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.module-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 设备探测 UI */
.input-with-btn {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.input-with-btn > .el-input,
.input-with-btn > .el-select {
  flex: 1;
  min-width: 0;
}

.input-with-btn > .el-button {
  flex-shrink: 0;
}

.probe-result {
  margin-top: 8px;
}

.ssh-warning {
  margin-bottom: 12px;
}

/* ─────────────────────────────────────────────────────────────────────────
   暗黑模式适配
   ───────────────────────────────────────────────────────────────────────── */
.dark .status-card {
  background: rgba(22, 27, 34, 0.8);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .status-card.status-healthy {
  border-color: rgba(34, 197, 94, 0.3);
  box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.1);
}

.dark .status-card.status-warning {
  border-color: rgba(234, 179, 8, 0.35);
  box-shadow: 0 0 0 1px rgba(234, 179, 8, 0.12);
}

.dark .status-card.status-critical {
  border-color: rgba(239, 68, 68, 0.35);
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.15), 0 2px 12px rgba(239, 68, 68, 0.1);
}

.dark .metric-block,
.dark .health-item,
.dark .info-row-item,
.dark .uplink-row {
  background: rgba(33, 38, 45, 0.6);
}

.dark .metric-block:hover,
.dark .health-item:hover {
  background: rgba(48, 54, 61, 0.6);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.dark .uptime-block {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.12) 0%, rgba(22, 163, 74, 0.06) 100%);
}

.dark .health-item.health-ok {
  background: rgba(34, 197, 94, 0.1);
}

.dark .info-collapse .el-collapse-item__header {
  background: rgba(33, 38, 45, 0.6);
}

.dark .edit-device-dialog .form-section,
.dark .edit-fault-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .edit-device-dialog .form-section-title,
.dark .edit-fault-dialog .form-section-title {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}

.dark .edit-device-dialog .form-section-title .el-icon,
.dark .edit-fault-dialog .form-section-title .el-icon {
  color: #58a6ff;
}

.dark .tabs-wrapper {
  background: rgba(22, 27, 34, 0.8);
  border-color: rgba(48, 54, 61, 0.4);
}

/* ─────────────────────────────────────────────────────────────────────────
   响应式布局
   ───────────────────────────────────────────────────────────────────────── */
@media (max-width: 1024px) {
  .core-metrics {
    grid-template-columns: repeat(2, 1fr);
  }

  .network-health {
    grid-template-columns: repeat(2, 1fr);
  }

  .info-compact-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .device-detail-page {
    padding: 0 12px;
  }

  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .page-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .status-header {
    flex-wrap: wrap;
    gap: 12px;
  }

  .device-identity {
    order: -1;
    width: 100%;
  }

  .device-ip-large {
    font-size: 18px;
  }

  .header-actions {
    margin-left: auto;
  }

  .core-metrics {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .metric-ring {
    width: 60px;
    height: 60px;
  }

  .metric-number {
    font-size: 18px;
  }

  .network-health {
    grid-template-columns: 1fr;
  }

  .quick-actions-bar {
    flex-wrap: wrap;
  }

  .quick-actions-bar .el-button {
    flex: none;
    width: calc(50% - 6px);
  }

  .tabs-wrapper {
    padding: 16px;
  }

  .cost-summary {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .core-metrics {
    grid-template-columns: 1fr;
  }

  .metric-block {
    padding: 16px 12px;
  }

  .quick-actions-bar .el-button {
    width: 100%;
  }
}

/* ===== 接口监控 Tab ===== */
.iface-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.util-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
.util-bar-bg {
  flex: 1;
  height: 6px;
  background: #ebeef5;
  border-radius: 3px;
  overflow: hidden;
  min-width: 40px;
}
.util-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}
.util-text {
  font-size: 11px;
  color: #606266;
  white-space: nowrap;
  min-width: 64px;
  text-align: right;
}
.iface-traffic-panel {
  padding: 8px 16px;
  background: #fafafa;
}
.spark-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.spark-line {
  display: flex;
  align-items: center;
  gap: 8px;
}
.spark-tag {
  font-size: 11px;
  color: #fff;
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
}
.spark-tag.in { background: #409eff; }
.spark-tag.out { background: #67c23a; }
.spark-svg {
  width: 240px;
  height: 40px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.spark-val {
  font-size: 12px;
  color: #303133;
}
.spark-val em {
  color: #909399;
  font-style: normal;
}
.spark-meta {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}
</style>
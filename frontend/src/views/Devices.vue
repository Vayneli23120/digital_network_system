<template>
  <div class="devices-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuDevices') }}</h1>
        <div class="search-box">
          <el-icon class="search-icon"><Search /></el-icon>
          <el-input
            v-model="searchText"
            :placeholder="t('deviceSearchPlaceholder')"
            class="search-input"
            clearable
          />
        </div>
      </div>
      <div class="nav-right">
        <div class="btn-group">
          <button class="nav-action-btn" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            <span>{{ t('deviceAdd') }}</span>
          </button>
          <el-dropdown class="nav-action-dropdown" trigger="click">
            <button class="nav-action-btn export">
              <el-icon><Upload /></el-icon>
              <span>{{ t('actionExport') }}</span>
              <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="exportDevices">
                  <el-icon><Upload /></el-icon>
                  {{ t('deviceExcelExport') }}
                </el-dropdown-item>
                <el-dropdown-item @click="showImportDialog = true">
                  <el-icon><Download /></el-icon>
                  {{ t('deviceExcelImport') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <button class="nav-action-btn secondary" @click="loadDevices" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard - 企业级紧凑卡片 -->
    <section class="stats-dashboard-compact">
      <div class="stats-grid-5">
        <!-- 总设备 -->
        <div class="stat-card-compact total" :class="{ active: activeFilter === '' }" @click="filterByType('')">
          <div class="stat-header">
            <span class="stat-title">{{ t('deviceStatsDeployed') }}</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.totalDeployed }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment reachable" :style="{ width: percent(stats.reachable, stats.totalDeployed) + '%' }"></div>
              <div class="stat-bar-segment unreachable" :style="{ width: percent(stats.unreachable, stats.totalDeployed) + '%' }"></div>
              <div class="stat-bar-segment unknown" v-if="stats.unknown > 0" :style="{ width: percent(stats.unknown, stats.totalDeployed) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator reachable"><span class="indicator-dot"></span>{{ stats.reachable }} {{ t('statusReachable') }}</span>
            <span class="stat-indicator unreachable clickable" @click.stop="filterByReachability('unreachable', '')"><span class="indicator-dot"></span>{{ stats.unreachable }} {{ t('statusUnreachable') }}</span>
          </div>
        </div>
        <!-- UCE -->
        <div class="stat-card-compact uce" :class="{ active: activeFilter === 'uce' && !filterReachability }" @click="filterByType('uce')">
          <div class="stat-header">
            <span class="stat-title">UCE</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ uceStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment reachable" :style="{ width: percent(uceStats.reachable, uceStats.total) + '%' }"></div>
              <div class="stat-bar-segment unreachable" :style="{ width: percent(uceStats.unreachable, uceStats.total) + '%' }"></div>
              <div class="stat-bar-segment unknown" v-if="uceStats.unknown > 0" :style="{ width: percent(uceStats.unknown, uceStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator reachable"><span class="indicator-dot"></span>{{ uceStats.reachable }} {{ t('statusReachable') }}</span>
            <span class="stat-indicator unreachable clickable" @click.stop="filterByReachability('unreachable', 'uce')"><span class="indicator-dot"></span>{{ uceStats.unreachable }} {{ t('statusUnreachable') }}</span>
          </div>
        </div>
        <!-- AP -->
        <div class="stat-card-compact ap" :class="{ active: activeFilter === 'ap' && !filterReachability }" @click="filterByType('ap')">
          <div class="stat-header">
            <span class="stat-title">AP</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ apStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment reachable" :style="{ width: percent(apStats.reachable, apStats.total) + '%' }"></div>
              <div class="stat-bar-segment unreachable" :style="{ width: percent(apStats.unreachable, apStats.total) + '%' }"></div>
              <div class="stat-bar-segment unknown" v-if="apStats.unknown > 0" :style="{ width: percent(apStats.unknown, apStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator reachable"><span class="indicator-dot"></span>{{ apStats.reachable }} {{ t('statusReachable') }}</span>
            <span class="stat-indicator unreachable clickable" @click.stop="filterByReachability('unreachable', 'ap')"><span class="indicator-dot"></span>{{ apStats.unreachable }} {{ t('statusUnreachable') }}</span>
          </div>
        </div>
        <!-- 办公室交换机 -->
        <div class="stat-card-compact office" :class="{ active: activeFilter === 'office_switch' && !filterReachability }" @click="filterByType('office_switch')">
          <div class="stat-header">
            <span class="stat-title">{{ t('deviceTypeOfficeSwitch') }}</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ officeSwitchStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment reachable" :style="{ width: percent(officeSwitchStats.reachable, officeSwitchStats.total) + '%' }"></div>
              <div class="stat-bar-segment unreachable" :style="{ width: percent(officeSwitchStats.unreachable, officeSwitchStats.total) + '%' }"></div>
              <div class="stat-bar-segment unknown" v-if="officeSwitchStats.unknown > 0" :style="{ width: percent(officeSwitchStats.unknown, officeSwitchStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator reachable"><span class="indicator-dot"></span>{{ officeSwitchStats.reachable }} {{ t('statusReachable') }}</span>
            <span class="stat-indicator unreachable clickable" @click.stop="filterByReachability('unreachable', 'office_switch')"><span class="indicator-dot"></span>{{ officeSwitchStats.unreachable }} {{ t('statusUnreachable') }}</span>
          </div>
        </div>
        <!-- 数据中心网络设备 -->
        <div class="stat-card-compact datacenter" :class="{ active: activeFilter === 'datacenter' && !filterReachability }" @click="filterByType('datacenter')">
          <div class="stat-header">
            <span class="stat-title">{{ t('deviceLayerDatacenter') }}</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ datacenterStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment reachable" :style="{ width: percent(datacenterStats.reachable, datacenterStats.total) + '%' }"></div>
              <div class="stat-bar-segment unreachable" :style="{ width: percent(datacenterStats.unreachable, datacenterStats.total) + '%' }"></div>
              <div class="stat-bar-segment unknown" v-if="datacenterStats.unknown > 0" :style="{ width: percent(datacenterStats.unknown, datacenterStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator reachable"><span class="indicator-dot"></span>{{ datacenterStats.reachable }} {{ t('statusReachable') }}</span>
            <span class="stat-indicator unreachable clickable" @click.stop="filterByReachability('unreachable', 'datacenter')"><span class="indicator-dot"></span>{{ datacenterStats.unreachable }} {{ t('statusUnreachable') }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 设备数据面板 - 树形表格 -->
    <section class="data-section">
      <div class="table-header">
        <div class="table-title-row">
          <span class="table-title">
            {{ filterStatus ? getStatusText(filterStatus) + ' ' : '' }}{{ activeFilter ? getFilterLabel(activeFilter) + ' ' : '' }}{{ t('deviceListTitle') }}
          </span>
          <el-tag v-if="filterStatus" size="small" type="danger" closable @close="filterStatus = ''" class="filter-tag">
            {{ getStatusText(filterStatus) }}
          </el-tag>
          <el-tag v-if="activeFilter" size="small" type="primary" closable @close="filterByType('')" class="filter-tag">
            {{ getFilterLabel(activeFilter) }}
          </el-tag>
        </div>
        <span class="table-count">{{ treeData.length }} {{ t('deviceRecords') }}</span>
          <button
            v-if="selectedDevices.length > 0"
            class="nav-action-btn"
            @click="batchBackupSelected"
            style="margin-left: 12px;"
          >
            批量备份 ({{ selectedDevices.length }})
          </button>
      </div>

      <!-- 筛选工具栏 -->
      <div class="filter-bar">
        <el-select v-model="filterDeployStatus" placeholder="部署状态" clearable size="small" style="width: 120px;">
          <el-option label="在用" value="in-use" />
          <el-option label="备用" value="un-used" />
          <el-option label="维护中" value="maintenance" />
          <el-option label="已退役" value="retired" />
        </el-select>
        <el-select v-model="filterVendor" placeholder="厂商" clearable size="small" style="width: 100px;">
          <el-option v-for="v in vendors" :key="v.key" :label="v.name" :value="v.key" />
        </el-select>
        <el-select v-model="filterLocation" placeholder="位置" clearable size="small" style="width: 130px;">
          <el-option v-for="loc in locationList" :key="loc" :label="loc" :value="loc" />
        </el-select>
        <span
          v-if="filterDeployStatus || filterVendor || filterLocation"
          class="filter-clear-btn"
          @click="clearFilters"
        >
          清除筛选
        </span>
      </div>

      <el-table
        ref="tableRef"
        :data="treeData"
        row-key="id"
        class="enterprise-tree-table"
        v-loading="loading"
        :row-class-name="treeRowClassName"
        :header-cell-style="{ background: 'transparent' }"
        :row-style="{ height: '36px' }"
        @selection-change="selectedDevices = $event"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="name" :label="t('deviceName')" min-width="180">
          <template #default="{ row }">
            <router-link :to="`/devices/${row.id}`" class="device-link">
              <span class="device-name">{{ row.name }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="ip" :label="t('deviceIp')" min-width="130">
          <template #default="{ row }">
            <span class="ip-text">{{ row.ip }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="deployment_status" :label="t('deviceDeployment')" width="110" align="center">
          <template #default="{ row }">
            <div :class="['deployment-badge', row.deployment_status]">
              <span>{{ getDeploymentText(row.deployment_status) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="reachability" :label="t('deviceReachability')" min-width="120" align="center">
          <template #default="{ row }">
            <div v-if="row.deployment_status === 'in-use'" :class="['reachability-badge', row.reachability]">
              <span class="status-dot"></span>
              <span class="status-text">{{ getReachabilityText(row.reachability) }}</span>
              <span v-if="row.reachability_latency_ms" class="latency-text">{{ row.reachability_latency_ms }}ms</span>
            </div>
            <span v-else class="empty-cell">--</span>
          </template>
        </el-table-column>
        <el-table-column label="故障" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.active_fault_count > 0" class="fault-badge">{{ row.active_fault_count }}</span>
            <span v-else class="empty-cell">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="model" :label="t('deviceModel')" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="model-text">{{ row.model || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="location" :label="t('deviceLocation')" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="location-text">{{ row.location || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="上次备份" width="110" align="center">
          <template #default="{ row }">
            <span :class="['backup-age-text', backupAgeClass(row.last_backup_time)]">
              {{ formatBackupAge(row.last_backup_time) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="t('deviceAction')" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-group">
              <button class="action-btn backup" @click="backupDevice(row)" title="备份配置">
                <el-icon><Download /></el-icon>
              </button>
              <button class="action-btn edit" @click="editDevice(row)" title="编辑">
                <el-icon><Edit /></el-icon>
              </button>
              <button class="action-btn delete" @click="deleteDevice(row)" title="删除">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 添加/编辑设备对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('editDeviceTitle') : t('addDeviceTitle')" width="650px" class="edit-device-dialog" @close="resetNewDevice">
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Monitor /></el-icon>
            {{ t('deviceBasicInfo') }}
          </div>
          <el-form :model="newDevice" label-width="100px">
            <el-form-item :label="t('deviceName')" required>
              <el-input v-model="newDevice.name" :placeholder="t('editDeviceNamePlaceholder')" :disabled="editMode" />
            </el-form-item>
            <el-form-item :label="t('deviceIp')" required>
              <div class="input-with-btn">
                <el-input v-model="newDevice.ip" :placeholder="t('editDeviceIpPlaceholder')" />
                <el-button size="small" @click="testReachability" :loading="probeLoading.ip" :disabled="!newDevice.ip">
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
              <el-input v-model="newDevice.model" :placeholder="t('editDeviceModelPlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('deviceLocation')">
              <el-input v-model="newDevice.location" :placeholder="t('editDeviceLocationPlaceholder')" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 模块序列号 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Box /></el-icon>
            模块序列号
            <el-button
              v-if="!editMode"
              size="small"
              type="primary"
              style="margin-left: auto;"
              @click="fetchDeviceInfoHandler"
              :loading="probeLoading.fetch"
              :disabled="!newDevice.ip || !newDevice.credential_group || sshDisabled"
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
            <div v-for="(module, index) in newDevice.modules" :key="index" class="module-row">
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
              <el-button type="danger" size="small" :icon="Close" circle @click="removeModule(index)" v-if="newDevice.modules.length > 1" />
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
          <el-form :model="newDevice" label-width="100px">
            <el-form-item :label="t('deviceType')" required>
              <el-select v-model="newDevice.device_type" :placeholder="t('deviceSelectType')">
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
              <el-select v-model="newDevice.vendor">
                <el-option v-for="v in vendors" :key="v.key" :label="v.name" :value="v.key" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceRole')">
              <el-select v-model="newDevice.role">
                <el-option :label="t('deviceRoleAccess')" value="access" />
                <el-option :label="t('deviceRoleDistribution')" value="distribution" />
                <el-option :label="t('deviceRoleCore')" value="core" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceDeploymentStatus')">
              <el-select v-model="newDevice.deployment_status">
                <el-option :label="t('statusInUse')" value="in-use" />
                <el-option :label="t('statusUnUsed')" value="un-used" />
                <el-option :label="t('statusMaintenance')" value="maintenance" />
                <el-option :label="t('statusRetired')" value="retired" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceCredentialGroup')">
              <div class="input-with-btn">
                <el-select v-model="newDevice.credential_group" :placeholder="t('deviceSelectCredential')">
                  <el-option label="default" value="default" />
                  <el-option v-for="cred in credentialGroups" :key="cred.id" :label="cred.name" :value="cred.name" />
                </el-select>
                <el-button size="small" @click="testConnection" :loading="probeLoading.connection" :disabled="!newDevice.ip || !newDevice.credential_group || sshDisabled">
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
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateDevice() : addDevice()" :loading="submitLoading">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 导入设备对话框 -->
    <el-dialog v-model="showImportDialog" :title="t('deviceImportTitle')" width="600px">
      <el-alert
        :title="t('deviceImportDesc')"
        type="info"
        :closable="false"
        style="margin-bottom: 15px"
      >
        <p>{{ t('deviceImportTip') }}</p>
        <ul style="margin: 10px 0; padding-left: 20px">
          <li>{{ t('deviceImportName') }}</li>
          <li>{{ t('deviceImportIp') }}</li>
          <li>{{ t('deviceImportModel') }}</li>
          <li>{{ t('deviceImportSerial') }}</li>
          <li>{{ t('deviceImportLocation') }}</li>
          <li>{{ t('deviceImportRole') }}</li>
          <li>{{ t('deviceImportStatus') }}</li>
          <li>{{ t('deviceImportCredGroup') }}</li>
          <li><strong>device_type</strong> (必填): uce / office_switch / ap / wlc / core_switch / server_switch / router / pa / ftd / other</li>
        </ul>
      </el-alert>
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx,.csv"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          {{ t('deviceUploadDrag') }}
        </div>
        <template #tip>
          <div class="el-upload__tip">
            {{ t('deviceUploadTip') }}
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showImportDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="importDevices" :disabled="!selectedFile">{{ t('deviceConfirmImport') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus, Upload, UploadFilled, Monitor, CircleCheck, CircleClose, Setting, WarningFilled, Refresh, Search, View, Edit, Delete, ArrowRight, ArrowDown, Connection, Location, Warning, Box, Close } from '@element-plus/icons-vue'
import { getDevices, createDevice, updateDevice as updateDeviceApi, deleteDevice as deleteDeviceApi, backupDevice as backupDeviceApi, batchBackup as batchBackupApi, getCredentials, exportDevices as exportDevicesApi, importDevices as importDevicesApi, getVendors, testDeviceReachability, testDeviceConnection, fetchDeviceInfo } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { debounce, throttle } from '@/utils/requestManager.js'
import { cachedRequest, clearCache } from '@/utils/cache.js'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const devices = ref([])
const tableRef = ref(null)  // el-table ref
const searchText = ref('')
const filterStatus = ref('')
const filterReachability = ref('')  // 新字段：可达性筛选
const filterRole = ref('')
const filterDeployStatus = ref('')
const filterVendor = ref('')
const filterLocation = ref('')

// 从设备数据动态提取位置列表
const locationList = computed(() => {
  const locs = new Set(devices.value.map(d => d.location).filter(Boolean))
  return Array.from(locs).sort()
})

const clearFilters = () => {
  filterDeployStatus.value = ''
  filterVendor.value = ''
  filterLocation.value = ''
}

const activeFilter = ref('') // 统计卡片筛选激活状态
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const editMode = ref(false)
const selectedDevices = ref([])
const credentialGroups = ref([])
const selectedFile = ref(null)
const vendors = ref([])

// 设备探测状态
const probeLoading = ref({
  ip: false,
  connection: false,
  fetch: false
})

const submitLoading = ref(false)

const probeResult = ref({
  ip: null,
  connection: null
})

// SSH能力判断
const sshDisabled = computed(() => {
  // AP设备不支持SSH
  return newDevice.value.device_type === 'ap'
})

const sshSpecialPermission = computed(() => {
  // 防火墙需要GoVault权限
  return ['pa', 'ftd'].includes(newDevice.value.device_type)
})

// 设备层级类型映射
const datacenterTypes = ['core_switch', 'server_switch', 'router', 'pa', 'ftd']
const wifiTypes = ['ap', 'wlc']
const accessTypes = ['uce', 'office_switch']

const newDevice = ref({
  name: '',
  ip: '',
  model: '',
  location: '',
  device_type: 'other',
  role: 'access',
  deployment_status: 'un-used',  // 新字段
  vendor: 'cisco',
  credential_group: 'default',
  modules: [{ type: 'main', pid: '', serial_number: '' }] // 默认一个主机模块
})

// 模块管理
const addModule = () => {
  newDevice.value.modules.push({ type: 'other', pid: '', serial_number: '' })
}

const removeModule = (index) => {
  newDevice.value.modules.splice(index, 1)
}

// 设备探测函数
const testReachability = async () => {
  if (!newDevice.value.ip) return
  probeLoading.value.ip = true
  probeResult.value.ip = null
  try {
    const result = await testDeviceReachability(newDevice.value.ip)
    probeResult.value.ip = result
  } catch (error) {
    probeResult.value.ip = { reachable: false, message: '测试失败: ' + (error.response?.data?.detail || error.message) }
  } finally {
    probeLoading.value.ip = false
  }
}

const testConnection = async () => {
  if (!newDevice.value.ip || !newDevice.value.credential_group) return
  probeLoading.value.connection = true
  probeResult.value.connection = null
  try {
    const result = await testDeviceConnection(
      newDevice.value.ip,
      newDevice.value.credential_group,
      newDevice.value.vendor,
      newDevice.value.device_type
    )
    probeResult.value.connection = result
  } catch (error) {
    probeResult.value.connection = { connected: false, message: '连接失败: ' + (error.response?.data?.detail || error.message) }
  } finally {
    probeLoading.value.connection = false
  }
}

const fetchDeviceInfoHandler = async () => {
  if (!newDevice.value.ip || !newDevice.value.credential_group) return
  probeLoading.value.fetch = true
  try {
    const result = await fetchDeviceInfo(
      newDevice.value.ip,
      newDevice.value.credential_group,
      newDevice.value.vendor,
      newDevice.value.device_type
    )
    if (result.success) {
      // 自动填充设备信息
      if (result.model) newDevice.value.model = result.model
      if (result.serial_number && newDevice.value.modules.length > 0) {
        newDevice.value.modules[0].serial_number = result.serial_number
      }
      if (result.location) newDevice.value.location = result.location
      // 添加获取到的模块信息
      if (result.modules && result.modules.length > 0) {
        // 清空现有模块，用获取到的模块替换
        newDevice.value.modules = result.modules
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

const resetNewDevice = () => {
  newDevice.value = {
    name: '',
    ip: '',
    model: '',
    location: '',
    device_type: 'other',
    role: 'access',
    deployment_status: 'un-used',  // 新字段
    vendor: 'cisco',
    credential_group: 'default',
    modules: [{ type: 'main', pid: '', serial_number: '' }]
  }
  // 重置探测状态
  probeResult.value = { ip: null, connection: null }
  editMode.value = false
}

// 格式化备份时间为「X小时前」或「X天前」
const formatBackupAge = (isoTime) => {
  if (!isoTime) return '从未'
  const hours = (Date.now() - new Date(isoTime)) / 3600000
  if (hours < 1) return '1小时内'
  if (hours < 24) return `${Math.floor(hours)}小时前`
  return `${Math.floor(hours / 24)}天前`
}

// 根据备份时间返回 CSS class
const backupAgeClass = (isoTime) => {
  if (!isoTime) return 'backup-never'
  const hours = (Date.now() - new Date(isoTime)) / 3600000
  if (hours < 24) return 'backup-fresh'
  if (hours < 168) return 'backup-warn'
  return 'backup-stale'
}

// 百分比计算函数
const percent = (value, total) => {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

// 统计数据 - 总设备（只统计已部署设备的可达性）
const stats = computed(() => {
  const deployedList = devices.value.filter(d => d.deployment_status === 'in-use')
  return {
    total: devices.value.length,  // 全设备总数
    totalDeployed: deployedList.length,  // 已部署设备
    reachable: deployedList.filter(d => d.reachability === 'reachable').length,
    unreachable: deployedList.filter(d => d.reachability === 'unreachable').length,
    unknown: deployedList.filter(d => d.reachability === 'unknown').length,
    // 部署状态统计
    deployment: {
      in_use: devices.value.filter(d => d.deployment_status === 'in-use').length,
      un_used: devices.value.filter(d => d.deployment_status === 'un-used').length,
      maintenance: devices.value.filter(d => d.deployment_status === 'maintenance').length,
      retired: devices.value.filter(d => d.deployment_status === 'retired').length,
    },
    // 兼容旧字段
    online: deployedList.filter(d => d.reachability === 'reachable').length,
    offline: deployedList.filter(d => d.reachability === 'unreachable').length,
  }
})

// UCE 统计（只统计已部署设备）
const uceStats = computed(() => {
  const deployedList = devices.value.filter(d => d.device_type === 'uce' && d.deployment_status === 'in-use')
  return {
    total: deployedList.length,
    reachable: deployedList.filter(d => d.reachability === 'reachable').length,
    unreachable: deployedList.filter(d => d.reachability === 'unreachable').length,
    unknown: deployedList.filter(d => d.reachability === 'unknown').length,
    // 兼容旧字段
    online: deployedList.filter(d => d.reachability === 'reachable').length,
    offline: deployedList.filter(d => d.reachability === 'unreachable').length,
    maintenance: deployedList.filter(d => d.deployment_status === 'maintenance').length
  }
})

// AP 统计（只统计已部署设备）
const apStats = computed(() => {
  const deployedList = devices.value.filter(d => d.device_type === 'ap' && d.deployment_status === 'in-use')
  return {
    total: deployedList.length,
    reachable: deployedList.filter(d => d.reachability === 'reachable').length,
    unreachable: deployedList.filter(d => d.reachability === 'unreachable').length,
    unknown: deployedList.filter(d => d.reachability === 'unknown').length,
    // 兼容旧字段
    online: deployedList.filter(d => d.reachability === 'reachable').length,
    offline: deployedList.filter(d => d.reachability === 'unreachable').length,
    maintenance: deployedList.filter(d => d.deployment_status === 'maintenance').length
  }
})

// 办公室交换机统计（只统计已部署设备）
const officeSwitchStats = computed(() => {
  const deployedList = devices.value.filter(d => d.device_type === 'office_switch' && d.deployment_status === 'in-use')
  return {
    total: deployedList.length,
    reachable: deployedList.filter(d => d.reachability === 'reachable').length,
    unreachable: deployedList.filter(d => d.reachability === 'unreachable').length,
    unknown: deployedList.filter(d => d.reachability === 'unknown').length,
    // 兼容旧字段
    online: deployedList.filter(d => d.reachability === 'reachable').length,
    offline: deployedList.filter(d => d.reachability === 'unreachable').length,
    maintenance: deployedList.filter(d => d.deployment_status === 'maintenance').length
  }
})

// 数据中心网络设备统计（只统计已部署设备）
const datacenterStats = computed(() => {
  const deployedList = devices.value.filter(d => datacenterTypes.includes(d.device_type) && d.deployment_status === 'in-use')
  return {
    total: deployedList.length,
    reachable: deployedList.filter(d => d.reachability === 'reachable').length,
    unreachable: deployedList.filter(d => d.reachability === 'unreachable').length,
    unknown: deployedList.filter(d => d.reachability === 'unknown').length,
    // 兼容旧字段
    online: deployedList.filter(d => d.reachability === 'reachable').length,
    offline: deployedList.filter(d => d.reachability === 'unreachable').length,
    maintenance: deployedList.filter(d => d.deployment_status === 'maintenance').length
  }
})

// 构建设备列表数据（扁平列表，无树形分组）
const treeData = computed(() => {
  let list = searchText.value
    ? devices.value.filter(d =>
        d.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
        d.ip?.includes(searchText.value)
      )
    : devices.value

  // 统计卡片类型筛选
  if (activeFilter.value) {
    if (activeFilter.value === 'datacenter') {
      list = list.filter(d => datacenterTypes.includes(d.device_type))
    } else {
      list = list.filter(d => d.device_type === activeFilter.value)
    }
  }

  // 可达性筛选（点击不可达数字）
  if (filterReachability.value) {
    list = list.filter(d => d.reachability === filterReachability.value)
  }

  // 状态筛选（点击离线/维护数字）
  if (filterStatus.value) {
    list = list.filter(d => d.status === filterStatus.value)
  }

  // 筛选工具栏条件
  if (filterDeployStatus.value) {
    list = list.filter(d => d.deployment_status === filterDeployStatus.value)
  }
  if (filterVendor.value) {
    list = list.filter(d => d.vendor === filterVendor.value)
  }
  if (filterLocation.value) {
    list = list.filter(d => d.location === filterLocation.value)
  }

  // 直接返回扁平设备列表
  return list.map(d => ({ ...d }))
})

// 表格行样式
const treeRowClassName = ({ row }) => {
  if (row.reachability === 'unreachable') return 'offline-row'
  return ''
}

const getStatusText = (status) => {
  const texts = { online: t('statusOnline'), offline: t('statusOffline'), maintenance: t('statusMaintenance'), retired: t('statusRetired') }
  return texts[status] || status
}

const getDeploymentText = (deployment_status) => {
  const texts = {
    'in-use': t('statusInUse'),
    'un-used': t('statusUnUsed'),
    'maintenance': t('statusMaintenance'),
    'retired': t('statusRetired')
  }
  return texts[deployment_status] || deployment_status
}

const getReachabilityText = (reachability) => {
  const texts = {
    reachable: t('statusReachable'),
    unreachable: t('statusUnreachable'),
    unknown: t('statusUnknown')
  }
  return texts[reachability] || reachability
}

const handleSelectionChange = (selection) => {
  selectedDevices.value = selection.map(d => d.id)
}

const loadDevices = debounce(async (force = false) => {
  loading.value = true
  try {
    const params = { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
    const data = await cachedRequest(
      () => getDevices(params),
      'devices',
      params,
      { forceRefresh: force }
    )
    devices.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('msgDeviceListFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

const loadCredentialGroups = async () => {
  try {
    const data = await getCredentials()
    credentialGroups.value = data.items || data || []
  } catch (error) {
    ElMessage.error(t('msgCredentialListFailed'))
  }
}

const viewDevice = (id) => {
  router.push(`/devices/${id}`)
}

const backupDevice = async (row) => {
  try {
    await backupDeviceApi(row.id, 'Web')
    ElMessage.success(t('msgBackupSuccess', { name: row.name }))
    loadDevices()
  } catch (error) {
    ElMessage.error(t('msgBackupFailed'))
  }
}

const batchBackupSelected = async () => {
  const ids = selectedDevices.value.map(d => d.id)
  if (ids.length === 0) return
  try {
    await batchBackupApi(ids)
    ElMessage.success(`已触发 ${ids.length} 台设备备份任务`)
    selectedDevices.value = []
  } catch {
    ElMessage.error('批量备份触发失败')
  }
}

const batchBackup = async () => {
  if (selectedDevices.value.length === 0) return

  try {
    await ElMessageBox.confirm(t('confirmBackupSelected', { count: selectedDevices.value.length }), t('confirmBatchBackup'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await batchBackupApi(selectedDevices.value, 'Web')
    ElMessage.success(t('msgBatchBackupSuccess'))
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgBatchBackupFailed'))
    }
  }
}

const editDevice = (row) => {
  editMode.value = true
  // 解析 modules 数据（兼容旧数据无 pid 字段）
  const modules = row.modules || [{ type: 'main', pid: '', serial_number: '' }]
  // 确保每个模块都有 pid 字段
  const normalizedModules = modules.map(m => ({
    type: m.type || 'other',
    pid: m.pid || '',
    serial_number: m.serial_number || ''
  }))
  newDevice.value = {
    ...row,
    modules: Array.isArray(normalizedModules) && normalizedModules.length > 0 ? normalizedModules : [{ type: 'main', pid: '', serial_number: '' }]
  }
  showAddDialog.value = true
}

const updateDevice = async () => {
  submitLoading.value = true
  try {
    const updateData = {
      id: newDevice.value.id,
      name: newDevice.value.name,
      ip: newDevice.value.ip,
      model: newDevice.value.model,
      location: newDevice.value.location,
      role: newDevice.value.role,
      deployment_status: newDevice.value.deployment_status,  // 新字段
      credential_group: newDevice.value.credential_group,
      modules: newDevice.value.modules
    }
    await updateDeviceApi(newDevice.value.id, updateData)
    clearCache('devices')  // 清除缓存
    ElMessage.success(t('msgDeviceUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    loadDevices(true)  // 强制刷新
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('msgDeviceUpdateFailed'))
  } finally {
    submitLoading.value = false
  }
}

const deleteDevice = async (row) => {
  try {
    await ElMessageBox.confirm(t('confirmDeleteDevice', { name: row.name }), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteDeviceApi(row.id)
    clearCache('devices')  // 清除缓存
    ElMessage.success(t('msgDeviceDeleteSuccess'))
    loadDevices(true)  // 强制刷新
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgDeviceDeleteFailed'))
    }
  }
}

const addDevice = async () => {
  submitLoading.value = true
  try {
    await createDevice(newDevice.value)
    clearCache('devices')  // 清除缓存
    ElMessage.success(t('msgDeviceAddSuccess'))
    showAddDialog.value = false
    loadDevices(true)  // 强制刷新
  } catch (error) {
    ElMessage.error(t('msgDeviceAddFailed'))
  } finally {
    submitLoading.value = false
  }
}

const exportDevices = async () => {
  try {
    const blob = await exportDevicesApi()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `devices-${new Date().toISOString().split('T')[0]}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success(t('msgExportSuccess'))
  } catch (error) {
    ElMessage.error(t('msgExportFailed'))
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const importDevices = async () => {
  if (!selectedFile.value) {
    ElMessage.warning(t('msgImportSelectFile'))
    return
  }

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const result = await importDevicesApi(formData)
    ElMessage.success(t('msgImportSuccess', { success: result.success, failed: result.failed }))
    showImportDialog.value = false
    selectedFile.value = null
    loadDevices()
    loadCredentialGroups()
  } catch (error) {
    ElMessage.error(t('msgImportFailed'))
    ElMessage.error(error.response?.data?.detail || t('msgImportFailed'))
  }
}

const loadVendors = async () => {
  try {
    const res = await getVendors()
    vendors.value = res.vendors || []
  } catch (e) {
    console.error(t('msgVendorListFailed'), e)
  }
}

// 卡片点击导航函数
const scrollToTable = () => {
  const tableSection = document.querySelector('.data-section')
  if (tableSection) {
    tableSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 统计卡片筛选
const filterByType = (type) => {
  activeFilter.value = type
  filterStatus.value = '' // 清除旧状态筛选
  filterReachability.value = '' // 清除可达性筛选
  scrollToTable()
}

// 按状态筛选（点击离线数字）
const filterByStatus = (status, type) => {
  filterStatus.value = status
  activeFilter.value = type
  scrollToTable()
}

// 按可达性筛选（点击不可达数字）
const filterByReachability = (reachability, type) => {
  filterReachability.value = reachability
  activeFilter.value = type
  filterStatus.value = '' // 清除旧状态筛选
  scrollToTable()
}

// 获取筛选类型显示名称
const getFilterLabel = (type) => {
  const labels = {
    'uce': 'UCE',
    'ap': 'AP',
    'office_switch': t('deviceTypeOfficeSwitch'),
    'datacenter': t('deviceLayerDatacenter')
  }
  return labels[type] || type
}

onMounted(() => {
  loadDevices()
  loadCredentialGroups()
  loadVendors()
})
</script>

<style scoped>
/* 字体清晰度优化 - 所有等宽字体 */
.device-no-badge,
.metric-value,
.chip-count,
.table-count,
.ip-text,
.status-text {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ===== 页面整体背景 ===== */
.devices-page {
  padding: 0;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f8fafc 0%, #e8f4fc 50%, #f0f7ff 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 页面顶部导航条 ===== */
.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.06);
  position: relative;
  overflow: hidden;
}

.page-nav-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.nav-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 按钮组 - 统一风格 */
.btn-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.nav-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
  height: 36px;
  white-space: nowrap;
}

.nav-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
}

.nav-action-btn.secondary {
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  box-shadow: none;
  padding: 8px 12px;
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

/* Export 按钮 - 与 Add Device 完全一致 */
.nav-action-btn.export {
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
}

.nav-action-btn.export:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
}

.nav-action-btn.export .dropdown-arrow {
  margin-left: 4px;
  font-size: 12px;
  opacity: 0.8;
}

/* 下拉菜单容器样式 */
.nav-action-dropdown {
  display: flex;
}

.nav-action-dropdown :deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-action-dropdown :deep(.el-dropdown-menu__item .el-icon) {
  font-size: 14px;
}

.nav-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 统计 Dashboard - 企业级紧凑卡片 ===== */
.stats-dashboard-compact {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.06);
}

.stats-grid-5 {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.stat-card-compact {
  display: flex;
  flex-direction: column;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  transition: all 0.25s ease;
  cursor: pointer;
}

.stat-card-compact:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 48, 135, 0.08);
}

.stat-card-compact.active {
  border: 2px solid #0984e3;
  box-shadow: 0 4px 16px rgba(9, 132, 227, 0.25);
  background: rgba(9, 132, 227, 0.08);
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.stat-title {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.02em;
}

.stat-body {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.stat-bar-container {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  background: rgba(148, 163, 184, 0.1);
  display: flex;
}

.stat-bar-segment {
  height: 100%;
  transition: width 0.4s ease;
}

.stat-bar-segment.reachable { background: #00b894; }
.stat-bar-segment.unreachable { background: #d63031; }
.stat-bar-segment.unknown { background: #94a3b8; }
.stat-bar-segment.maintenance { background: #e17055; }
/* 兼容旧字段 */
.stat-bar-segment.online { background: #00b894; }
.stat-bar-segment.offline { background: #d63031; }

.stat-footer {
  display: flex;
  gap: 8px;
}

.stat-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  background: rgba(248, 250, 252, 0.8);
}

.stat-indicator .indicator-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.stat-indicator.reachable .indicator-dot { background: #00b894; }
.stat-indicator.unreachable .indicator-dot { background: #d63031; }
.stat-indicator.unknown .indicator-dot { background: #94a3b8; }
.stat-indicator.maintenance .indicator-dot { background: #e17055; }
/* 兼容旧字段 */
.stat-indicator.online .indicator-dot { background: #00b894; }
.stat-indicator.offline .indicator-dot { background: #d63031; }

.stat-indicator.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 6px;
}

.stat-indicator.clickable:hover {
  background: rgba(214, 48, 49, 0.12);
  color: #d63031;
  transform: scale(1.05);
}

.stat-indicator.maintenance.clickable:hover {
  background: rgba(225, 112, 85, 0.12);
  color: #e17055;
}

/* 卡片类型特定样式 */
.stat-card-compact.total .stat-value { color: #0984e3; }
.stat-card-compact.uce .stat-value { color: #e17055; }
.stat-card-compact.ap .stat-value { color: #00b894; }
.stat-card-compact.office .stat-value { color: #f59e0b; }
.stat-card-compact.datacenter .stat-value { color: #0984e3; }

/* ===== 数据面板 ===== */
.data-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.08);
}

.table-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-tag {
  cursor: pointer;
}

.table-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.table-count {
  font-size: 12px;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

/* ===== DNAC风格树形表格 ===== */
.enterprise-tree-table {
  width: 100%;
  --dnac-header-bg: #f5f7fa;
  --dnac-row-hover: #e8f4f8;
  --dnac-border: #e4e7eb;
  --dnac-text: #1d2129;
  --dnac-text-secondary: #86909c;
  --dnac-success: #00b42a;
  --dnac-danger: #f53f3f;
  --dnac-warning: #ff7d00;
  --dnac-info: #165dff;
}

.enterprise-tree-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

/* 表格单元格内部容器 */
.enterprise-tree-table :deep(.cell) {
  padding: 0 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
}

/* 表头 - DNAC风格 */
.enterprise-tree-table :deep(th.el-table__cell) {
  background: var(--dnac-header-bg) !important;
  font-size: 12px;
  font-weight: 500;
  color: var(--dnac-text-secondary);
  padding: 10px 0;
  border-bottom: 1px solid var(--dnac-border);
  text-transform: none;
}

/* 数据单元格 */
.enterprise-tree-table :deep(td.el-table__cell) {
  border-bottom: 1px solid var(--dnac-border);
  padding: 8px 0;
  background: transparent;
  color: var(--dnac-text);
}

/* 行hover效果 */
.enterprise-tree-table :deep(.el-table__row) {
  transition: background 0.15s ease;
}

.enterprise-tree-table :deep(.el-table__row:hover > td) {
  background: var(--dnac-row-hover) !important;
}

/* 设备链接 - DNAC风格 */
.device-link {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--dnac-info);
  text-decoration: none;
  transition: color 0.15s;
}

.device-link:hover {
  color: #4080ff;
}

.device-name {
  font-size: 13px;
  font-weight: 400;
}

.link-arrow {
  opacity: 0;
  font-size: 12px;
  transition: opacity 0.15s;
}

.device-link:hover .link-arrow {
  opacity: 1;
}

/* 空单元格 */
.empty-cell {
  color: var(--dnac-text-secondary);
  font-size: 13px;
}

/* IP单元格 */
.ip-text {
  font-size: 13px;
  color: var(--dnac-text);
}

/* 型号/位置 */
.model-text, .location-text {
  font-size: 13px;
  color: var(--dnac-text);
}

/* DNAC风格状态指示 - 简洁圆点 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border-radius: 0;
  font-size: 13px;
  font-weight: 400;
  background: transparent;
  border: none;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-badge.online { color: var(--dnac-text); }
.status-badge.online .status-dot { background: var(--dnac-success); }
.status-badge.offline { color: var(--dnac-text); }
.status-badge.offline .status-dot { background: var(--dnac-danger); }
.status-badge.maintenance { color: var(--dnac-text); }
.status-badge.maintenance .status-dot { background: var(--dnac-warning); }
.status-badge.retired { color: var(--dnac-text-secondary); }
.status-badge.retired .status-dot { background: var(--dnac-text-secondary); }

/* 部署状态 - DNAC简洁标签 */
.deployment-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 400;
  white-space: nowrap;
}

.deployment-badge.in-use {
  background: rgba(0, 180, 42, 0.1);
  color: var(--dnac-success);
}

.deployment-badge.un-used {
  background: rgba(134, 144, 156, 0.1);
  color: var(--dnac-text-secondary);
}

.deployment-badge.maintenance {
  background: rgba(255, 125, 0, 0.1);
  color: var(--dnac-warning);
}

.deployment-badge.retired {
  background: rgba(22, 93, 255, 0.1);
  color: var(--dnac-info);
}

/* 可达性状态 - DNAC简洁风格 */
.reachability-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border-radius: 0;
  font-size: 13px;
  font-weight: 400;
  background: transparent;
  border: none;
}

.reachability-badge.reachable {
  color: var(--dnac-text);
}

.reachability-badge.reachable .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--dnac-success);
}

.reachability-badge.unreachable {
  color: var(--dnac-text);
}

.reachability-badge.unreachable .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--dnac-danger);
}

.reachability-badge.unknown {
  color: var(--dnac-text-secondary);
}

.reachability-badge.unknown .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--dnac-text-secondary);
}

.reachability-badge .latency-text {
  font-size: 12px;
  color: var(--dnac-text-secondary);
}

/* 操作按钮 - DNAC简洁图标 */
.action-group {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.action-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: var(--dnac-text-secondary);
  cursor: pointer;
  transition: color 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: transparent;
  transform: none;
  box-shadow: none;
}

.action-btn.backup:hover { color: var(--dnac-success); }
.action-btn.edit:hover { color: var(--dnac-info); }
.action-btn.delete:hover { color: var(--dnac-danger); }

/* 搜索框 */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #64748b;
  font-size: 14px;
  z-index: 1;
}

.search-input {
  width: 240px;
}

.search-input :deep(.el-input__wrapper) {
  padding-left: 36px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: none;
}

.search-input :deep(.el-input__wrapper:hover),
.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #0984e3;
  box-shadow: 0 0 0 3px rgba(9, 132, 227, 0.1);
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .stats-grid-5 { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 768px) {
  .stats-grid-5 { grid-template-columns: repeat(2, 1fr); }
  .nav-left { flex-direction: column; align-items: flex-start; }
  .search-input { width: 100%; }
}

/* ===== 暗黑模式 - DNAC风格 ===== */
.dark .devices-page {
  background: #1d2129;
}

.dark .page-nav-bar {
  background: #232730;
  border-color: #3d4451;
}

.dark .page-title { color: #c9cdd4; }

.dark .nav-action-btn {
  background: var(--dnac-info);
}

.dark .nav-action-btn.secondary {
  background: #3d4451;
  color: #86909c;
  border-color: #4e5766;
}

.dark .stats-dashboard-compact {
  background: #232730;
  border-color: #3d4451;
}

.dark .stat-card-compact {
  background: #1d2129;
  border-color: #3d4451;
}

.dark .stat-title { color: #86909c; }
.dark .stat-value { color: #c9cdd4; }
.dark .stat-card-compact.total .stat-value { color: var(--dnac-info); }
.dark .stat-card-compact.uce .stat-value { color: var(--dnac-warning); }
.dark .stat-card-compact.ap .stat-value { color: var(--dnac-success); }
.dark .stat-card-compact.office .stat-value { color: #ff7d00; }
.dark .stat-card-compact.datacenter .stat-value { color: var(--dnac-info); }

.dark .stat-card-compact.active {
  border: 1px solid var(--dnac-info);
  background: rgba(22, 93, 255, 0.1);
}

.dark .stat-bar-container { background: #3d4451; }
.dark .stat-indicator { background: #3d4451; color: #86909c; }

.dark .search-input :deep(.el-input__wrapper) {
  background: #1d2129;
  border-color: #3d4451;
}

.dark .search-icon { color: #86909c; }

.dark .data-section {
  background: #232730;
  border-color: #3d4451;
}

.dark .table-title { color: #c9cdd4; }
.dark .table-count { color: #86909c; }

/* DNAC暗黑表格 */
.dark .enterprise-tree-table {
  --dnac-header-bg: #232730;
  --dnac-border: #3d4451;
  --dnac-text: #c9cdd4;
  --dnac-text-secondary: #86909c;
  --dnac-row-hover: #2d333b;
}

.dark .enterprise-tree-table :deep(.cell) { color: #c9cdd4; }

.dark .device-link { color: var(--dnac-info); }
.dark .device-link:hover { color: #4080ff; }
.dark .device-name { color: #c9cdd4; }

.dark .empty-cell { color: #86909c; }
.dark .ip-text, .dark .model-text, .dark .location-text { color: #c9cdd4; }

.dark .filter-bar {
  background: #232730;
}

.dark .filter-clear-btn { color: var(--dnac-info); }

/* 编辑对话框 */
.dark .form-section {
  background: #1d2129;
  border-color: #3d4451;
}

.dark .form-section-title { color: #86909c; }

/* ===== 设备探测 UI ===== */
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

/* ===== 编辑对话框 ===== */
.edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 16px;
  border: 1px solid #e4e7eb;
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--dnac-text);
  margin-bottom: 12px;
}

.modules-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.module-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 活跃故障数 - DNAC简洁数字 */
.fault-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  background: var(--dnac-danger);
  color: #fff;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

/* 上次备份 - DNAC简洁文字 */
.backup-age-text {
  font-size: 13px;
  white-space: nowrap;
}
.backup-fresh    { color: var(--dnac-success); }
.backup-warn     { color: var(--dnac-warning); }
.backup-stale    { color: var(--dnac-danger); }
.backup-never    { color: var(--dnac-text-secondary); }

/* 筛选工具栏 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  flex-wrap: wrap;
  background: var(--dnac-header-bg);
  border-radius: 4px;
  margin-bottom: 8px;
}

.filter-clear-btn {
  font-size: 13px;
  color: var(--dnac-info);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: color 0.15s;
}

.filter-clear-btn:hover {
  color: var(--dnac-danger);
}
</style>

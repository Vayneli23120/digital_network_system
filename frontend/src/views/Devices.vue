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
        <button class="nav-action-btn" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          <span>{{ t('deviceAdd') }}</span>
        </button>
        <el-dropdown split-button class="nav-action-btn export" @click="exportDevices">
          <el-icon><Upload /></el-icon>
          <span>{{ t('actionExport') }}</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="exportDevices">{{ t('deviceExcelExport') }}</el-dropdown-item>
              <el-dropdown-item @click="showImportDialog = true">{{ t('deviceExcelImport') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
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
            <span class="stat-title">{{ t('deviceStatsTotal') }}</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment online" :style="{ width: percent(stats.online, stats.total) + '%' }"></div>
              <div class="stat-bar-segment offline" :style="{ width: percent(stats.offline, stats.total) + '%' }"></div>
              <div class="stat-bar-segment maintenance" :style="{ width: percent(stats.maintenance, stats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator online"><span class="indicator-dot"></span>{{ stats.online }} 在线</span>
            <span class="stat-indicator offline clickable" @click.stop="filterByStatus('offline', '')"><span class="indicator-dot"></span>{{ stats.offline }} 离线</span>
            <span class="stat-indicator maintenance clickable" @click.stop="filterByStatus('maintenance', '')"><span class="indicator-dot"></span>{{ stats.maintenance }} 维护</span>
          </div>
        </div>
        <!-- UCE -->
        <div class="stat-card-compact uce" :class="{ active: activeFilter === 'uce' && !filterStatus }" @click="filterByType('uce')">
          <div class="stat-header">
            <span class="stat-title">UCE</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ uceStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment online" :style="{ width: percent(uceStats.online, uceStats.total) + '%' }"></div>
              <div class="stat-bar-segment offline" :style="{ width: percent(uceStats.offline, uceStats.total) + '%' }"></div>
              <div class="stat-bar-segment maintenance" :style="{ width: percent(uceStats.maintenance, uceStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator online"><span class="indicator-dot"></span>{{ uceStats.online }} 在线</span>
            <span class="stat-indicator offline clickable" @click.stop="filterByStatus('offline', 'uce')"><span class="indicator-dot"></span>{{ uceStats.offline }} 离线</span>
            <span class="stat-indicator maintenance clickable" @click.stop="filterByStatus('maintenance', 'uce')"><span class="indicator-dot"></span>{{ uceStats.maintenance }} 维护</span>
          </div>
        </div>
        <!-- AP -->
        <div class="stat-card-compact ap" :class="{ active: activeFilter === 'ap' && !filterStatus }" @click="filterByType('ap')">
          <div class="stat-header">
            <span class="stat-title">AP</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ apStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment online" :style="{ width: percent(apStats.online, apStats.total) + '%' }"></div>
              <div class="stat-bar-segment offline" :style="{ width: percent(apStats.offline, apStats.total) + '%' }"></div>
              <div class="stat-bar-segment maintenance" :style="{ width: percent(apStats.maintenance, apStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator online"><span class="indicator-dot"></span>{{ apStats.online }} 在线</span>
            <span class="stat-indicator offline clickable" @click.stop="filterByStatus('offline', 'ap')"><span class="indicator-dot"></span>{{ apStats.offline }} 离线</span>
            <span class="stat-indicator maintenance clickable" @click.stop="filterByStatus('maintenance', 'ap')"><span class="indicator-dot"></span>{{ apStats.maintenance }} 维护</span>
          </div>
        </div>
        <!-- 办公室交换机 -->
        <div class="stat-card-compact office" :class="{ active: activeFilter === 'office_switch' && !filterStatus }" @click="filterByType('office_switch')">
          <div class="stat-header">
            <span class="stat-title">{{ t('deviceTypeOfficeSwitch') }}</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ officeSwitchStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment online" :style="{ width: percent(officeSwitchStats.online, officeSwitchStats.total) + '%' }"></div>
              <div class="stat-bar-segment offline" :style="{ width: percent(officeSwitchStats.offline, officeSwitchStats.total) + '%' }"></div>
              <div class="stat-bar-segment maintenance" :style="{ width: percent(officeSwitchStats.maintenance, officeSwitchStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator online"><span class="indicator-dot"></span>{{ officeSwitchStats.online }} 在线</span>
            <span class="stat-indicator offline clickable" @click.stop="filterByStatus('offline', 'office_switch')"><span class="indicator-dot"></span>{{ officeSwitchStats.offline }} 离线</span>
            <span class="stat-indicator maintenance clickable" @click.stop="filterByStatus('maintenance', 'office_switch')"><span class="indicator-dot"></span>{{ officeSwitchStats.maintenance }} 维护</span>
          </div>
        </div>
        <!-- 数据中心网络设备 -->
        <div class="stat-card-compact datacenter" :class="{ active: activeFilter === 'datacenter' && !filterStatus }" @click="filterByType('datacenter')">
          <div class="stat-header">
            <span class="stat-title">{{ t('deviceLayerDatacenter') }}</span>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ datacenterStats.total }}</span>
            <div class="stat-bar-container">
              <div class="stat-bar-segment online" :style="{ width: percent(datacenterStats.online, datacenterStats.total) + '%' }"></div>
              <div class="stat-bar-segment offline" :style="{ width: percent(datacenterStats.offline, datacenterStats.total) + '%' }"></div>
              <div class="stat-bar-segment maintenance" :style="{ width: percent(datacenterStats.maintenance, datacenterStats.total) + '%' }"></div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-indicator online"><span class="indicator-dot"></span>{{ datacenterStats.online }} 在线</span>
            <span class="stat-indicator offline clickable" @click.stop="filterByStatus('offline', 'datacenter')"><span class="indicator-dot"></span>{{ datacenterStats.offline }} 离线</span>
            <span class="stat-indicator maintenance clickable" @click.stop="filterByStatus('maintenance', 'datacenter')"><span class="indicator-dot"></span>{{ datacenterStats.maintenance }} 维护</span>
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
      </div>

      <el-table
        ref="tableRef"
        :data="treeData"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        class="enterprise-tree-table"
        v-loading="loading"
        :row-class-name="treeRowClassName"
        :header-cell-style="{ background: 'transparent' }"
        default-expand-all
      >
        <el-table-column prop="name" :label="t('deviceName')" min-width="180">
          <template #default="{ row }">
            <template v-if="row.isLayer">
              <div class="layer-row">
                <span class="layer-icon" :class="row.layerClass"></span>
                <span class="layer-name">{{ row.name }}</span>
                <span class="layer-count-badge">{{ row.onlineCount }}/{{ row.totalCount }}</span>
              </div>
            </template>
            <template v-else-if="row.isType">
              <div class="type-row">
                <span class="type-dot" :class="row.layerClass"></span>
                <span class="type-name">{{ row.name }}</span>
                <span class="type-stats">{{ row.onlineCount }} {{ t('statusOnline') }}</span>
              </div>
            </template>
            <template v-else>
              <router-link :to="`/devices/${row.id}`" class="device-link">
                <span class="device-name">{{ row.name }}</span>
                <el-icon class="link-arrow"><ArrowRight /></el-icon>
              </router-link>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="ip" :label="t('deviceIp')" min-width="130">
          <template #default="{ row }">
            <template v-if="!row.isLayer && !row.isType">
              <div class="ip-cell">
                <span class="ip-text">{{ row.ip }}</span>
              </div>
            </template>
            <template v-else>
              <span class="empty-cell">—</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('deviceStatus')" min-width="110" align="center">
          <template #default="{ row }">
            <template v-if="!row.isLayer && !row.isType">
              <div :class="['status-badge', row.status]">
                <span class="status-dot"></span>
                <span class="status-text">{{ getStatusText(row.status) }}</span>
              </div>
            </template>
            <template v-else>
              <span class="empty-cell">—</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="model" :label="t('deviceModel')" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="!row.isLayer && !row.isType">
              <span class="model-text">{{ row.model || '--' }}</span>
            </template>
            <template v-else>
              <span class="empty-cell">—</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="location" :label="t('deviceLocation')" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="!row.isLayer && !row.isType">
              <span class="location-text">{{ row.location || '--' }}</span>
            </template>
            <template v-else>
              <span class="empty-cell">—</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column :label="t('deviceAction')" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <template v-if="!row.isLayer && !row.isType">
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
            <template v-else>
              <span class="empty-cell">—</span>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 添加/编辑设备对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('editDeviceTitle') : t('addDeviceTitle')" width="600px" class="edit-device-dialog" @close="resetNewDevice">
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
              <el-input v-model="newDevice.ip" :placeholder="t('editDeviceIpPlaceholder')" />
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
            {{ t('deviceModules') }}
          </div>
          <div class="modules-container">
            <div v-for="(module, index) in newDevice.modules" :key="index" class="module-row">
              <el-select v-model="module.type" :placeholder="t('deviceModuleType')" size="small" style="width: 140px;">
                <el-option :label="t('deviceMainModule')" value="main" />
                <el-option :label="t('deviceExpansionModule')" value="expansion" />
                <el-option :label="t('devicePowerModule')" value="power" />
                <el-option :label="t('deviceSfpModule')" value="sfp" />
                <el-option :label="t('deviceFanModule')" value="fan" />
                <el-option :label="t('deviceTypeOther')" value="other" />
              </el-select>
              <el-input v-model="module.serial_number" :placeholder="t('deviceModuleSn')" size="small" style="width: 180px;" />
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
            <el-form-item :label="t('deviceStatus')">
              <el-select v-model="newDevice.status">
                <el-option :label="t('statusOnline')" value="online" />
                <el-option :label="t('statusOffline')" value="offline" />
                <el-option :label="t('statusMaintenance')" value="maintenance" />
                <el-option :label="t('statusRetired')" value="retired" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceCredentialGroup')">
              <el-select v-model="newDevice.credential_group" :placeholder="t('deviceSelectCredential')">
                <el-option label="default" value="default" />
                <el-option v-for="cred in credentialGroups" :key="cred.id" :label="cred.name" :value="cred.name" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateDevice() : addDevice()">{{ t('actionConfirm') }}</el-button>
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
import { Download, Plus, Upload, UploadFilled, Monitor, CircleCheck, CircleClose, Setting, WarningFilled, Refresh, Search, View, Edit, Delete, ArrowRight, Connection, Location, Warning, Box, Close } from '@element-plus/icons-vue'
import { getDevices, createDevice, updateDevice as updateDeviceApi, deleteDevice as deleteDeviceApi, backupDevice as backupDeviceApi, batchBackup as batchBackupApi, getCredentials, exportDevices as exportDevicesApi, importDevices as importDevicesApi, getVendors } from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const devices = ref([])
const tableRef = ref(null)  // el-table ref
const searchText = ref('')
const filterStatus = ref('')
const filterRole = ref('')
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
  status: 'online',
  vendor: 'cisco',
  credential_group: 'default',
  modules: [{ type: 'main', serial_number: '' }] // 默认一个主机模块
})

// 模块管理
const addModule = () => {
  newDevice.value.modules.push({ type: 'other', serial_number: '' })
}

const removeModule = (index) => {
  newDevice.value.modules.splice(index, 1)
}

const resetNewDevice = () => {
  newDevice.value = {
    name: '',
    ip: '',
    model: '',
    location: '',
    device_type: 'other',
    role: 'access',
    status: 'online',
    vendor: 'cisco',
    credential_group: 'default',
    modules: [{ type: 'main', serial_number: '' }]
  }
}

// 百分比计算函数
const percent = (value, total) => {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

// 统计数据 - 总设备
const stats = computed(() => {
  const list = devices.value
  return {
    total: list.length,
    online: list.filter(d => d.status === 'online').length,
    offline: list.filter(d => d.status === 'offline').length,
    maintenance: list.filter(d => d.status === 'maintenance').length,
    retired: list.filter(d => d.status === 'retired').length
  }
})

// UCE 统计
const uceStats = computed(() => {
  const list = devices.value.filter(d => d.device_type === 'uce')
  return {
    total: list.length,
    online: list.filter(d => d.status === 'online').length,
    offline: list.filter(d => d.status === 'offline').length,
    maintenance: list.filter(d => d.status === 'maintenance').length
  }
})

// AP 统计
const apStats = computed(() => {
  const list = devices.value.filter(d => d.device_type === 'ap')
  return {
    total: list.length,
    online: list.filter(d => d.status === 'online').length,
    offline: list.filter(d => d.status === 'offline').length,
    maintenance: list.filter(d => d.status === 'maintenance').length
  }
})

// 办公室交换机统计
const officeSwitchStats = computed(() => {
  const list = devices.value.filter(d => d.device_type === 'office_switch')
  return {
    total: list.length,
    online: list.filter(d => d.status === 'online').length,
    offline: list.filter(d => d.status === 'offline').length,
    maintenance: list.filter(d => d.status === 'maintenance').length
  }
})

// 数据中心网络设备统计
const datacenterStats = computed(() => {
  const list = devices.value.filter(d => datacenterTypes.includes(d.device_type))
  return {
    total: list.length,
    online: list.filter(d => d.status === 'online').length,
    offline: list.filter(d => d.status === 'offline').length,
    maintenance: list.filter(d => d.status === 'maintenance').length
  }
})

// 设备类型标签
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
    pa: t('deviceTypePA'),
    ftd: t('deviceTypeFTD'),
    other: t('deviceTypeOther'),
  }
  return map[dtype] || dtype
}

// 构建树形数据
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

  // 状态筛选（点击离线/维护数字）
  if (filterStatus.value) {
    list = list.filter(d => d.status === filterStatus.value)
  }

  // 有筛选时返回扁平列表
  if (activeFilter.value || filterStatus.value) {
    return list.map(d => ({ ...d }))
  }

  // 无筛选时显示树形结构
  const tree = []

  // 数据中心网络设备层级
  const datacenterDevices = list.filter(d => datacenterTypes.includes(d.device_type))
  if (datacenterDevices.length > 0) {
    const datacenterChildren = []
    // 按类型分组
    const typeGroups = {}
    datacenterDevices.forEach(d => {
      if (!typeGroups[d.device_type]) typeGroups[d.device_type] = []
      typeGroups[d.device_type].push(d)
    })
    Object.entries(typeGroups).forEach(([dtype, devs]) => {
      const onlineCount = devs.filter(d => d.status === 'online').length
      datacenterChildren.push({
        id: `type-${dtype}`,
        name: typeLabel(dtype),
        isType: true,
        layerClass: 'datacenter',
        onlineCount,
        totalCount: devs.length,
        children: devs.map(d => ({ ...d, device_type: dtype }))
      })
    })
    tree.push({
      id: 'layer-datacenter',
      name: t('deviceLayerDatacenter'),
      isLayer: true,
      layerClass: 'datacenter',
      onlineCount: datacenterDevices.filter(d => d.status === 'online').length,
      totalCount: datacenterDevices.length,
      children: datacenterChildren
    })
  }

  // 无线网络层级
  const wifiDevices = list.filter(d => wifiTypes.includes(d.device_type))
  if (wifiDevices.length > 0) {
    const wifiChildren = []
    const typeGroups = {}
    wifiDevices.forEach(d => {
      if (!typeGroups[d.device_type]) typeGroups[d.device_type] = []
      typeGroups[d.device_type].push(d)
    })
    Object.entries(typeGroups).forEach(([dtype, devs]) => {
      const onlineCount = devs.filter(d => d.status === 'online').length
      wifiChildren.push({
        id: `type-${dtype}`,
        name: typeLabel(dtype),
        isType: true,
        layerClass: 'wifi',
        onlineCount,
        totalCount: devs.length,
        children: devs.map(d => ({ ...d, device_type: dtype }))
      })
    })
    tree.push({
      id: 'layer-wifi',
      name: t('deviceLayerWiFi'),
      isLayer: true,
      layerClass: 'wifi',
      onlineCount: wifiDevices.filter(d => d.status === 'online').length,
      totalCount: wifiDevices.length,
      children: wifiChildren
    })
  }

  // 接入层层级
  const accessDevices = list.filter(d => accessTypes.includes(d.device_type))
  if (accessDevices.length > 0) {
    const accessChildren = []
    const typeGroups = {}
    accessDevices.forEach(d => {
      if (!typeGroups[d.device_type]) typeGroups[d.device_type] = []
      typeGroups[d.device_type].push(d)
    })
    Object.entries(typeGroups).forEach(([dtype, devs]) => {
      const onlineCount = devs.filter(d => d.status === 'online').length
      accessChildren.push({
        id: `type-${dtype}`,
        name: typeLabel(dtype),
        isType: true,
        layerClass: 'access',
        onlineCount,
        totalCount: devs.length,
        children: devs.map(d => ({ ...d, device_type: dtype }))
      })
    })
    tree.push({
      id: 'layer-access',
      name: t('deviceLayerAccess'),
      isLayer: true,
      layerClass: 'access',
      onlineCount: accessDevices.filter(d => d.status === 'online').length,
      totalCount: accessDevices.length,
      children: accessChildren
    })
  }

  // 其他设备层级
  const otherDevices = list.filter(d =>
    !datacenterTypes.includes(d.device_type) &&
    !wifiTypes.includes(d.device_type) &&
    !accessTypes.includes(d.device_type)
  )
  if (otherDevices.length > 0) {
    tree.push({
      id: 'layer-other',
      name: t('deviceTypeOther'),
      isLayer: true,
      layerClass: 'other',
      onlineCount: otherDevices.filter(d => d.status === 'online').length,
      totalCount: otherDevices.length,
      children: otherDevices.map(d => ({ ...d }))
    })
  }

  return tree
})

// 表格行样式
const treeRowClassName = ({ row }) => {
  if (row.isLayer) return 'layer-row'
  if (row.isType) return 'type-row'
  if (row.status === 'offline') return 'offline-row'
  return ''
}

const getStatusText = (status) => {
  const texts = { online: t('statusOnline'), offline: t('statusOffline'), maintenance: t('statusMaintenance'), retired: t('statusRetired') }
  return texts[status] || status
}

const handleSelectionChange = (selection) => {
  selectedDevices.value = selection.map(d => d.id)
}

const loadDevices = async () => {
  loading.value = true
  try {
    const params = { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
    const data = await getDevices(params)
    devices.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(t('msgDeviceListFailed'))
  } finally {
    loading.value = false
  }
}

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
  // 解析 modules 数据
  const modules = row.modules || [{ type: 'main', serial_number: '' }]
  newDevice.value = {
    ...row,
    modules: Array.isArray(modules) && modules.length > 0 ? modules : [{ type: 'main', serial_number: '' }]
  }
  showAddDialog.value = true
}

const updateDevice = async () => {
  try {
    const updateData = {
      id: newDevice.value.id,
      name: newDevice.value.name,
      ip: newDevice.value.ip,
      model: newDevice.value.model,
      location: newDevice.value.location,
      role: newDevice.value.role,
      status: newDevice.value.status,
      credential_group: newDevice.value.credential_group,
      modules: newDevice.value.modules
    }
    await updateDeviceApi(newDevice.value.id, updateData)
    ElMessage.success(t('msgDeviceUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    loadDevices()
  } catch (error) {
    ElMessage.error(t('msgDeviceUpdateFailed'))
    ElMessage.error(error.response?.data?.detail || t('msgDeviceUpdateFailed'))
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
    ElMessage.success(t('msgDeviceDeleteSuccess'))
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgDeviceDeleteFailed'))
    }
  }
}

const addDevice = async () => {
  try {
    await createDevice(newDevice.value)
    ElMessage.success(t('msgDeviceAddSuccess'))
    showAddDialog.value = false
    loadDevices()
  } catch (error) {
    ElMessage.error(t('msgDeviceAddFailed'))
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
  filterStatus.value = '' // 清除状态筛选
  scrollToTable()
}

// 点击离线/维护数字筛选
const filterByStatus = (status, type) => {
  filterStatus.value = status
  activeFilter.value = type
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

const expandAndScrollTo = (typeOrLayer) => {
  scrollToTable()

  // 根据点击的卡片类型，确定要展开的层级或类型节点
  let targetNodeId = ''

  if (typeOrLayer === 'datacenter') {
    targetNodeId = 'layer-datacenter'
  } else if (typeOrLayer === 'ap' || typeOrLayer === 'wlc') {
    targetNodeId = 'layer-wifi'
  } else if (typeOrLayer === 'uce' || typeOrLayer === 'office_switch') {
    targetNodeId = 'layer-access'
  } else if (typeOrLayer === 'other') {
    targetNodeId = 'layer-other'
  }

  // 等待 DOM 更新后展开节点
  setTimeout(() => {
    if (tableRef.value) {
      // 展开所有节点（因为已经有 default-expand-all）
      // 尝试滚动到特定层级行
      const rows = document.querySelectorAll('.el-table__row')
      rows.forEach(row => {
        // Element Plus 的树形表格会通过 data-row-key 属性标识行
        // 由于层级行带有特殊 class，可以尝试找到它
      })
    }
  }, 100)
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

.nav-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
  color: white;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(9, 132, 227, 0.25);
}

.nav-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(9, 132, 227, 0.35);
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

.nav-action-btn.export {
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  box-shadow: none;
}

.nav-action-btn.export:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
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

.stat-bar-segment.online { background: #00b894; }
.stat-bar-segment.offline { background: #d63031; }
.stat-bar-segment.maintenance { background: #e17055; }

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

.stat-indicator.online .indicator-dot { background: #00b894; }
.stat-indicator.offline .indicator-dot { background: #d63031; }
.stat-indicator.maintenance .indicator-dot { background: #e17055; }

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

/* ===== 树形表格 ===== */
.enterprise-tree-table {
  width: 100%;
}

.enterprise-tree-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.enterprise-tree-table :deep(th.el-table__cell) {
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.03em;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 48, 135, 0.1);
}

.enterprise-tree-table :deep(td.el-table__cell) {
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
  padding: 10px 0;
  background: transparent;
}

.enterprise-tree-table :deep(.el-table__row) {
  transition: all 0.2s ease;
}

.enterprise-tree-table :deep(.el-table__row:hover > td) {
  background: rgba(9, 132, 227, 0.04) !important;
}

/* 层级行样式 */
.enterprise-tree-table :deep(.layer-row) {
  background: rgba(0, 48, 135, 0.04) !important;
}

.enterprise-tree-table :deep(.layer-row > td) {
  background: rgba(0, 48, 135, 0.04) !important;
  border-bottom: 1px solid rgba(0, 48, 135, 0.1);
}

.enterprise-tree-table :deep(.type-row) {
  background: rgba(248, 250, 252, 0.6) !important;
}

/* 层级行内容 */
.layer-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.layer-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.layer-icon.datacenter {
  background: rgba(9, 132, 227, 0.12);
  color: #0984e3;
}

.layer-icon.wifi {
  background: rgba(0, 184, 148, 0.12);
  color: #00b894;
}

.layer-icon.access {
  background: rgba(225, 112, 85, 0.12);
  color: #e17055;
}

.layer-icon.other {
  background: rgba(148, 163, 184, 0.12);
  color: #64748b;
}

.layer-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.layer-count-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(0, 184, 148, 0.12);
  color: #00b894;
}

/* 类型行内容 */
.type-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.type-dot.datacenter { background: #0984e3; }
.type-dot.wifi { background: #00b894; }
.type-dot.access { background: #e17055; }
.type-dot.other { background: #64748b; }

.type-name {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.type-stats {
  font-size: 11px;
  color: #00b894;
  font-weight: 500;
}

/* 设备链接 */
.device-link {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #0984e3;
  text-decoration: none;
  transition: all 0.2s;
}

.device-link:hover {
  color: #74b9ff;
}

.device-name {
  font-size: 13px;
  font-weight: 500;
}

.link-arrow {
  opacity: 0;
  font-size: 12px;
  transition: all 0.2s;
}

.device-link:hover .link-arrow {
  opacity: 1;
  transform: translateX(3px);
}

/* 空单元格 */
.empty-cell {
  color: #94a3b8;
  font-size: 12px;
}

/* IP单元格 */
.ip-text {
  font-size: 13px;
  color: #475569;
  font-family: 'JetBrains Mono', monospace;
}

/* 型号/位置 */
.model-text, .location-text {
  font-size: 13px;
  color: #475569;
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-badge.online { border-color: rgba(0, 184, 148, 0.3); color: #00b894; }
.status-badge.online .status-dot { background: #00b894; }
.status-badge.offline { border-color: rgba(214, 48, 49, 0.3); color: #d63031; }
.status-badge.offline .status-dot { background: #d63031; }
.status-badge.maintenance { border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.status-badge.maintenance .status-dot { background: #e17055; }
.status-badge.retired { border-color: rgba(116, 185, 255, 0.3); color: #74b9ff; }
.status-badge.retired .status-dot { background: #74b9ff; }

/* 操作按钮 */
.action-group {
  display: flex;
  gap: 4px;
  justify-content: center;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.9);
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.12);
}

.action-btn.backup:hover { background: rgba(0, 184, 148, 0.08); color: #00b894; }
.action-btn.edit:hover { background: rgba(245, 158, 11, 0.08); color: #f59e0b; }
.action-btn.delete:hover { background: rgba(214, 48, 49, 0.08); color: #d63031; }

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

/* ===== 暗黑模式 ===== */
.dark .devices-page {
  background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #161b22 100%);
}

.dark .page-nav-bar {
  background: rgba(22, 27, 34, 0.9);
  border-color: rgba(48, 54, 61, 0.8);
}

.dark .page-title { color: #f0f6fc; }

.dark .nav-action-btn { background: linear-gradient(135deg, #0984e3, #74b9ff); }

.dark .nav-action-btn.secondary {
  background: rgba(48, 54, 61, 0.8);
  color: #8b949e;
  border-color: #30363d;
}

.dark .stats-dashboard-compact {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
}

.dark .stat-card-compact {
  background: rgba(13, 17, 23, 0.9);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .stat-title { color: #8b949e; }
.dark .stat-value { color: #f0f6fc; }
.dark .stat-card-compact.total .stat-value { color: #58a6ff; }
.dark .stat-card-compact.uce .stat-value { color: #e17055; }
.dark .stat-card-compact.ap .stat-value { color: #3fb950; }
.dark .stat-card-compact.office .stat-value { color: #d29922; }
.dark .stat-card-compact.datacenter .stat-value { color: #58a6ff; }

.dark .stat-card-compact.active {
  border: 2px solid #58a6ff;
  box-shadow: 0 4px 16px rgba(88, 166, 255, 0.25);
  background: rgba(88, 166, 255, 0.1);
}

.dark .stat-bar-container { background: rgba(48, 54, 61, 0.3); }
.dark .stat-indicator { background: rgba(48, 54, 61, 0.3); color: #8b949e; }

.dark .search-input :deep(.el-input__wrapper) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

.dark .search-icon { color: #8b949e; }

.dark .data-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
}

.dark .table-title { color: #f0f6fc; }
.dark .table-count { color: #8b949e; }

.dark .enterprise-tree-table :deep(th.el-table__cell) { color: #8b949e; }
.dark .enterprise-tree-table :deep(td.el-table__cell) { border-bottom-color: rgba(48, 54, 61, 0.3); }
.dark .enterprise-tree-table :deep(.el-table__row:hover > td) { background: rgba(88, 166, 255, 0.08) !important; }

.dark .enterprise-tree-table :deep(.layer-row > td) { background: rgba(48, 54, 61, 0.2) !important; }
.dark .enterprise-tree-table :deep(.type-row > td) { background: rgba(48, 54, 61, 0.15) !important; }

.dark .layer-icon.datacenter { background: rgba(88, 166, 255, 0.2); color: #58a6ff; }
.dark .layer-icon.wifi { background: rgba(63, 185, 80, 0.2); color: #3fb950; }
.dark .layer-icon.access { background: rgba(225, 112, 85, 0.2); color: #e17055; }

.dark .layer-name { color: #f0f6fc; }
.dark .layer-count-badge { background: rgba(63, 185, 80, 0.2); color: #3fb950; }

.dark .type-dot.datacenter { background: #58a6ff; }
.dark .type-dot.wifi { background: #3fb950; }
.dark .type-dot.access { background: #e17055; }

.dark .type-name { color: #8b949e; }
.dark .type-stats { color: #3fb950; }

.dark .device-link { color: #58a6ff; }
.dark .device-link:hover { color: #74b9ff; }
.dark .device-name { color: #f0f6fc; }

.dark .empty-cell { color: #6e7681; }
.dark .ip-text, .dark .model-text, .dark .location-text { color: #8b949e; }

.dark .status-badge { background: rgba(13, 17, 23, 0.9); }
.dark .status-badge.online { border-color: rgba(63, 185, 80, 0.4); color: #3fb950; }
.dark .status-badge.online .status-dot { background: #3fb950; }
.dark .status-badge.offline { border-color: rgba(248, 81, 73, 0.4); color: #f85149; }
.dark .status-badge.offline .status-dot { background: #f85149; }
.dark .status-badge.maintenance { border-color: rgba(225, 112, 85, 0.4); color: #e17055; }
.dark .status-badge.maintenance .status-dot { background: #e17055; }

.dark .action-btn { background: rgba(13, 17, 23, 0.9); color: #8b949e; }
.dark .action-btn:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); }
.dark .action-btn.backup:hover { background: rgba(63, 185, 80, 0.15); color: #3fb950; }
.dark .action-btn.edit:hover { background: rgba(210, 153, 34, 0.15); color: #d29922; }
.dark .action-btn.delete:hover { background: rgba(248, 81, 73, 0.15); color: #f85149; }

/* ===== 编辑对话框 ===== */
.edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
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

.dark .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .form-section-title { color: #8b949e; }
</style>

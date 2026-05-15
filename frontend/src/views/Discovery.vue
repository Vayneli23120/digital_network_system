<template>
  <div class="discovery-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('discoveryTitle') }}</span>
          <div class="actions">
            <el-button type="primary" @click="showDiscoverDialog = true" :loading="scanning">
              <el-icon><Search /></el-icon> {{ t('discoveryStartScan') }}
            </el-button>
            <el-button @click="loadCapabilities">
              <el-icon><Refresh /></el-icon> {{ t('discoveryRefreshCapability') }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 扫描结果 -->
      <el-alert v-if="scanResult" :title="t('discoveryScanComplete', { count: scanResult.total })" type="success" :closable="false" class="scan-alert" />

      <el-table :data="discoveredDevices" v-loading="loading" style="width: 100%">
        <el-table-column prop="ip" :label="t('deviceIp')" width="150" />
        <el-table-column prop="hostname" :label="t('discoveryColHostname')" width="180" />
        <el-table-column prop="vendor" :label="t('deviceVendor')" width="100" />
        <el-table-column prop="model" :label="t('discoveryColModel')" width="150" />
        <el-table-column prop="discovery_method" :label="t('discoveryColDiscoveryMethod')" width="120" />
        <el-table-column prop="is_cisco" :label="'Cisco'" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_cisco ? 'success' : 'info'" size="small">{{ row.is_cisco ? t('statusYes') : t('statusNo') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('colOperation')" width="120">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="importDevice(row)">{{ t('actionImport') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && discoveredDevices.length === 0" :description="t('discoveryNoResults')" />
    </el-card>

    <!-- 扫描配置对话框 -->
    <el-dialog v-model="showDiscoverDialog" :title="t('discoveryPingSweep')" width="500px">
      <el-form :model="scanForm" label-width="100px">
        <el-form-item :label="t('discoveryIpSubnet')" required>
          <el-input v-model="scanForm.subnet" placeholder="192.168.1.0/24" />
        </el-form-item>
        <el-form-item :label="t('discoveryTimeout')">
          <el-input-number v-model="scanForm.timeout" :min="0.5" :max="30" :step="0.5" />
        </el-form-item>
        <el-form-item :label="t('discoveryConcurrency')">
          <el-input-number v-model="scanForm.workers" :min="1" :max="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDiscoverDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="startPingSweep" :loading="scanning">
          {{ scanning ? t('discoveryScanning') : t('discoveryStartScan') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入设备对话框 -->
    <el-dialog v-model="showImportDialog" :title="t('discoveryImportDevice')" width="500px">
      <el-form :model="importForm" label-width="100px">
        <el-form-item :label="t('deviceName')">
          <el-input v-model="importForm.name" />
        </el-form-item>
        <el-form-item :label="t('deviceIp')">
          <el-input v-model="importForm.ip" disabled />
        </el-form-item>
        <el-form-item :label="t('discoveryColModel')">
          <el-input v-model="importForm.model" />
        </el-form-item>
        <el-form-item :label="t('deviceRole')">
          <el-select v-model="importForm.role" style="width: 100%">
            <el-option :label="t('deviceRoleAccess')" value="access" />
            <el-option :label="t('deviceRoleDistribution')" value="distribution" />
            <el-option :label="t('deviceRoleCore')" value="core" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showImportDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="confirmImport">{{ t('discoveryConfirmImport') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { pingSweep, getDiscoveryCapabilities, createDevice } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

const loading = ref(false)
const scanning = ref(false)
const showDiscoverDialog = ref(false)
const showImportDialog = ref(false)
const scanResult = ref(null)
const discoveredDevices = ref([])
const selectedDevice = ref(null)

const scanForm = reactive({
  subnet: '192.168.1.0/24',
  timeout: 2,
  workers: 50
})

const importForm = reactive({
  name: '',
  ip: '',
  model: '',
  role: 'access'
})

const startPingSweep = async () => {
  scanning.value = true
  try {
    const res = await pingSweep(scanForm)
    scanResult.value = res
    discoveredDevices.value = res.devices || []
    ElMessage.success(t('discoveryMsgScanComplete', { count: res.total }))
    showDiscoverDialog.value = false
  } catch (error) {
    ElMessage.error(t('discoveryMsgScanFailed', { error: error.response?.data?.detail || error.message }))
  } finally {
    scanning.value = false
  }
}

const loadCapabilities = debounce(async (force = false) => {
  try {
    await cachedRequest(
      () => getDiscoveryCapabilities(),
      'discovery_capabilities',
      {},
      { forceRefresh: force }
    )
    ElMessage.info(t('discoveryMsgCapabilityUpdated'))
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('discoveryMsgCapabilityFailed'))
    }
  }
}, 300)

const importDevice = (device) => {
  selectedDevice.value = device
  importForm.ip = device.ip
  importForm.name = device.hostname || `Device-${device.ip.split('.').pop()}`
  importForm.model = device.model || ''
  importForm.role = 'access'
  showImportDialog.value = true
}

const confirmImport = async () => {
  try {
    await createDevice({
      name: importForm.name,
      ip: importForm.ip,
      model: importForm.model,
      role: importForm.role,
      status: 'online',
      vendor: selectedDevice.value?.vendor || 'Cisco'
    })
    ElMessage.success(t('discoveryMsgImportSuccess'))
    showImportDialog.value = false
  } catch (error) {
    ElMessage.error(t('discoveryMsgImportFailed', { error: error.response?.data?.detail || error.message }))
  }
}
</script>

<style scoped>
.discovery-page { padding: 0; }
.scan-alert { margin-bottom: var(--gap-md); }
</style>

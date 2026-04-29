<template>
  <div class="discovery-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>设备发现</span>
          <div class="actions">
            <el-button type="primary" @click="showDiscoverDialog = true" :loading="scanning">
              <el-icon><Search /></el-icon> 开始扫描
            </el-button>
            <el-button @click="loadCapabilities">
              <el-icon><Refresh /></el-icon> 刷新能力
            </el-button>
          </div>
        </div>
      </template>

      <!-- 扫描结果 -->
      <el-alert v-if="scanResult" :title="`扫描完成：发现 ${scanResult.total} 台设备`" type="success" :closable="false" class="scan-alert" />

      <el-table :data="discoveredDevices" v-loading="loading" style="width: 100%">
        <el-table-column prop="ip" label="IP 地址" width="150" />
        <el-table-column prop="hostname" label="主机名" width="180" />
        <el-table-column prop="vendor" label="厂商" width="100" />
        <el-table-column prop="model" label="型号" width="150" />
        <el-table-column prop="discovery_method" label="发现方式" width="120" />
        <el-table-column prop="is_cisco" label="Cisco" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_cisco ? 'success' : 'info'" size="small">{{ row.is_cisco ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="importDevice(row)">导入</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && discoveredDevices.length === 0" description="暂无发现结果，点击上方「开始扫描」" />
    </el-card>

    <!-- 扫描配置对话框 -->
    <el-dialog v-model="showDiscoverDialog" title="Ping Sweep 扫描" width="500px">
      <el-form :model="scanForm" label-width="100px">
        <el-form-item label="IP 网段" required>
          <el-input v-model="scanForm.subnet" placeholder="192.168.1.0/24" />
        </el-form-item>
        <el-form-item label="超时(秒)">
          <el-input-number v-model="scanForm.timeout" :min="0.5" :max="30" :step="0.5" />
        </el-form-item>
        <el-form-item label="并发数">
          <el-input-number v-model="scanForm.workers" :min="1" :max="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDiscoverDialog = false">取消</el-button>
        <el-button type="primary" @click="startPingSweep" :loading="scanning">
          {{ scanning ? '扫描中...' : '开始扫描' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入设备对话框 -->
    <el-dialog v-model="showImportDialog" title="导入设备" width="500px">
      <el-form :model="importForm" label-width="100px">
        <el-form-item label="设备名称">
          <el-input v-model="importForm.name" />
        </el-form-item>
        <el-form-item label="IP 地址">
          <el-input v-model="importForm.ip" disabled />
        </el-form-item>
        <el-form-item label="型号">
          <el-input v-model="importForm.model" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="importForm.role" style="width: 100%">
            <el-option label="接入" value="access" />
            <el-option label="汇聚" value="distribution" />
            <el-option label="核心" value="core" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { pingSweep, getDiscoveryCapabilities, createDevice } from '@/api'

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
    ElMessage.success(`扫描完成，发现 ${res.total} 台设备`)
    showDiscoverDialog.value = false
  } catch (error) {
    ElMessage.error('扫描失败：' + (error.response?.data?.detail || error.message))
  } finally {
    scanning.value = false
  }
}

const loadCapabilities = async () => {
  try {
    await getDiscoveryCapabilities()
    ElMessage.info('发现能力已更新')
  } catch (error) {
    ElMessage.error('获取能力失败')
  }
}

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
    ElMessage.success('设备导入成功')
    showImportDialog.value = false
  } catch (error) {
    ElMessage.error('导入失败：' + (error.response?.data?.detail || error.message))
  }
}
</script>

<style scoped>
.discovery-page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.scan-alert { margin-bottom: 16px; }
</style>

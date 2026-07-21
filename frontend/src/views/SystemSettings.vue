<template>
  <div class="system-settings-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('systemSettings') || '系统设置' }}</span>
          <el-button type="primary" @click="saveSettings" :loading="saving">{{ t('alertSaveSettings') || '保存' }}</el-button>
        </div>
      </template>

      <el-form :model="form" label-width="140px" v-loading="loading">
        <!-- 时区设置 -->
        <div class="form-section">
          <div class="section-header">{{ t('systemTimeSettings') || '时间设置' }}</div>

          <el-form-item :label="t('systemTimezone') || '系统时区'">
            <el-select v-model="form.timezone" placeholder="选择时区" style="width: 300px">
              <el-option
                v-for="tz in timezoneOptions"
                :key="tz.value"
                :label="tz.label"
                :value="tz.value"
              />
            </el-select>
            <span class="form-tip">{{ t('systemTimezoneTip') || '系统全局时区，影响所有时间显示' }}</span>
          </el-form-item>
        </div>

        <!-- Grafana 集成 -->
        <div class="form-section">
          <div class="section-header">Grafana 指标图表</div>
          <el-form-item label="Grafana 地址">
            <el-input v-model="form.grafana_url" placeholder="如 http://192.168.4.37:3001" style="width: 360px" />
            <span class="form-tip">用于设备详情页嵌入指标图表；为空则不显示。指向你部署的 Grafana（docker 默认宿主机 3001）。</span>
          </el-form-item>
        </div>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>{{ t('systemHelpTitle') || '系统架构中心' }}</span>
          <el-button type="primary" plain @click="goSystemHelp">{{ t('menuSystemHelp') || '系统帮助' }}</el-button>
        </div>
      </template>
      <div class="slo-hint">
        {{ t('systemHelpQuickEntryDesc') || '用于查看系统全景架构、模块关系与数据流，适合运维交接、问题定位与汇报展示。' }}
      </div>
    </el-card>

    <!-- SLO 服务配置 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>SLO 服务配置</span>
          <el-button type="primary" size="small" @click="openSloDialog()">新增 SLO</el-button>
        </div>
      </template>
      <div class="slo-hint">定义服务可用性目标（如核心机房 99.9%）。同一故障域的设备应归入同一个 SLO；停机按故障时长自动计入预算。</div>
      <el-table :data="sloList" v-loading="sloLoading" size="small" style="margin-top: 8px">
        <el-table-column label="服务名称" prop="service_name" min-width="130" />
        <el-table-column label="标识 key" prop="service_key" width="140" />
        <el-table-column label="目标" width="80">
          <template #default="{ row }">{{ row.slo_target }}%</template>
        </el-table-column>
        <el-table-column label="设备类型" min-width="220">
          <template #default="{ row }">{{ row.device_types || '全局' }}</template>
        </el-table-column>
        <el-table-column label="窗口" width="70">
          <template #default="{ row }">{{ row.window_days }}d</template>
        </el-table-column>
        <el-table-column label="启用" width="64" align="center">
          <template #default="{ row }"><el-switch :model-value="row.is_active" @change="v => toggleSlo(row, v)" size="small" /></template>
        </el-table-column>
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openSloDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteSloRow(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!sloList.length && !sloLoading" description="尚未配置 SLO，点「新增 SLO」添加" :image-size="56" />
    </el-card>

    <!-- SLO 编辑对话框 -->
    <el-dialog v-model="sloDialog" :title="sloForm.id ? '编辑 SLO' : '新增 SLO'" width="560px">
      <el-form :model="sloForm" label-width="100px">
        <el-form-item label="服务名称" required>
          <el-input v-model="sloForm.service_name" placeholder="如 核心机房网络" />
        </el-form-item>
        <el-form-item label="标识 key" required>
          <el-input v-model="sloForm.service_key" placeholder="如 core_room（英文、唯一）" :disabled="!!sloForm.id" />
        </el-form-item>
        <el-form-item label="目标可用率">
          <el-input-number v-model="sloForm.slo_target" :min="90" :max="100" :step="0.1" :precision="2" />
          <span class="form-tip">%</span>
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="sloDeviceTypes" multiple placeholder="选择设备类型（空=全局）" style="width: 100%">
            <el-option v-for="dt in deviceTypeOptions" :key="dt.value" :label="dt.label" :value="dt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="统计窗口">
          <el-input-number v-model="sloForm.window_days" :min="1" :max="365" />
          <span class="form-tip">天</span>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="sloForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sloDialog = false">取消</el-button>
        <el-button type="primary" @click="saveSlo" :loading="sloSaving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)

const form = reactive({
  timezone: 'Asia/Shanghai',
  grafana_url: '',
})

const timezoneOptions = [
  { value: 'UTC', label: 'UTC (UTC+0)' },
  { value: 'Asia/Shanghai', label: '中国标准时间 (UTC+8)' },
  { value: 'Asia/Taipei', label: '台北时间 (UTC+8)' },
  { value: 'Asia/Hong_Kong', label: '香港时间 (UTC+8)' },
  { value: 'Asia/Tokyo', label: '日本标准时间 (UTC+9)' },
  { value: 'Asia/Seoul', label: '韩国标准时间 (UTC+9)' },
  { value: 'Asia/Singapore', label: '新加坡时间 (UTC+8)' },
  { value: 'America/New_York', label: '美国东部时间 (UTC-5)' },
  { value: 'America/Chicago', label: '美国中部时间 (UTC-6)' },
  { value: 'America/Denver', label: '美国山地时间 (UTC-7)' },
  { value: 'America/Los_Angeles', label: '美国太平洋时间 (UTC-8)' },
  { value: 'Europe/London', label: '格林威治标准时间 (UTC+0)' },
  { value: 'Europe/Berlin', label: '欧洲中部时间 (UTC+1)' },
  { value: 'Europe/Paris', label: '法国时间 (UTC+1)' },
  { value: 'Australia/Sydney', label: '澳大利亚东部时间 (UTC+10)' },
  { value: 'Pacific/Auckland', label: '新西兰时间 (UTC+12)' },
]

async function loadSettings() {
  loading.value = true
  try {
    const res = await axios.get('/api/system/config')
    const items = res.data.items || []
    for (const item of items) {
      if (item.key in form) {
        form[item.key] = item.value
      }
    }
  } catch (e) {
    ElMessage.error('加载系统设置失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await axios.put('/api/system/config', { key: 'timezone', value: form.timezone })
    await axios.put('/api/system/config', { key: 'grafana_url', value: form.grafana_url || '' })
    ElMessage.success('设置已保存')
  } catch (e) {
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

function goSystemHelp() {
  router.push('/system-help')
}

onMounted(loadSettings)

// ===== SLO 服务配置 =====
const deviceTypeOptions = [
  { value: 'core_switch', label: '核心交换机' },
  { value: 'router', label: '路由器' },
  { value: 'firewall', label: '防火墙' },
  { value: 'server_switch', label: '服务器交换机' },
  { value: 'office_switch', label: '办公交换机' },
  { value: 'switch', label: '接入交换机' },
  { value: 'uce', label: 'UCE' },
  { value: 'wlc', label: '无线控制器' },
  { value: 'ap', label: 'AP' },
  { value: 'pa', label: 'PA 防火墙' },
  { value: 'ftd', label: 'FTD' },
  { value: 'other', label: '其他' },
]

const sloList = ref([])
const sloLoading = ref(false)
const sloDialog = ref(false)
const sloSaving = ref(false)
const sloDeviceTypes = ref([])
const sloForm = reactive({
  id: null,
  service_key: '',
  service_name: '',
  slo_target: 99.9,
  window_days: 30,
  is_active: true,
})

async function loadSlo() {
  sloLoading.value = true
  try {
    const res = await axios.get('/api/dashboard/slo')
    sloList.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载 SLO 配置失败')
  } finally {
    sloLoading.value = false
  }
}

function openSloDialog(row = null) {
  if (row) {
    sloForm.id = row.id
    sloForm.service_key = row.service_key
    sloForm.service_name = row.service_name
    sloForm.slo_target = row.slo_target
    sloForm.window_days = row.window_days
    sloForm.is_active = row.is_active
    sloDeviceTypes.value = (row.device_types || '').split(',').map(s => s.trim()).filter(Boolean)
  } else {
    sloForm.id = null
    sloForm.service_key = ''
    sloForm.service_name = ''
    sloForm.slo_target = 99.9
    sloForm.window_days = 30
    sloForm.is_active = true
    sloDeviceTypes.value = []
  }
  sloDialog.value = true
}

async function saveSlo() {
  if (!sloForm.service_name.trim() || !sloForm.service_key.trim()) {
    ElMessage.warning('服务名称和标识 key 不能为空')
    return
  }
  sloSaving.value = true
  const payload = {
    service_key: sloForm.service_key.trim(),
    service_name: sloForm.service_name.trim(),
    slo_target: sloForm.slo_target,
    device_types: sloDeviceTypes.value.join(','),
    window_days: sloForm.window_days,
    is_active: sloForm.is_active,
  }
  try {
    if (sloForm.id) {
      await axios.put(`/api/dashboard/slo/${sloForm.id}`, payload)
    } else {
      await axios.post('/api/dashboard/slo', payload)
    }
    ElMessage.success('已保存')
    sloDialog.value = false
    loadSlo()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    sloSaving.value = false
  }
}

async function toggleSlo(row, val) {
  try {
    await axios.put(`/api/dashboard/slo/${row.id}`, {
      service_key: row.service_key,
      service_name: row.service_name,
      slo_target: row.slo_target,
      device_types: row.device_types || '',
      window_days: row.window_days,
      is_active: val,
    })
    row.is_active = val
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

async function deleteSloRow(row) {
  try {
    await ElMessageBox.confirm(`确定删除 SLO「${row.service_name}」？`, '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await axios.delete(`/api/dashboard/slo/${row.id}`)
    ElMessage.success('已删除')
    loadSlo()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(loadSlo)
</script>

<style scoped>
.system-settings-page {
  padding: 20px;
  max-width: 1080px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-tip {
  margin-left: 10px;
  font-size: 12px;
  color: #999;
}

.slo-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.form-section {
  margin-bottom: 24px;
}

.section-header {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}
</style>

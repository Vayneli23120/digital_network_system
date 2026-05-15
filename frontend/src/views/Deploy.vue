<template>
  <div class="deploy-page" :class="{ dark: isDark }">
    <!-- 页面标题栏 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('deployTitle') }}</h1>
        <el-tag v-if="executionStatus === 'running'" type="warning" effect="dark" class="status-tag">
          <el-icon class="is-loading"><Loading /></el-icon>
          {{ t('deployExecuting') }}
        </el-tag>
        <el-tag v-else-if="executionStatus === 'completed'" type="success" class="status-tag">
          <el-icon><CircleCheckFilled /></el-icon>
          {{ t('deployCompleted') }}
        </el-tag>
        <el-tag v-else-if="executionStatus === 'failed'" type="danger" class="status-tag">
          <el-icon><CircleCloseFilled /></el-icon>
          {{ t('deployFailed') }}
        </el-tag>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn secondary" @click="showVariableHelp = true">
          <el-icon><QuestionFilled /></el-icon>
          {{ t('deployVariableHelp') }}
        </button>
        <button
          v-if="executionStatus === 'running'"
          class="nav-action-btn danger"
          @click="confirmAbort"
          :loading="aborting"
        >
          <el-icon><CircleClose /></el-icon>
          {{ t('deployAbort') }}
        </button>
      </div>
    </section>

    <!-- 生产环境警告 -->
    <section
      v-if="isProductionEnv && deployForm.target_devices.length > 1"
      class="warning-section"
    >
      <div class="warning-card">
        <el-icon class="warning-icon"><WarningFilled /></el-icon>
        <div class="warning-content">
          <div class="warning-title">{{ t('deployProductionWarningTitle') }}</div>
          <div class="warning-desc">
            {{ t('deployProductionWarning', { count: deployForm.target_devices.length }) }}
          </div>
        </div>
        <el-tag type="warning" effect="dark" size="large">
          {{ t('deploySerialExecution') }}
        </el-tag>
      </div>
    </section>

    <!-- 主内容区 -->
    <section class="main-content-area">
      <el-row :gutter="20" class="full-height">
        <!-- 左侧：配置面板 -->
        <el-col :span="8" class="config-column">
          <div class="config-panel" v-loading="loading">
            <div class="panel-header">
              <span class="panel-title">{{ t('deployConfigPanel') }}</span>
            </div>

            <el-form :model="deployForm" label-position="top" class="config-form">
              <!-- 部署模式 -->
              <div class="form-section">
                <div class="section-label">{{ t('deployMode') }}</div>
                <el-radio-group v-model="deployForm.mode" class="mode-radio-group">
                  <el-radio-button label="backup">
                    <el-icon><Document /></el-icon>
                    {{ t('deployFromBackup') }}
                  </el-radio-button>
                  <el-radio-button label="template">
                    <el-icon><Files /></el-icon>
                    {{ t('deployUseTemplate') }}
                  </el-radio-button>
                </el-radio-group>
              </div>

              <!-- 备份文件选择 -->
              <div v-if="deployForm.mode === 'backup'" class="form-section">
                <div class="section-label required">{{ t('deployBackupFile') }}</div>
                <el-select
                  v-model="deployForm.backup_file"
                  :placeholder="t('deploySelectBackupFile')"
                  style="width: 100%"
                  filterable
                >
                  <el-option
                    v-for="backup in backups"
                    :key="backup.id"
                    :label="`${backup.device_name} - ${backup.backup_file}`"
                    :value="backup.backup_file"
                  >
                    <div class="backup-option">
                      <span class="backup-name">{{ backup.device_name }}</span>
                      <span class="backup-file">{{ backup.backup_file }}</span>
                      <span class="backup-time">{{ formatDateTime(backup.backup_time) }}</span>
                    </div>
                  </el-option>
                </el-select>
              </div>

              <!-- 模板选择 -->
              <div v-if="deployForm.mode === 'template'" class="form-section">
                <div class="section-label required">{{ t('deployConfigTemplate') }}</div>
                <el-select
                  v-model="deployForm.template_id"
                  :placeholder="t('deploySelectTemplate')"
                  style="width: 100%"
                  @change="loadTemplateVariables"
                >
                  <el-option
                    v-for="template in templates"
                    :key="template.id"
                    :label="template.name"
                    :value="template.id"
                  >
                    <div class="template-option">
                      <span class="template-name">{{ template.name }}</span>
                      <span v-if="template.description" class="template-desc">
                        {{ template.description }}
                      </span>
                    </div>
                  </el-option>
                </el-select>
              </div>

              <!-- 目标设备 -->
              <div class="form-section">
                <div class="section-label required">{{ t('deployTargetDevice') }}</div>
                <el-select
                  v-model="deployForm.target_devices"
                  multiple
                  :placeholder="t('deploySelectDeviceMultiple')"
                  style="width: 100%"
                  filterable
                  @change="handleDeviceChange"
                >
                  <el-option
                    v-for="device in devices"
                    :key="device.id"
                    :label="`${device.name} (${device.ip})`"
                    :value="device.id"
                    :disabled="device.status === 'offline'"
                  >
                    <div class="device-option">
                      <span class="device-name">{{ device.name }}</span>
                      <span class="device-ip">{{ device.ip }}</span>
                      <el-tag
                        v-if="device.status !== 'online'"
                        size="small"
                        type="danger"
                      >
                        {{ device.status }}
                      </el-tag>
                    </div>
                  </el-option>
                </el-select>
                <div class="section-desc">{{ t('deployDeviceTip') }}</div>

                <!-- 执行模式提示 -->
                <div v-if="deployForm.target_devices.length > 1" class="execution-mode-hint">
                  <el-tag
                    v-if="isProductionEnv"
                    type="warning"
                    effect="dark"
                    size="large"
                  >
                    <el-icon><WarningFilled /></el-icon>
                    {{ t('deploySerialMode') }}
                  </el-tag>
                  <el-tag v-else type="success" effect="dark" size="large">
                    <el-icon><CircleCheckFilled /></el-icon>
                    {{ t('deployParallelMode', { limit: parallelLimit }) }}
                  </el-tag>
                </div>
              </div>

              <!-- 变量替换 -->
              <div v-if="deployForm.mode === 'template' && availableVariables.length > 0" class="form-section">
                <div class="section-label">{{ t('deployVariableReplace') }}</div>
                <div class="variables-list">
                  <div
                    v-for="(variable, index) in deployForm.variables"
                    :key="index"
                    class="variable-item"
                  >
                    <el-select
                      v-model="variable.key"
                      :placeholder="t('deploySelectVariable')"
                      style="width: 140px"
                      size="small"
                    >
                      <el-option
                        v-for="v in availableVariables"
                        :key="v.key"
                        :label="v.key"
                        :value="v.key"
                      />
                    </el-select>
                    <el-input
                      v-model="variable.value"
                      :placeholder="getVariablePlaceholder(variable.key)"
                      style="flex: 1"
                      size="small"
                    />
                    <el-button
                      size="small"
                      type="danger"
                      link
                      @click="removeVariable(index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button size="small" @click="addVariable" class="add-var-btn">
                    <el-icon><Plus /></el-icon>
                    {{ t('deployAddVariable') }}
                  </el-button>
                </div>
              </div>

              <!-- 干运行选项 -->
              <div class="form-section">
                <el-checkbox v-model="deployForm.dry_run">
                  {{ t('deployDryRun') }}
                </el-checkbox>
                <div class="section-desc">{{ t('deployPreviewTip') }}</div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section actions-section">
                <button
                  class="nav-action-btn secondary preview-btn"
                  @click="previewDeploy"
                  :disabled="!canDeploy || !deployForm.dry_run"
                  :class="{ disabled: !canDeploy || !deployForm.dry_run }"
                >
                  <el-icon><View /></el-icon>
                  {{ t('deployPreviewChange') }}
                </button>
                <button
                  class="nav-action-btn deploy-btn"
                  @click="confirmDeploy"
                  :disabled="!canDeploy"
                  :class="{ disabled: !canDeploy }"
                >
                  <el-icon><Upload /></el-icon>
                  {{ t('deployStart') }}
                </button>
              </div>
            </el-form>
          </div>
        </el-col>

        <!-- 右侧：执行面板 -->
        <el-col :span="16" class="execution-column">
          <div class="execution-panel" :class="{ active: executionStatus !== 'idle' }">
            <!-- 执行进度概览 -->
            <div class="execution-overview">
              <div class="overview-header">
                <div class="overview-title">
                  <el-icon v-if="executionStatus === 'running'" class="is-loading"><Loading /></el-icon>
                  <span>{{ t('deployExecutionTitle') }}</span>
                </div>
                <div v-if="elapsedTime > 0" class="elapsed-time">
                  {{ t('deployElapsedTime') }}: {{ formatDuration(elapsedTime) }}
                </div>
              </div>

              <div class="progress-overview">
                <div class="progress-item">
                  <div class="progress-label">{{ t('deployTotalDevices') }}</div>
                  <div class="progress-value">{{ totalDevices }}</div>
                </div>
                <div class="progress-item success">
                  <div class="progress-label">{{ t('deployCompleted') }}</div>
                  <div class="progress-value">{{ completedDevices }}</div>
                </div>
                <div class="progress-item warning">
                  <div class="progress-label">{{ t('deployInProgress') }}</div>
                  <div class="progress-value">{{ inProgressDevices }}</div>
                </div>
                <div class="progress-item error">
                  <div class="progress-label">{{ t('deployFailed') }}</div>
                  <div class="progress-value">{{ failedDevices }}</div>
                </div>
              </div>

              <el-progress
                :percentage="progressPercentage"
                :status="progressStatus"
                :stroke-width="12"
                class="overall-progress"
              />
            </div>

            <el-divider />

            <!-- 设备执行状态 -->
            <div class="devices-section">
              <div class="section-header">
                <span class="section-title">{{ t('deployDeviceExecution') }}</span>
              </div>
              <div class="device-cards">
                <div
                  v-for="device in deviceExecutions"
                  :key="device.device_id"
                  class="device-card"
                  :class="{
                    active: selectedDevice?.device_id === device.device_id,
                    success: device.status === 'completed',
                    error: device.status === 'failed',
                    running: device.status === 'running'
                  }"
                  @click="selectDevice(device)"
                >
                  <div class="device-card-header">
                    <div class="device-info">
                      <el-icon
                        v-if="device.status === 'completed'"
                        class="status-icon success"
                      >
                        <CircleCheckFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'failed'"
                        class="status-icon error"
                      >
                        <CircleCloseFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'running'"
                        class="status-icon running is-loading"
                      >
                        <Loading />
                      </el-icon>
                      <el-icon v-else class="status-icon pending">
                        <Timer />
                      </el-icon>
                      <div class="device-text">
                        <div class="device-name">{{ device.device_name }}</div>
                        <div class="device-ip">{{ device.device_ip }}</div>
                      </div>
                    </div>
                    <el-tag
                      :type="getDeviceStatusType(device.status)"
                      size="small"
                      effect="dark"
                    >
                      {{ getDeviceStatusText(device.status) }}
                    </el-tag>
                  </div>
                  <el-progress
                    :percentage="device.progress"
                    :status="getDeviceProgressStatus(device.status)"
                    :stroke-width="4"
                    class="device-progress"
                  />
                  <div v-if="device.message" class="device-message">
                    {{ device.message }}
                  </div>
                </div>
              </div>
            </div>

            <!-- CLI 回显区域 -->
            <div v-if="selectedDevice" class="cli-section">
              <div class="cli-header">
                <span class="cli-title">
                  {{ t('deployCliOutput') }} - {{ selectedDevice.device_name }}
                </span>
                <button class="nav-action-btn secondary small" @click="clearCliOutput">
                  <el-icon><Delete /></el-icon>
                  {{ t('actionClear') }}
                </button>
              </div>
              <div ref="cliOutputRef" class="cli-output">
                <div
                  v-for="(line, index) in selectedDevice.cliLogs"
                  :key="index"
                  class="cli-line"
                  :class="line.type"
                >
                  <span class="cli-timestamp">{{ line.timestamp }}</span>
                  <span class="cli-content">{{ line.content }}</span>
                </div>
                <div v-if="selectedDevice.cliLogs.length === 0" class="cli-empty">
                  {{ t('deployCliEmpty') }}
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </section>

    <!-- 变量说明对话框 -->
    <el-dialog
      v-model="showVariableHelp"
      :title="t('deployVariableDialog')"
      width="800px"
      align-center
      draggable
    >
      <el-table :data="allVariables" style="width: 100%" stripe>
        <el-table-column prop="key" :label="t('deployVariableName')" width="200" />
        <el-table-column prop="description" :label="t('deployDescription')" />
        <el-table-column prop="example" :label="t('deployExampleValue')" width="200" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  QuestionFilled,
  Delete,
  Plus,
  View,
  Upload,
  CircleClose,
  WarningFilled,
  CircleCheckFilled,
  CircleCloseFilled,
  Loading,
  Timer,
  Document,
  Files
} from '@element-plus/icons-vue'
import {
  getDevices,
  getBackups,
  getTemplates,
  getTemplate,
  previewDeploy as previewDeployApi,
  executeDeploy as executeDeployApi,
  getCompatibleVariables
} from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

// 暗黑模式检测
const isDark = computed(() => document.documentElement.classList.contains('dark'))

// 环境控制
const isProductionEnv = ref(false)
const parallelLimit = ref(1)

// 数据
const devices = ref([])
const backups = ref([])
const templates = ref([])
const allVariables = ref([])
const availableVariables = ref([])
const loading = ref(false)

// 表单
const deployForm = ref({
  mode: 'backup',
  backup_file: '',
  template_id: '',
  target_devices: [],
  variables: [],
  dry_run: false
})

// 执行状态
const executionStatus = ref('idle') // idle, running, completed, failed, aborted
const taskId = ref(null)
const startTime = ref(null)
const elapsedTime = ref(0)
const deviceExecutions = ref([])
const selectedDevice = ref(null)
const aborting = ref(false)
const showVariableHelp = ref(false)
const cliOutputRef = ref(null)

// 审批相关状态
const approvalStatus = ref('none') // none, pending, approved, rejected
const approvalId = ref(null)
const approvalLevel = ref(null)
const approvalInfo = ref(null)
const showApprovalDialog = ref(false)
const approvalComment = ref('')
const rejectionReason = ref('')

// 计算属性
const canDeploy = computed(() => {
  if (deployForm.value.target_devices.length === 0) return false
  if (deployForm.value.mode === 'backup') {
    return !!deployForm.value.backup_file
  }
  return !!deployForm.value.template_id
})

const totalDevices = computed(() => deviceExecutions.value.length)
const completedDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'completed').length
)
const inProgressDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'running').length
)
const failedDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'failed').length
)

const progressPercentage = computed(() => {
  if (totalDevices.value === 0) return 0
  const totalProgress = deviceExecutions.value.reduce((sum, d) => sum + d.progress, 0)
  return Math.round(totalProgress / totalDevices.value)
})

const progressStatus = computed(() => {
  if (executionStatus.value === 'failed') return 'exception'
  if (executionStatus.value === 'completed') return 'success'
  return ''
})

// 加载数据
const loadDevices = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getDevices(),
      'devices',
      {},
      { forceRefresh: force }
    )
    devices.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadDeviceFailed'))
    }
  }
}, 300)

const loadBackups = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getBackups({ limit: 50 }),
      'backups',
      { limit: 50 },
      { forceRefresh: force }
    )
    backups.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadBackupFailed'))
    }
  }
}, 300)

const loadTemplates = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getTemplates(),
      'templates',
      {},
      { forceRefresh: force }
    )
    templates.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadTemplateFailed'))
    }
  }
}, 300)

const loadCompatibleVariables = async () => {
  try {
    const data = await getCompatibleVariables()
    allVariables.value = data.variables || []
  } catch (error) {
    // Silent fail
  }
}

const loadTemplateVariables = async (templateId) => {
  if (!templateId) {
    availableVariables.value = []
    return
  }

  try {
    const data = await getTemplate(templateId)
    if (data.variables) {
      try {
        const vars = typeof data.variables === 'string'
          ? JSON.parse(data.variables)
          : data.variables
        availableVariables.value = vars
        deployForm.value.variables = vars.map(v => ({
          key: v.key,
          value: v.default || ''
        }))
      } catch (e) {
        console.error('Parse template variables failed:', e)
      }
    }
  } catch (error) {
    ElMessage.error(t('deployLoadTemplateVarFailed'))
  }
}

// 环境检测
const detectEnvironment = () => {
  const productionPatterns = [
    /prod/i, /production/i, /live/i, /core/i,
    /border/i, /wan/i, /internet/i
  ]

  const hasProductionDevice = deployForm.value.target_devices.some(deviceId => {
    const device = devices.value.find(d => d.id === deviceId)
    if (!device) return false
    return productionPatterns.some(pattern =>
      pattern.test(device.name) || pattern.test(device.ip)
    )
  })

  isProductionEnv.value = hasProductionDevice
  parallelLimit.value = isProductionEnv.value ? 1 : 3
}

const handleDeviceChange = () => {
  detectEnvironment()
  // 重置设备执行列表
  deviceExecutions.value = deployForm.value.target_devices.map(id => {
    const device = devices.value.find(d => d.id === id)
    return {
      device_id: id,
      device_name: device?.name || '',
      device_ip: device?.ip || '',
      status: 'pending',
      progress: 0,
      message: '',
      cliLogs: []
    }
  })
}

// 变量操作
const getVariablePlaceholder = (key) => {
  const v = allVariables.value.find(v => v.key === key)
  return v ? t('deployExample') + v.example : ''
}

const addVariable = () => {
  deployForm.value.variables.push({ key: '', value: '' })
}

const removeVariable = (index) => {
  deployForm.value.variables.splice(index, 1)
}

// 设备状态
const getDeviceStatusType = (status) => {
  const types = { pending: 'info', running: 'primary', completed: 'success', failed: 'danger' }
  return types[status] || 'info'
}

const getDeviceStatusText = (status) => {
  const texts = {
    pending: t('deployDevicePending'),
    running: t('deployDeviceRunning'),
    completed: t('deployDeviceCompleted'),
    failed: t('deployDeviceFailed')
  }
  return texts[status] || status
}

const getDeviceProgressStatus = (status) => {
  if (status === 'failed') return 'exception'
  if (status === 'completed') return 'success'
  return ''
}

const selectDevice = (device) => {
  selectedDevice.value = device
}

const clearCliOutput = () => {
  if (selectedDevice.value) {
    selectedDevice.value.cliLogs = []
  }
}

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 预览部署
const previewDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  const deployData = {
    mode: deployForm.value.mode,
    backup_file: deployForm.value.backup_file,
    template_id: deployForm.value.template_id,
    target_devices: deployForm.value.target_devices,
    variables: {}
  }

  deployForm.value.variables.forEach(v => {
    if (v.key) deployData.variables[v.key] = v.value
  })

  try {
    const result = await previewDeployApi(deployData)
    ElMessage.success(t('deployPreviewSuccess'))
    // 预览结果显示在配置面板
  } catch (error) {
    ElMessage.error(t('deployPreviewFailed'))
  }
}

// 执行部署
const confirmDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  detectEnvironment()

  // 生产环境多设备警告
  if (isProductionEnv.value && deployForm.value.target_devices.length > 1) {
    try {
      await ElMessageBox.confirm(
        t('deployProductionConfirm', { count: deployForm.value.target_devices.length }),
        t('deployProductionWarningTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )
    } catch {
      return
    }
  } else {
    try {
      await ElMessageBox.confirm(
        t('deployConfirmMessage'),
        t('deployConfirmTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )
    } catch {
      return
    }
  }

  await executeDeploy()
}

// SSE 执行
let eventSource = null
let timer = null

const executeDeploy = async () => {
  try {
    const deployData = {
      mode: deployForm.value.mode,
      backup_file: deployForm.value.backup_file,
      template_id: deployForm.value.template_id,
      target_devices: deployForm.value.target_devices,
      variables: {},
      dry_run: false,
      is_production: isProductionEnv.value,
      parallel_limit: parallelLimit.value
    }

    deployForm.value.variables.forEach(v => {
      if (v.key) deployData.variables[v.key] = v.value
    })

    // 创建执行任务
    const result = await executeDeployApi(deployData)

    // 检查是否需要审批
    if (result.requires_approval) {
      approvalStatus.value = 'pending'
      approvalId.value = result.approval_id
      approvalLevel.value = result.approval_level
      approvalInfo.value = {
        requester: currentUser?.username || 'Unknown',
        requestedAt: new Date().toISOString(),
        level: result.approval_level
      }
      ElMessage.info(t('deployPendingApproval'))
      return
    }

    // 无需审批，开始执行
    executionStatus.value = 'running'
    startTime.value = Date.now()
    timer = setInterval(() => {
      elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
    }, 1000)

    taskId.value = result.task_id

    // 连接SSE流
    connectExecutionStream()

    ElMessage.success(t('deployStarted'))
  } catch (error) {
    ElMessage.error(t('deployFailed'))
  }
}

const connectExecutionStream = () => {
  if (!taskId.value) return

  eventSource = new EventSource(`/api/deploy/execute/${taskId.value}/stream`)

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleExecutionEvent(data)
  }

  eventSource.onerror = () => {
    if (executionStatus.value === 'running') {
      executionStatus.value = 'failed'
      ElMessage.error(t('deployStreamError'))
    }
    closeEventSource()
  }
}

const handleExecutionEvent = (data) => {
  const device = deviceExecutions.value.find(d => d.device_id === data.device_id)

  switch (data.type) {
    case 'device_start':
      if (device) {
        device.status = 'running'
        device.message = data.message
      }
      break
    case 'device_progress':
      if (device) {
        device.progress = data.progress
        device.message = data.message
      }
      break
    case 'device_cli':
      if (device) {
        device.cliLogs.push({
          timestamp: data.timestamp,
          content: data.cli_output,
          type: data.log_type || 'info'
        })
        // 自动滚动
        if (selectedDevice.value?.device_id === data.device_id) {
          nextTick(() => {
            if (cliOutputRef.value) {
              cliOutputRef.value.scrollTop = cliOutputRef.value.scrollHeight
            }
          })
        }
      }
      break
    case 'device_complete':
      if (device) {
        device.status = 'completed'
        device.progress = 100
        device.message = data.message
      }
      break
    case 'device_failed':
      if (device) {
        device.status = 'failed'
        device.message = data.message
      }
      break
    case 'execution_complete':
      executionStatus.value = data.success ? 'completed' : 'failed'
      closeEventSource()
      stopTimer()
      clearCache('devices')
      ElMessage.success(t('deployComplete'))
      break
  }
}

const closeEventSource = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const stopTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const confirmAbort = async () => {
  try {
    await ElMessageBox.confirm(
      t('deployAbortConfirm'),
      t('deployAbortTitle'),
      { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
    )
    await abortExecution()
  } catch {
    // Cancelled
  }
}

const abortExecution = async () => {
  aborting.value = true
  try {
    await fetch(`/api/deploy/execute/${taskId.value}/abort`, { method: 'POST' })
    executionStatus.value = 'aborted'
    ElMessage.warning(t('deployAborted'))
    closeEventSource()
    stopTimer()
  } catch (error) {
    ElMessage.error(t('deployAbortFailed'))
  } finally {
    aborting.value = false
  }
}

// 审批处理函数
const handleApprovalSubmit = async () => {
  if (!approvalComment.value.trim()) {
    ElMessage.warning(t('deployApprovalCommentRequired'))
    return
  }

  try {
    const response = await fetch(`/api/deploy-approval/${approvalId.value}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: approvalComment.value })
    })

    if (response.ok) {
      approvalStatus.value = 'approved'
      ElMessage.success(t('deployApproved'))
      // 刷新并开始执行
      await startApprovedDeployment()
    } else {
      ElMessage.error(t('deployApproveFailed'))
    }
  } catch (error) {
    ElMessage.error(t('deployApproveFailed'))
  }
}

const handleRejectionSubmit = async () => {
  if (!rejectionReason.value.trim()) {
    ElMessage.warning(t('deployRejectionReasonRequired'))
    return
  }

  try {
    const response = await fetch(`/api/deploy-approval/${approvalId.value}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: rejectionReason.value })
    })

    if (response.ok) {
      approvalStatus.value = 'rejected'
      ElMessage.warning(t('deployRejected'))
    } else {
      ElMessage.error(t('deployRejectFailed'))
    }
  } catch (error) {
    ElMessage.error(t('deployRejectFailed'))
  }
}

const startApprovedDeployment = async () => {
  // 审批通过后开始执行
  executionStatus.value = 'running'
  startTime.value = Date.now()
  timer = setInterval(() => {
    elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
  }, 1000)

  // 重新调用部署API
  // 注意：实际实现需要一个新的API端点或在原API中处理
  // 这里简化处理，直接显示执行状态
}

onMounted(() => {
  loadDevices()
  loadBackups()
  loadTemplates()
  loadCompatibleVariables()
})
</script>

<style scoped>
.deploy-page {
  padding: 0;
}

/* Dark mode support */
.deploy-page.dark {
  --panel-bg: var(--bg-secondary);
  --panel-border: var(--border-default);
  --text-primary: var(--text-primary);
  --text-secondary: var(--text-secondary);
}

.deploy-page:not(.dark) {
  --panel-bg: #fff;
  --panel-border: #e4e7ed;
  --text-primary: #303133;
  --text-secondary: #606266;
}

/* Page nav bar */
.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 5px;
}

.nav-right {
  display: flex;
  gap: 10px;
}

.nav-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  border: none;
}

.nav-action-btn.secondary {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.secondary:hover {
  background: #f5f7fa;
}

.nav-action-btn.danger {
  background: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
  color: white;
}

.nav-action-btn.danger:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.nav-action-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Warning section */
.warning-section {
  margin-bottom: 20px;
}

.warning-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 20px;
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  border: 1px solid #ffc107;
  border-radius: 12px;
}

.deploy-page.dark .warning-card {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.15) 0%, rgba(255, 183, 77, 0.15) 100%);
}

.warning-icon {
  font-size: 24px;
  color: #f59e0b;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-weight: 600;
  color: #92400e;
  margin-bottom: 4px;
}

.deploy-page.dark .warning-title {
  color: #fbbf24;
}

.warning-desc {
  font-size: 13px;
  color: #a16207;
}

.deploy-page.dark .warning-desc {
  color: #fcd34d;
}

/* Main content */
.main-content-area {
  height: calc(100vh - 200px);
}

.full-height {
  height: 100%;
}

.config-column,
.execution-column {
  height: 100%;
}

/* Config panel */
.config-panel {
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 12px;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.panel-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--panel-border);
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

/* Form sections */
.form-section {
  margin-bottom: 20px;
}

.section-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.section-label.required::after {
  content: ' *';
  color: #f56c6c;
}

.section-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 5px;
}

.mode-radio-group {
  display: flex;
  width: 100%;
}

.mode-radio-group :deep(.el-radio-button) {
  flex: 1;
}

.mode-radio-group :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

/* Options styling */
.backup-option,
.template-option,
.device-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.backup-name,
.template-name,
.device-name {
  font-weight: 500;
}

.backup-file,
.template-desc,
.device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

.backup-time {
  font-size: 11px;
  color: #909399;
}

/* Execution mode hint */
.execution-mode-hint {
  margin-top: 10px;
}

/* Variables */
.variables-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.variable-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.add-var-btn {
  margin-top: 5px;
}

/* Actions */
.actions-section {
  display: flex;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid var(--panel-border);
}

.preview-btn,
.deploy-btn {
  flex: 1;
  justify-content: center;
}

.deploy-btn {
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
}

.deploy-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 184, 148, 0.3);
}

/* Execution panel */
.execution-panel {
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 12px;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.execution-panel.active {
  border-color: #00b894;
  box-shadow: 0 0 20px rgba(0, 184, 148, 0.1);
}

/* Execution overview */
.execution-overview {
  margin-bottom: 20px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.overview-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.elapsed-time {
  font-size: 13px;
  color: var(--text-secondary);
}

.progress-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 15px;
}

.progress-item {
  text-align: center;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.progress-item.success {
  background: rgba(103, 194, 58, 0.1);
}

.progress-item.warning {
  background: rgba(230, 162, 60, 0.1);
}

.progress-item.error {
  background: rgba(245, 108, 108, 0.1);
}

.progress-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 5px;
}

.progress-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.progress-item.success .progress-value {
  color: #67c23a;
}

.progress-item.warning .progress-value {
  color: #e6a23c;
}

.progress-item.error .progress-value {
  color: #f56c6c;
}

.overall-progress {
  margin-top: 10px;
}

/* Devices section */
.devices-section {
  margin-bottom: 20px;
}

.section-header {
  margin-bottom: 15px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.device-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.device-card {
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.device-card:hover {
  border-color: #409eff;
}

.device-card.active {
  border-color: #00b894;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.2);
}

.device-card.success {
  border-color: #67c23a;
  background: rgba(103, 194, 58, 0.05);
}

.device-card.error {
  border-color: #f56c6c;
  background: rgba(245, 108, 108, 0.05);
}

.device-card.running {
  border-color: #409eff;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(64, 158, 255, 0); }
}

.device-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.device-info {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.status-icon {
  font-size: 16px;
  margin-top: 2px;
}

.status-icon.success {
  color: #67c23a;
}

.status-icon.error {
  color: #f56c6c;
}

.status-icon.running {
  color: #409eff;
}

.status-icon.pending {
  color: #909399;
}

.device-text {
  display: flex;
  flex-direction: column;
}

.device-name {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 13px;
}

.device-ip {
  font-size: 11px;
  color: var(--text-secondary);
}

.device-progress {
  margin-top: 8px;
}

.device-message {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-secondary);
}

/* CLI section */
.cli-section {
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  overflow: hidden;
}

.cli-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--panel-border);
}

.cli-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.cli-output {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 12px 15px;
  max-height: 250px;
  overflow-y: auto;
  min-height: 100px;
}

.cli-line {
  display: flex;
  gap: 10px;
  padding: 1px 0;
}

.cli-timestamp {
  color: #858585;
  flex-shrink: 0;
}

.cli-content {
  white-space: pre-wrap;
  word-break: break-all;
}

.cli-line.command .cli-content {
  color: #4ec9b0;
}

.cli-line.error .cli-content {
  color: #f48771;
}

.cli-line.warning .cli-content {
  color: #dcdcaa;
}

.cli-line.success .cli-content {
  color: #7ee787;
}

.cli-empty {
  color: #858585;
  text-align: center;
  padding: 40px 0;
}

/* Animations */
.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

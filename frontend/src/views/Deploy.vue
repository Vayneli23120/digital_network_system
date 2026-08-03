<template>
  <div class="deploy-page" :class="{ dark: isDark }">
    <!-- 页面标题栏 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('deployTitle') }}</h1>
        <el-tag v-if="executionStatus === 'running'" type="warning" effect="dark" class="status-tag">
          <span class="status-content">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>{{ t('deployExecuting') }}</span>
          </span>
        </el-tag>
        <el-tag v-else-if="executionStatus === 'completed'" type="success" class="status-tag">
          <span class="status-content">
            <el-icon><CircleCheckFilled /></el-icon>
            <span>{{ t('deployCompleted') }}</span>
          </span>
        </el-tag>
        <el-tag v-else-if="executionStatus === 'failed'" type="danger" class="status-tag">
          <span class="status-content">
            <el-icon><CircleCloseFilled /></el-icon>
            <span>{{ t('deployFailed') }}</span>
          </span>
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

    <!-- 主内容区 -->
    <section class="main-content-area">
      <el-row :gutter="20" class="full-height">
        <!-- 左侧：配置面板 -->
        <el-col :span="8" class="config-column">
      <DeployFormPanel
        v-model:deploy-form="deployForm"
        v-model:execution-mode="executionMode"
        v-model:parallel-limit="parallelLimit"
        :loading="loading"
        :devices="devices"
        :backups="backups"
        :templates="templates"
        :available-variables="availableVariables"
        :all-variables="allVariables"
        :can-deploy="canDeploy"
        @template-change="loadTemplateVariables"
        @device-change="handleDeviceChange"
        @preview="previewDeploy"
        @deploy="confirmDeploy"
      />
        </el-col>

        <!-- 右侧：执行面板 -->
        <el-col :span="16" class="execution-column">
          <DeployExecutionPanel
            :status="executionStatus"
            :elapsed-time="elapsedTime"
            :device-executions="deviceExecutions"
            :selected-device="selectedDevice"
            :total-devices="totalDevices"
            :completed-devices="completedDevices"
            :in-progress-devices="inProgressDevices"
            :failed-devices="failedDevices"
            :progress-percentage="progressPercentage"
            :progress-status="progressStatus"
            :has-rollback-available="hasRollbackAvailable"
            :register-cli-output="registerCliOutput"
            @select-device="selectDevice"
            @clear-cli="clearCliOutput"
            @rollback="handleRollback"
          >
            <template #history>
              <DeployHistoryPanel
                :grouped-history="groupedHistory"
                :selected-history-id="selectedHistoryId"
                :history-loading="historyLoading"
                :is-group-expanded="isGroupExpanded"
                @select-record="loadHistoryRecord"
                @toggle-group="toggleGroupExpand"
                @rollback-record="handleHistoryRollback"
                @redeploy-record="handleRedeploy"
                @delete-record="handleDeleteHistory"
              />
            </template>
          </DeployExecutionPanel>
        </el-col>
      </el-row>
    </section>

    <!-- 配置差异预览对话框 -->
    <DeployPreviewDialog
      v-model="showPreviewDialog"
      :preview-loading="previewLoading"
      :preview-results="previewResults"
      v-model:selected-preview-device="selectedPreviewDevice"
      :impact-analysis="impactAnalysis"
      :is-dark="isDark"
      @deploy="confirmDeployFromPreview"
    />

    <!-- 变量说明对话框 -->
    <DeployVariableHelpDialog
      v-model="showVariableHelp"
      :all-variables="allVariables"
    />

    <!-- 操作者会话级 SSH 凭证 -->
    <SSHCredentialDialog ref="credDialog" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Loading,
  CircleCheckFilled,
  QuestionFilled,
  CircleClose,
  CircleCloseFilled
} from '@element-plus/icons-vue'
import { previewDeploy as previewDeployApi } from '@/api'
import { useI18n } from '@/composables/useI18n'
import DeployPreviewDialog from '@/components/DeployPreviewDialog.vue'
import DeployVariableHelpDialog from '@/components/DeployVariableHelpDialog.vue'
import DeployFormPanel from '@/components/DeployFormPanel.vue'
import DeployExecutionPanel from '@/components/DeployExecutionPanel.vue'
import DeployHistoryPanel from '@/components/DeployHistoryPanel.vue'
import { useDeployForm } from '@/composables/useDeployForm'
import { useDeployExecution } from '@/composables/useDeployExecution'
import { useDeployHistory } from '@/composables/useDeployHistory'
import SSHCredentialDialog from '@/components/SSHCredentialDialog.vue'
import { getSessionCredentials, setSessionCredentials } from '@/composables/useSessionCredentials'

const { t } = useI18n()
// 暗黑模式检测
const isDark = computed(() => document.documentElement.classList.contains('dark'))

// 变量说明对话框显隐
const showVariableHelp = ref(false)

// 操作者会话级 SSH 凭证（密码不存储在服务器上，仅浏览器会话 sessionStorage 复用）
const credDialog = ref(null)
const ensureDeployCredentials = async () => {
  const stored = getSessionCredentials()
  if (stored) return stored
  const creds = await credDialog.value.open()
  if (creds) setSessionCredentials(creds)
  return creds
}

// 配置表单状态（收拢于 useDeployForm，item 946 切片 4）
const {
  deployForm,
  executionMode,
  parallelLimit,
  devices,
  backups,
  templates,
  allVariables,
  availableVariables,
  loading,
  canDeploy,
  loadDevices,
  loadBackups,
  loadTemplates,
  loadCompatibleVariables,
  loadTemplateVariables
} = useDeployForm()

// 执行/历史状态（收拢于 useDeployExecution/useDeployHistory，item 946 切片 5）
// deployForm↔deviceExecutions 交叉耦合通过晚绑定 hooks/deps 解耦，避免循环构造
const execHooks = {}
const historyDeps = { deployForm }

const {
  executionStatus,
  elapsedTime,
  deviceExecutions,
  selectedDevice,
  totalDevices,
  completedDevices,
  inProgressDevices,
  failedDevices,
  progressPercentage,
  progressStatus,
  hasRollbackAvailable,
  initDeviceExecutions,
  setDeviceExecutions,
  setSelectedDevice,
  selectDevice,
  clearCliOutput,
  registerCliOutput,
  executeDeploy,
  handleRollback,
  aborting,
  confirmAbort
} = useDeployExecution({ deployForm, executionMode, parallelLimit, devices }, execHooks)

const history = useDeployHistory(historyDeps)
const {
  groupedHistory,
  selectedHistoryId,
  historyLoading,
  isGroupExpanded,
  toggleGroupExpand,
  loadHistoryRecord,
  handleHistoryRollback,
  handleRedeploy,
  handleDeleteHistory,
  loadHistory
} = history

// 晚绑定接线（构造完成后；实际调用发生在用户交互时，闭包惰性求值）
execHooks.ensureCredentials = () => ensureDeployCredentials()
execHooks.reloadHistory = () => history.loadHistory()
execHooks.setCurrentHistoryId = (id) => history.setCurrentHistoryId(id)
execHooks.getSelectedHistoryId = () => history.getSelectedHistoryId()
execHooks.getCurrentHistoryId = () => history.getCurrentHistoryId()
execHooks.setRedeployParentId = (id) => history.setRedeployParentId(id)
execHooks.clearRedeployParentId = () => history.clearRedeployParentId()
historyDeps.executeDeploy = () => executeDeploy()
historyDeps.handleRollback = () => handleRollback()
historyDeps.setDeviceExecutions = (list) => setDeviceExecutions(list)
historyDeps.setSelectedDevice = (dev) => setSelectedDevice(dev)

const handleDeviceChange = () => {
  // 重置设备执行列表
  initDeviceExecutions(deployForm.value.target_devices)
}
// Phase 3: 配置差异预览
const previewResults = ref([])
const showPreviewDialog = ref(false)
const previewLoading = ref(false)
const selectedPreviewDevice = ref(null)

// Phase 3: 影响分析
const impactAnalysis = ref({
  totalChanges: 0,
  affectedServices: [],
  estimatedDowntime: 0,
  riskLevel: 'low',
  highRiskDevices: 0
})


// 预览部署
const previewDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  const deployData = {
    mode: deployForm.value.mode,
    engine: deployForm.value.engine,
    napalm_mode: deployForm.value.napalm_mode,
    backup_file: deployForm.value.backup_file,
    template_id: deployForm.value.template_id,
    snippet: deployForm.value.snippet,
    snippet_position: deployForm.value.snippet_position,
    base_backup_file: deployForm.value.base_backup_file,
    target_devices: deployForm.value.target_devices,
    variables: {}
  }

  deployForm.value.variables.forEach(v => {
    if (v.key) deployData.variables[v.key] = v.value
  })

  previewLoading.value = true
  showPreviewDialog.value = true

  try {
    const result = await previewDeployApi(deployData)
    previewResults.value = result.preview || []
    selectedPreviewDevice.value = previewResults.value[0] || null

    // 更新影响分析
    impactAnalysis.value = {
      totalChanges: result.summary?.total_changes || 0,
      highRiskDevices: result.summary?.high_risk_devices || 0,
      affectedServices: [...new Set(previewResults.value.flatMap(p => p.impact?.affected_services || []))],
      estimatedDowntime: Math.max(...previewResults.value.map(p => p.impact?.estimated_downtime_seconds || 0)),
      riskLevel: result.summary?.high_risk_devices > 0 ? 'high' :
                 result.summary?.total_changes > 20 ? 'medium' : 'low'
    }

    ElMessage.success(t('deployPreviewSuccess'))
  } catch (error) {
    ElMessage.error(t('deployPreviewFailed'))
    showPreviewDialog.value = false
  } finally {
    previewLoading.value = false
  }
}

// 执行部署
const confirmDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  // 操作者会话级 SSH 凭证：缺少时先弹对话框收集（取消则中止部署）
  if (!(await ensureDeployCredentials())) return

  // 计算实际并行数量：串行模式为1，并行模式使用用户设置的值
  const actualParallelLimit = executionMode.value === 'serial' ? 1 : parallelLimit.value

  // 多设备部署确认
  if (deployForm.value.target_devices.length > 1) {
    const modeText = executionMode.value === 'serial'
      ? t('deploySerialModeLabel')
      : t('deployParallelModeLabel') + ` (${actualParallelLimit})`

    try {
      await ElMessageBox.confirm(
        t('deployMultiDeviceConfirm', {
          count: deployForm.value.target_devices.length,
          mode: modeText
        }),
        t('deployConfirmTitle'),
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


// 从预览确认部署
const confirmDeployFromPreview = async () => {
  showPreviewDialog.value = false
  await confirmDeploy()
}

onMounted(async () => {
  // 加载部署历史
  await loadHistory()

  // 依次加载，避免同时触发太多请求
  await loadDevices()
  await new Promise(r => setTimeout(r, 100))
  await loadBackups()
  await new Promise(r => setTimeout(r, 100))
  await loadTemplates()
  await new Promise(r => setTimeout(r, 100))
  loadCompatibleVariables()  // 这个请求失败不影响，可以并行
})

</script>

<style scoped>
/* ========================================
   使用全局 Theme Token（来自 tokens.css）
   不要重新定义变量，直接使用全局变量
   ======================================== */

.deploy-page {
  padding: 0;
  background: var(--bg-primary);
}

/* ========================================
   页面导航栏
   ======================================== */

.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--gap-md);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-tag {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 6px !important;
  white-space: nowrap !important;
}

/* 穿透 Element Plus el-tag 内部结构 */
.status-tag :deep(.el-tag__content) {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 6px !important;
}

/* 直接作用于 el-tag 的所有子元素 */
.status-tag.el-tag {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
}

.status-tag.el-tag--large {
  height: 32px;
  padding: 0 12px;
}

.status-tag :deep(.el-icon) {
  display: inline-flex !important;
  align-items: center !important;
  width: 14px !important;
  height: 14px !important;
  flex-shrink: 0 !important;
  margin-right: 0 !important;
  margin-bottom: 0 !important;
  vertical-align: middle !important;
}

.status-tag.el-tag--large :deep(.el-icon) {
  width: 16px !important;
  height: 16px !important;
}

.status-tag :deep(.is-loading) {
  display: inline-flex !important;
  align-items: center !important;
}

/* 确保 el-tag 内的文字也是 inline */
.status-tag,
.status-tag :deep(*) {
  vertical-align: middle !important;
}

.status-content {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.status-content .el-icon {
  display: inline-flex;
  align-items: center;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

/* 导航栏状态标签加载旋转 */
.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.nav-right {
  display: flex;
  gap: 10px;
}

/* ========================================
   按钮系统 - 现代、轻量、主次分明
   ======================================== */

.nav-action-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: none;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.nav-action-btn .el-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

/* 小按钮 */
.nav-action-btn.small {
  height: 22px;
  padding: 0 8px;
  font-size: 11px;
}

/* 主按钮 - deploy */
.nav-action-btn.deploy-btn {
  background: var(--accent-primary);
  color: white;
  border: none;
}

.nav-action-btn.deploy-btn:hover:not(.disabled) {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

.nav-action-btn.deploy-btn.disabled {
  background: rgba(0, 184, 148, 0.4);
  cursor: not-allowed;
}

/* 次按钮 */
.nav-action-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

/* 危险按钮 */
.nav-action-btn.danger {
  background: var(--accent-danger);
  color: white;
  border: none;
}

.nav-action-btn.danger:hover {
  background: #c42a2a;
  box-shadow: 0 2px 6px rgba(214, 48, 49, 0.2);
  transform: translateY(-1px);
}

/* 预览按钮 */
.nav-action-btn.preview-btn {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.preview-btn:hover:not(.disabled) {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
}

.nav-action-btn.preview-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ========================================
   主内容区域
   ======================================== */

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
</style>

<!-- 全局样式：Select 下拉框文字清晰化（下拉菜单挂载在 body 上，需要非 scoped） -->
<style>
/* Select 选项文字 */
.el-select-dropdown__item {
  color: var(--text-primary);
  font-size: 13px;
}

/* 选项 hover */
.el-select-dropdown__item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* 已选中 */
.el-select-dropdown__item.selected {
  color: var(--accent-secondary);
}

/* 暗色模式 Select 下拉框 */
.dark .el-select-dropdown__item {
  color: var(--text-primary);
}

.dark .el-select-dropdown__item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.dark .el-select-dropdown__item.selected {
  color: var(--accent-primary);
}
</style>
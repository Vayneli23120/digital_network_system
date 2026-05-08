<template>
  <div class="deploy-page">
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>{{ t('deployTitle') }}</span>
              <el-button type="info" size="small" @click="showVariableHelp = true">
                <el-icon><QuestionFilled /></el-icon>
                {{ t('deployVariableHelp') }}
              </el-button>
            </div>
          </template>

          <el-form :model="deployForm" label-width="120px">
            <el-form-item :label="t('deployMode')">
              <el-radio-group v-model="deployForm.mode">
                <el-radio label="backup">{{ t('deployFromBackup') }}</el-radio>
                <el-radio label="template">{{ t('deployUseTemplate') }}</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="deployForm.mode === 'backup'" :label="t('deployBackupFile')" required>
              <el-select
                v-model="deployForm.backup_file"
                :placeholder="t('deploySelectBackupFile')"
                style="width: 100%"
                filterable
              >
                <el-option
                  v-for="backup in backups"
                  :key="backup.id"
                  :label="`${backup.device_name} - ${backup.backup_file} (${formatDateTime(backup.backup_time)})`"
                  :value="backup.backup_file"
                />
              </el-select>
            </el-form-item>

            <el-form-item v-if="deployForm.mode === 'template'" :label="t('deployConfigTemplate')" required>
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
                    <span>{{ template.name }}</span>
                    <span class="template-desc">{{ template.description }}</span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>

            <el-divider />

            <el-form-item :label="t('deployTargetDevice')" required>
              <el-select
                v-model="deployForm.target_devices"
                multiple
                :placeholder="t('deploySelectDeviceMultiple')"
                style="width: 100%"
                filterable
              >
                <el-option
                  v-for="device in devices"
                  :key="device.id"
                  :label="`${device.name} - ${device.ip} (${device.credential_group || 'default'}${t('deployCredential')})`"
                  :value="device.id"
                  :disabled="device.status === 'offline'"
                >
                  <div class="device-option">
                    <span>{{ device.name }} - {{ device.ip }}</span>
                    <el-tag v-if="device.status !== 'online'" size="small" type="danger">{{ device.status }}</el-tag>
                  </div>
                </el-option>
              </el-select>
              <div class="form-tip">{{ t('deployDeviceTip') }}</div>
            </el-form-item>

            <el-form-item v-if="deployForm.mode === 'template'" :label="t('deployVariableReplace')">
              <el-table :data="deployForm.variables" style="width: 100%" border>
                <el-table-column prop="key" :label="t('deployVariableName')" width="180">
                  <template #default="{ row }">
                    <el-select v-model="row.key" :placeholder="t('deploySelectVariable')" style="width: 100%" filterable>
                      <el-option
                        v-for="v in availableVariables"
                        :key="v.key"
                        :label="`${v.key} - ${v.description}`"
                        :value="v.key"
                      />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column prop="value" :label="t('deployReplaceValue')">
                  <template #default="{ row }">
                    <el-input
                      v-model="row.value"
                      :placeholder="getVariablePlaceholder(row.key)"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="description" :label="t('deployDescription')" width="200">
                  <template #default="{ row }">
                    {{ getVariableDescription(row.key) }}
                  </template>
                </el-table-column>
                <el-table-column width="80" align="center">
                  <template #default="{ $index }">
                    <el-button
                      size="small"
                      type="danger"
                      @click="removeVariable($index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="form-tip" style="margin-top: 10px;">
                <el-button size="small" @click="addVariable">
                  <el-icon><Plus /></el-icon>
                  {{ t('deployAddVariable') }}
                </el-button>
                <el-button size="small" @click="autoFillVariables">
                  <el-icon><MagicStick /></el-icon>
                  {{ t('deployAutoFillVariables') }}
                </el-button>
              </div>
            </el-form-item>

            <el-form-item :label="t('deployDryRun')">
              <el-switch
                v-model="deployForm.dry_run"
                :active-text="t('deployPreviewMode')"
                :inactive-text="t('deployActualMode')"
              />
              <div class="form-tip">
                {{ t('deployPreviewTip') }}
              </div>
            </el-form-item>

            <el-form-item>
              <el-button
                type="warning"
                @click="previewDeploy"
                :disabled="!canDeploy || deployForm.dry_run === false"
                :loading="previewLoading"
              >
                <el-icon><View /></el-icon>
                {{ t('deployPreviewChange') }}
              </el-button>
              <el-button
                type="success"
                @click="confirmDeploy"
                :disabled="!canDeploy"
                :loading="deployLoading"
              >
                <el-icon><Upload /></el-icon>
                {{ deployForm.dry_run ? t('deployConfirmDeploy') : t('deployImmediateDeploy') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card v-loading="loading">
          <template #header>
            <span>{{ t('deployPreviewResult') }}</span>
          </template>

          <div v-if="previewResult" class="preview-content">
            <h4>{{ t('deployResultSummary') }}</h4>
            <div class="result-summary">
              <el-alert
                v-for="(result, index) in previewResult.results"
                :key="index"
                :title="`${result.device_name} (${result.device_ip})`"
                :type="result.success ? 'success' : 'error'"
                :description="result.message"
                show-icon
                style="margin-bottom: 10px;"
              />
            </div>

            <h4 style="margin-top: 20px;">{{ t('deployConfigChangeDetail') }}</h4>
            <div v-for="(result, index) in previewResult.results" :key="index">
              <div class="device-result">
                <h5>{{ result.device_name }} - {{ result.success ? t('deploySuccess') : t('deployFailed') }}</h5>
                <div v-if="result.changes && result.changes.length > 0" class="diff">
                  <div v-for="(change, cIndex) in result.changes" :key="cIndex" :class="['diff-line', change.type]">
                    <span class="diff-symbol">{{ change.type === 'add' ? '+' : '-' }}</span>
                    <span class="diff-content">{{ change.content }}</span>
                  </div>
                </div>
                <div v-else-if="result.message" class="no-changes">
                  <el-tag type="info">{{ t('deployNoChange') }}</el-tag>
                  <span>{{ result.message }}</span>
                </div>
                <div v-if="result.errors && result.errors.length > 0" class="errors">
                  <div v-for="(error, eIndex) in result.errors" :key="eIndex" class="error-line">
                    <el-icon><CircleClose /></el-icon>
                    {{ error }}
                  </div>
                </div>
              </div>
            </div>

            <h4 style="margin-top: 20px;">{{ t('deployConfigPreview') }}</h4>
            <pre class="config-preview">{{ previewResult.config_preview }}</pre>
          </div>

          <el-empty v-else :description="t('deployClickPreview')" />

          <div v-if="deployResult && !deployForm.dry_run" class="deploy-result">
            <el-divider />
            <h4>{{ t('deployActualResult') }}</h4>
            <div class="result-summary">
              <el-alert
                v-for="(result, index) in deployResult.results"
                :key="index"
                :title="`${result.device_name} (${result.device_ip})`"
                :type="result.success ? 'success' : 'error'"
                :description="result.message"
                :closable="false"
                show-icon
                style="margin-bottom: 10px;"
              />
            </div>
            <div v-if="deployResult.summary" class="deploy-summary">
              <el-statistic :title="t('deployTotalDevices')" :value="deployResult.summary.total" />
              <el-statistic :title="t('deploySuccess')" :value="deployResult.summary.success" />
              <el-statistic :title="t('deployFailed')" :value="deployResult.summary.failed" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 变量说明对话框 -->
    <el-dialog v-model="showVariableHelp" :title="t('deployVariableDialog')" width="800px">
      <el-table :data="allVariables" style="width: 100%">
        <el-table-column prop="key" :label="t('deployVariableName')" width="200" />
        <el-table-column prop="description" :label="t('deployDescription')" />
        <el-table-column prop="example" :label="t('deployExampleValue')" width="200" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  QuestionFilled,
  Delete,
  Plus,
  MagicStick,
  View,
  Upload,
  CircleClose
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

const { t } = useI18n()

const devices = ref([])
const backups = ref([])
const loading = ref(false)
const templates = ref([])
const allVariables = ref([])

const deployForm = ref({
  mode: 'backup',
  backup_file: '',
  template_id: '',
  target_devices: [],
  variables: [],
  dry_run: true
})

const availableVariables = ref([])
const previewResult = ref(null)
const deployResult = ref(null)
const previewLoading = ref(false)
const deployLoading = ref(false)
const showVariableHelp = ref(false)

const canDeploy = computed(() => {
  if (deployForm.value.target_devices.length === 0) return false
  if (deployForm.value.mode === 'backup') {
    return !!deployForm.value.backup_file
  } else {
    return !!deployForm.value.template_id
  }
})

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (error) {
    ElMessage.error(t('deployLoadDeviceFailed'))
  }
}

const loadBackups = async () => {
  try {
    const data = await getBackups({ limit: 50 })
    backups.value = data.items || []
  } catch (error) {
    ElMessage.error(t('deployLoadBackupFailed'))
  }
}

const loadTemplates = async () => {
  try {
    const data = await getTemplates()
    templates.value = data.items || []
  } catch (error) {
    ElMessage.error(t('deployLoadTemplateFailed'))
  }
}

const loadCompatibleVariables = async () => {
  try {
    const data = await getCompatibleVariables()
    allVariables.value = data.variables || []
  } catch (error) {
    ElMessage.error(t('deployLoadVariableFailed'))
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
        const vars = typeof data.variables === 'string' ? JSON.parse(data.variables) : data.variables
        availableVariables.value = vars
        // 清空当前变量并加载模板默认变量
        deployForm.value.variables = vars.map(v => ({
          key: v.key,
          value: v.default || ''
        }))
      } catch (e) {
        console.error('解析模板变量失败:', e)
      }
    }
  } catch (error) {
    ElMessage.error(t('deployLoadTemplateVarFailed'))
  }
}

const getVariablePlaceholder = (key) => {
  const v = allVariables.value.find(v => v.key === key)
  return v ? `${t('deployExample')}${v.example}` : ''
}

const getVariableDescription = (key) => {
  const v = allVariables.value.find(v => v.key === key)
  return v ? v.description : ''
}

const addVariable = () => {
  deployForm.value.variables.push({ key: '', value: '' })
}

const removeVariable = (index) => {
  deployForm.value.variables.splice(index, 1)
}

const autoFillVariables = () => {
  // 自动填充一些常用变量
  const commonVars = [
    { key: 'HOSTNAME', value: '' },
    { key: 'MGMT_IP', value: '' },
    { key: 'DEFAULT_GATEWAY', value: '' },
    { key: 'SNMP_COMMUNITY', value: 'YourSNMPCommunity' },
    { key: 'LOCATION', value: '' },
    { key: 'NTP_SERVER', value: '10.0.0.1' }
  ]

  deployForm.value.variables = commonVars.filter(v => {
    return !deployForm.value.variables.some(existing => existing.key === v.key)
  })
}

const previewDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  previewLoading.value = true
  previewResult.value = null

  try {
    const deployData = {
      mode: deployForm.value.mode,
      backup_file: deployForm.value.backup_file,
      template_id: deployForm.value.template_id,
      target_devices: deployForm.value.target_devices,
      variables: {}
    }

    // 转换变量为对象
    deployForm.value.variables.forEach(v => {
      if (v.key) {
        deployData.variables[v.key] = v.value
      }
    })

    const result = await previewDeployApi(deployData)
    previewResult.value = result
    ElMessage.success(t('deployPreviewSuccess'))
  } catch (error) {
    ElMessage.error(t('deployPreviewFailed'))
    ElMessage.error(`${t('deployPreviewFailed')}: ${error.response?.data?.detail || error.message}`)
  } finally {
    previewLoading.value = false
  }
}

const confirmDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  try {
    await ElMessageBox.confirm(
      deployForm.value.dry_run
        ? t('deployConfirmMessage')
        : t('deployWarningMessage'),
      t('deployConfirmTitle'),
      {
        confirmButtonText: t('actionConfirm'),
        cancelButtonText: t('actionCancel'),
        type: deployForm.value.dry_run ? 'warning' : 'error'
      }
    )
  } catch {
    return
  }

  deployLoading.value = true
  deployResult.value = null

  try {
    const deployData = {
      mode: deployForm.value.mode,
      backup_file: deployForm.value.backup_file,
      template_id: deployForm.value.template_id,
      target_devices: deployForm.value.target_devices,
      variables: {},
      dry_run: false
    }

    deployForm.value.variables.forEach(v => {
      if (v.key) {
        deployData.variables[v.key] = v.value
      }
    })

    const result = await executeDeployApi(deployData)
    deployResult.value = result
    ElMessage.success(result.message || t('deployComplete'))
  } catch (error) {
    ElMessage.error(t('deployFailed'))
    ElMessage.error(`${t('deployFailed')}: ${error.response?.data?.detail || error.message}`)
  } finally {
    deployLoading.value = false
  }
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.template-option .template-desc {
  font-size: 12px;
  color: #909399;
}

.device-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.preview-content h4 {
  margin-bottom: 15px;
  color: #303133;
}

.result-summary {
  margin-bottom: 20px;
}

.device-result {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.device-result h5 {
  margin-bottom: 10px;
  color: #303133;
}

.diff {
  background: #1e1e1e;
  padding: 10px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 300px;
  overflow-y: auto;
}

.diff-line {
  display: flex;
}

.diff-symbol {
  width: 20px;
  font-weight: bold;
}

.diff-line.add .diff-symbol {
  color: #22863a;
}

.diff-line.remove .diff-symbol {
  color: #cb2431;
}

.diff-content {
  flex: 1;
  color: #d4d4d4;
}

.no-changes {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #909399;
}

.errors {
  margin-top: 10px;
}

.error-line {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #f56c6c;
  font-size: 13px;
}

.config-preview {
  background: #f6f8fa;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.deploy-result {
  margin-top: 20px;
}

.deploy-summary {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
}
</style>
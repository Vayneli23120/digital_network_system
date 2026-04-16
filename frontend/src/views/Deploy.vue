<template>
  <div class="deploy-page">
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>配置部署</span>
              <el-button type="info" size="small" @click="showVariableHelp = true">
                <el-icon><QuestionFilled /></el-icon>
                变量说明
              </el-button>
            </div>
          </template>

          <el-form :model="deployForm" label-width="120px">
            <el-form-item label="部署方式">
              <el-radio-group v-model="deployForm.mode">
                <el-radio label="backup">从备份恢复</el-radio>
                <el-radio label="template">使用模板</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="deployForm.mode === 'backup'" label="备份文件" required>
              <el-select
                v-model="deployForm.backup_file"
                placeholder="选择备份文件"
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

            <el-form-item v-if="deployForm.mode === 'template'" label="配置模板" required>
              <el-select
                v-model="deployForm.template_id"
                placeholder="选择配置模板"
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

            <el-form-item label="目标设备" required>
              <el-select
                v-model="deployForm.target_devices"
                multiple
                placeholder="选择设备（可多选）"
                style="width: 100%"
                filterable
              >
                <el-option
                  v-for="device in devices"
                  :key="device.id"
                  :label="`${device.name} - ${device.ip} (${device.credential_group || 'default'}凭证)`"
                  :value="device.id"
                  :disabled="device.status === 'offline'"
                >
                  <div class="device-option">
                    <span>{{ device.name }} - {{ device.ip }}</span>
                    <el-tag v-if="device.status !== 'online'" size="small" type="danger">{{ device.status }}</el-tag>
                  </div>
                </el-option>
              </el-select>
              <div class="form-tip">提示：只有在线状态的设备可选择，离线设备将被禁用</div>
            </el-form-item>

            <el-form-item v-if="deployForm.mode === 'template'" label="变量替换">
              <el-table :data="deployForm.variables" style="width: 100%" border>
                <el-table-column prop="key" label="变量名" width="180">
                  <template #default="{ row }">
                    <el-select v-model="row.key" placeholder="选择变量" style="width: 100%" filterable>
                      <el-option
                        v-for="v in availableVariables"
                        :key="v.key"
                        :label="`${v.key} - ${v.description}`"
                        :value="v.key"
                      />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column prop="value" label="替换值">
                  <template #default="{ row }">
                    <el-input
                      v-model="row.value"
                      :placeholder="getVariablePlaceholder(row.key)"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="说明" width="200">
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
                  添加变量
                </el-button>
                <el-button size="small" @click="autoFillVariables">
                  <el-icon><MagicStick /></el-icon>
                  自动填充常用变量
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="Dry Run">
              <el-switch
                v-model="deployForm.dry_run"
                active-text="预览模式（不实际部署）"
                inactive-text="实际部署"
              />
              <div class="form-tip">
                预览模式下只展示配置变更，不会实际修改设备配置
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
                预览变更
              </el-button>
              <el-button
                type="success"
                @click="confirmDeploy"
                :disabled="!canDeploy"
                :loading="deployLoading"
              >
                <el-icon><Upload /></el-icon>
                {{ deployForm.dry_run ? '确认部署' : '立即部署' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card>
          <template #header>
            <span>部署预览/结果</span>
          </template>

          <div v-if="previewResult" class="preview-content">
            <h4>部署结果摘要：</h4>
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

            <h4 style="margin-top: 20px;">配置变更详情：</h4>
            <div v-for="(result, index) in previewResult.results" :key="index">
              <div class="device-result">
                <h5>{{ result.device_name }} - {{ result.success ? '成功' : '失败' }}</h5>
                <div v-if="result.changes && result.changes.length > 0" class="diff">
                  <div v-for="(change, cIndex) in result.changes" :key="cIndex" :class="['diff-line', change.type]">
                    <span class="diff-symbol">{{ change.type === 'add' ? '+' : '-' }}</span>
                    <span class="diff-content">{{ change.content }}</span>
                  </div>
                </div>
                <div v-else-if="result.message" class="no-changes">
                  <el-tag type="info">无变更</el-tag>
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

            <h4 style="margin-top: 20px;">配置预览（前 2000 字符）：</h4>
            <pre class="config-preview">{{ previewResult.config_preview }}</pre>
          </div>

          <el-empty v-else description="点击预览变更查看将要执行的变更" />

          <div v-if="deployResult && !deployForm.dry_run" class="deploy-result">
            <el-divider />
            <h4>实际部署结果：</h4>
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
              <el-statistic title="总设备数" :value="deployResult.summary.total" />
              <el-statistic title="成功" :value="deployResult.summary.success" />
              <el-statistic title="失败" :value="deployResult.summary.failed" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 变量说明对话框 -->
    <el-dialog v-model="showVariableHelp" title="可用变量说明" width="800px">
      <el-table :data="allVariables" style="width: 100%">
        <el-table-column prop="key" label="变量名" width="200" />
        <el-table-column prop="description" label="说明" />
        <el-table-column prop="example" label="示例值" width="200" />
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
import dayjs from 'dayjs'

const devices = ref([])
const backups = ref([])
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

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

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
    console.error('加载设备列表失败:', error)
  }
}

const loadBackups = async () => {
  try {
    const data = await getBackups({ limit: 50 })
    backups.value = data.items || []
  } catch (error) {
    console.error('加载备份列表失败:', error)
  }
}

const loadTemplates = async () => {
  try {
    const data = await getTemplates()
    templates.value = data.items || []
  } catch (error) {
    console.error('加载模板列表失败:', error)
  }
}

const loadCompatibleVariables = async () => {
  try {
    const data = await getCompatibleVariables()
    allVariables.value = data.variables || []
  } catch (error) {
    console.error('加载变量列表失败:', error)
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
    console.error('加载模板变量失败:', error)
  }
}

const getVariablePlaceholder = (key) => {
  const v = allVariables.value.find(v => v.key === key)
  return v ? `例如：${v.example}` : ''
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
    ElMessage.warning('请先选择部署方式和目标设备')
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
    ElMessage.success('预览生成成功')
  } catch (error) {
    console.error('预览失败:', error)
    ElMessage.error(`预览失败：${error.response?.data?.detail || error.message}`)
  } finally {
    previewLoading.value = false
  }
}

const confirmDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning('请先选择部署方式和目标设备')
    return
  }

  try {
    await ElMessageBox.confirm(
      deployForm.value.dry_run
        ? '确认要执行部署吗？这将把配置推送到选中的设备。'
        : '警告：实际部署将直接修改设备配置，请确认已预览变更！',
      '确认部署',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
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
    ElMessage.success(result.message || '部署完成')
  } catch (error) {
    console.error('部署失败:', error)
    ElMessage.error(`部署失败：${error.response?.data?.detail || error.message}`)
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

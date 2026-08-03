<template>
  <el-dialog
    v-model="visible"
    :title="t('complianceRunCheck')"
    width="700px"
    append-to-body
    draggable
    align-center
    class="compliance-dialog"
  >
    <el-tabs v-model="auditTab" class="audit-tabs">
      <!-- 文件上传 -->
      <el-tab-pane name="upload" :label="t('complianceUploadConfig')">
        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            accept=".txt,.cfg,.log,.xlsx,.xls,.conf"
            drag
            class="config-upload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              {{ t('complianceUploadConfigHint') }}
            </div>
          </el-upload>

          <!-- 文件解析结果 -->
          <div class="parse-result" v-if="parseResult">
            <div class="parse-info">
              <span class="info-item">
                <span class="label">{{ t('complianceHostname') }}:</span>
                <span class="value">{{ parseResult.hostname || '-' }}</span>
              </span>
              <span class="info-item">
                <span class="label">{{ t('complianceDeviceType') }}:</span>
                <span class="value">{{ parseResult.device_type }}</span>
              </span>
              <span class="info-item">
                <span class="label">{{ t('complianceConfigLines') }}:</span>
                <span class="value">{{ parseResult.config_lines }}</span>
              </span>
              <span class="info-item" v-if="parseResult.device_count">
                <span class="label">{{ t('complianceDeviceCount') }}:</span>
                <span class="value">{{ parseResult.device_count }}</span>
              </span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 手动输入 -->
      <el-tab-pane name="manual" :label="t('complianceManualInput')">
        <el-form :model="auditForm" label-width="100px" size="default" class="config-form">
          <div class="form-section">
            <div class="section-header">
              <el-icon><Connection /></el-icon>
              <span>{{ t('complianceDeviceSection') }}</span>
            </div>
            <el-form-item :label="t('complianceDeviceName')">
              <el-input v-model="auditForm.device_name" />
            </el-form-item>
            <el-form-item :label="t('complianceDeviceIp')">
              <el-input v-model="auditForm.device_ip" />
            </el-form-item>
          </div>

          <div class="form-section">
            <div class="section-header">
              <el-icon><Document /></el-icon>
              <span>{{ t('complianceConfigSection') }}</span>
            </div>
            <el-form-item :label="t('complianceConfigText')">
              <el-input
                v-model="auditForm.config_text"
                type="textarea"
                :rows="12"
                :placeholder="t('complianceConfigPlaceholder')"
                class="snippet-input"
              />
            </el-form-item>
          </div>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <!-- 审核选项 -->
    <div class="audit-options">
      <div class="option-row">
        <span class="option-label">{{ t('complianceAuditMode') }}</span>
        <el-radio-group v-model="auditForm.audit_mode" size="small">
          <el-radio-button value="full">{{ t('complianceAuditModeFull') }}</el-radio-button>
          <el-radio-button value="basic">{{ t('complianceAuditModeBasic') }}</el-radio-button>
          <el-radio-button value="ai_only">{{ t('complianceAuditModeAIOnly') }}</el-radio-button>
        </el-radio-group>
      </div>
      <div class="option-row" v-if="auditForm.audit_mode !== 'basic'">
        <el-checkbox v-model="auditForm.use_ai" :disabled="!hasAIPermission">{{ t('complianceUseAI') }}</el-checkbox>
        <span class="ai-config-status" v-if="!aiConfigured">
          <el-icon><Warning /></el-icon>
          {{ t('complianceAIConfigHint') }}
        </span>
        <span class="ai-config-status" v-if="!hasAIPermission">
          <el-icon><Warning /></el-icon>
          {{ t('aiPermissionNoPermission') }}
        </span>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <button class="nav-action-btn secondary" @click="visible = false">
          {{ t('actionCancel') }}
        </button>
        <button class="nav-action-btn deploy-btn" @click="runAudit" :disabled="auditing">
          <el-icon v-if="auditing" class="is-loading"><Loading /></el-icon>
          {{ t('complianceRunCheck') }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Connection, Document, Warning, Loading } from '@element-plus/icons-vue'
import { uploadConfigFile, runComplianceCheck } from '@/api'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  hasAIPermission: { type: Boolean, default: true },
  aiConfigured: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'completed'])

const configText = defineModel('configText', { type: String, default: '' })

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const auditTab = ref('upload')
const uploadRef = ref(null)
const currentFile = ref(null)
const parseResult = ref(null)

const auditForm = reactive({
  device_name: '',
  device_ip: '',
  config_text: '',
  audit_mode: 'full',
  use_ai: true
})

const auditing = ref(false)

// 打开时重置表单（对齐原 showAuditDialog）
watch(() => props.modelValue, (val) => {
  if (val) {
    auditTab.value = 'upload'
    currentFile.value = null
    parseResult.value = null
    auditForm.device_name = ''
    auditForm.device_ip = ''
    auditForm.config_text = ''
    auditForm.audit_mode = 'full'
    auditForm.use_ai = true
    configText.value = ''
  }
})

// 文件上传处理
const handleFileChange = (file) => {
  currentFile.value = file.raw
  parseResult.value = null
}

const handleExceed = () => {
  ElMessage.warning(t('uploadLimitExceeded'))
}

// 运行审核
const runAudit = async () => {
  auditing.value = true

  try {
    // 文件上传模式
    if (auditTab.value === 'upload' && currentFile.value) {
      const formData = new FormData()
      formData.append('file', currentFile.value)

      const data = await uploadConfigFile(formData)
      parseResult.value = data.parse_result

      let reportObj
      if (data.format === 'multi_device') {
        // 多设备批量审核结果
        reportObj = {
          total_checks: data.device_count,
          passed: data.audit_results.filter(r => r.compliance_score >= 80).length,
          failed: data.audit_results.filter(r => r.compliance_score < 80).length,
          compliance_score: Math.round(data.audit_results.reduce((sum, r) => sum + r.compliance_score, 0) / data.device_count),
          results: data.audit_results.map(r => ({
            check_id: r.device_name,
            check_name: r.device_ip || r.device_name,
            category: 'compliance',
            severity: r.compliance_score >= 80 ? 'low' : 'high',
            passed: r.compliance_score >= 80,
            detail: `${t('complianceScore')}: ${r.compliance_score}%`,
            recommendation: ''
          })),
          audit_mode: 'batch'
        }
      } else {
        // 单设备审核结果
        reportObj = data.audit_result
      }

      ElMessage.success(`${t('complianceCheckComplete')}: ${reportObj.compliance_score}%`)
      emit('completed', reportObj)
      visible.value = false
    } else {
      // 手动输入模式
      if (!auditForm.config_text.trim()) {
        ElMessage.warning(t('complianceConfigPlaceholder'))
        return
      }

      const data = await runComplianceCheck(auditForm)
      ElMessage.success(`${t('complianceCheckComplete')}: ${data.compliance_score}%`)
      configText.value = auditForm.config_text
      emit('completed', data)
      visible.value = false
    }
  } catch (e) {
    ElMessage.error(t('complianceCheckFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    auditing.value = false
  }
}
</script>

<style scoped>
/* ========================================
   按钮系统
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

.nav-action-btn.deploy-btn {
  background: var(--accent-primary);
  color: white;
  border: none;
}

.nav-action-btn.deploy-btn:hover:not(:disabled) {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

.nav-action-btn.deploy-btn:disabled {
  background: rgba(0, 184, 148, 0.4);
  cursor: not-allowed;
}

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

/* ========================================
   对话框表单卡片
   ======================================== */

.compliance-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}

.compliance-dialog .section-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}

.compliance-dialog .section-header .el-icon {
  color: var(--accent-primary);
}

.compliance-dialog .el-form-item {
  margin-bottom: 10px;
}

/* ========================================
   上传区域
   ======================================== */

.upload-area {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.config-upload {
  width: 100%;
}

.config-upload :deep(.el-upload-dragger) {
  background: var(--bg-hover);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 24px;
}

.config-upload :deep(.el-upload-dragger:hover) {
  border-color: var(--accent-secondary);
}

.config-upload :deep(.el-icon--upload) {
  color: var(--text-tertiary);
  font-size: 32px;
}

.config-upload :deep(.el-upload__text) {
  color: var(--text-secondary);
  font-size: 13px;
}

.parse-result {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
}

.parse-info {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-md);
}

.parse-info .info-item {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
}

.parse-info .label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.parse-info .value {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

/* ========================================
   审核选项
   ======================================== */

.audit-options {
  margin-top: var(--gap-md);
  padding: var(--gap-md);
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.option-row {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.option-row + .option-row {
  margin-top: var(--gap-sm);
}

.option-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.ai-config-status {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  font-size: 12px;
  color: var(--accent-danger);
}

/* ========================================
   对话框底部
   ======================================== */

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}

/* ========================================
   表单输入样式
   ======================================== */

.config-form :deep(.el-input__wrapper) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: none;
  padding: 0 12px;
  height: 32px;
  transition: all 0.15s ease;
}

.config-form :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
  background: var(--bg-card);
}

.config-form :deep(.el-input__inner) {
  font-size: 14px;
  color: var(--text-primary);
  height: 32px;
}

.config-form :deep(.el-input__inner::placeholder) {
  color: var(--text-tertiary);
  font-size: 13px;
  opacity: 1;
}

/* Textarea */
.config-form :deep(.el-textarea__inner) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-primary);
  padding: 12px;
  transition: all 0.15s ease;
  box-shadow: none;
}

.config-form :deep(.el-textarea__inner:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-textarea__inner:focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

/* Snippet input 特殊样式 */
.snippet-input :deep(.el-textarea__inner) {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
}

/* ========================================
   暗色模式
   ======================================== */

.dark .compliance-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .compliance-dialog .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}

.dark .compliance-dialog .section-header .el-icon {
  color: #58a6ff;
}

.dark .config-form :deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-input__wrapper.is-focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

.dark .config-form :deep(.el-textarea__inner) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-textarea__inner:focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

.dark .parse-result {
  background: var(--bg-tertiary);
}

.dark .audit-options {
  background: var(--bg-tertiary);
}

.dark .config-upload :deep(.el-upload-dragger) {
  background: var(--bg-tertiary);
}
</style>

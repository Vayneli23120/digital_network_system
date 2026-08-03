<template>
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
          <el-radio-button label="snippet">
            <el-icon><Edit /></el-icon>
            {{ t('deploySnippet') }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 部署引擎选择 -->
      <div class="form-section">
        <div class="section-label">{{ t('deployEngine') }}</div>
        <el-radio-group v-model="deployForm.engine" size="small">
          <el-radio-button label="napalm" :disabled="deployForm.mode === 'template' || deployForm.mode === 'backup'">
            <el-icon><Shield /></el-icon>
            {{ t('deployEngineNapalm') }}
            <el-tag type="success" size="small" effect="plain" class="engine-tag">{{ t('deployEngineNapalmTag') }}</el-tag>
          </el-radio-button>
          <el-radio-button label="netmiko">
            <el-icon><Connection /></el-icon>
            {{ t('deployEngineNetmiko') }}
            <el-tag type="info" size="small" effect="plain" class="engine-tag">{{ t('deployEngineNetmikoTag') }}</el-tag>
          </el-radio-button>
        </el-radio-group>
        <div v-if="deployForm.mode === 'template' || deployForm.mode === 'backup'" class="engine-tip warning">
          <el-icon><WarningFilled /></el-icon>
          {{ t('deployBackupTemplateNetmikoOnly') }}
        </div>
        <div v-else-if="deployForm.engine === 'napalm'" class="engine-tip safe">
          <el-icon><InfoFilled /></el-icon>
          {{ t('deployEngineNapalmTip') }}
        </div>
      </div>

      <!-- NAPALM 传输方式选择 -->
      <div v-if="deployForm.engine === 'napalm'" class="form-section">
        <div class="section-label">{{ t('deployNapalmTransfer') }}</div>
        <el-radio-group v-model="deployForm.transfer_mode" size="small">
          <el-radio-button label="scp">
            {{ t('deployTransferScp') }}
            <el-tag type="success" size="small" effect="plain" class="engine-tag">{{ t('deployTransferScpTag') }}</el-tag>
          </el-radio-button>
          <el-radio-button label="inline">
            {{ t('deployTransferInline') }}
            <el-tag type="warning" size="small" effect="plain" class="engine-tag">{{ t('deployTransferInlineTag') }}</el-tag>
          </el-radio-button>
        </el-radio-group>
        <div class="napalm-mode-tip">
          {{ deployForm.transfer_mode === 'scp' ? t('deployTransferScpTip') : t('deployTransferInlineTip') }}
        </div>
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
          @change="(val) => emit('template-change', val)"
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

      <!-- 配置片段模式 -->
      <div v-if="deployForm.mode === 'snippet'" class="form-section">
        <div class="section-label required">{{ t('deploySnippetContent') }}</div>
        <el-input
          v-model="deployForm.snippet"
          type="textarea"
          :rows="8"
          :placeholder="t('deploySnippetPlaceholder')"
          style="width: 100%"
          class="snippet-input"
        />
        <div class="section-desc">{{ t('deploySnippetTip') }}</div>

        <!-- 片段位置 -->
        <div class="section-label" style="margin-top: 12px;">{{ t('deploySnippetPosition') }}</div>
        <el-radio-group v-model="deployForm.snippet_position" size="small">
          <el-radio-button label="smart">{{ t('deploySnippetSmart') }}</el-radio-button>
          <el-radio-button label="append">{{ t('deploySnippetAppend') }}</el-radio-button>
          <el-radio-button label="prepend">{{ t('deploySnippetPrepend') }}</el-radio-button>
          <el-radio-button label="replace">{{ t('deploySnippetReplace') }}</el-radio-button>
        </el-radio-group>
        <div v-if="deployForm.snippet_position === 'smart'" class="smart-mode-tip">
          <el-icon class="tip-icon"><InfoFilled /></el-icon>
          <span class="tip-text">{{ t('deploySmartModeTip') }}</span>
        </div>

        <!-- 基础配置选择（可选） -->
        <div class="section-label" style="margin-top: 12px;">{{ t('deploySnippetBaseConfig') }}</div>
        <el-select
          v-model="deployForm.base_backup_file"
          :placeholder="t('deploySelectBackupOptional')"
          style="width: 100%"
          clearable
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
        <div class="section-desc">{{ t('deploySnippetBaseTip') }}</div>
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
          @change="() => emit('device-change')"
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

        <!-- 执行模式选择 -->
        <div v-if="deployForm.target_devices.length > 1" class="execution-mode-section">
          <div class="mode-options">
            <el-radio-group v-model="executionMode" size="small">
              <el-radio-button value="serial">
                <span class="mode-option-content">
                  <el-icon><Loading /></el-icon>
                  <span>{{ t('deploySerialModeLabel') }}</span>
                </span>
              </el-radio-button>
              <el-radio-button value="parallel">
                <span class="mode-option-content">
                  <el-icon><CircleCheckFilled /></el-icon>
                  <span>{{ t('deployParallelModeLabel') }}</span>
                </span>
              </el-radio-button>
            </el-radio-group>
          </div>
          <div v-if="executionMode === 'parallel'" class="parallel-limit-input">
            <span class="limit-label">{{ t('deployParallelLimitLabel') }}</span>
            <el-input-number
              v-model="parallelLimit"
              :min="1"
              :max="5"
              size="small"
              controls-position="right"
            />
            <span class="limit-tip">{{ t('deployParallelLimitTip') }}</span>
          </div>
        </div>
      </div>

      <!-- 变量替换 -->
      <div v-if="deployForm.mode === 'template' && availableVariables.length > 0" class="form-section">
        <div class="section-label">{{ t('deployVariableReplace') }}</div>
        <div class="variables-list">
          <div
            v-for="(variable, index) in deployForm.variables"
            :key="variable._uid"
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
          type="button"
          class="nav-action-btn secondary preview-btn"
          @click="emit('preview')"
          :disabled="!canDeploy || !deployForm.dry_run"
          :class="{ disabled: !canDeploy || !deployForm.dry_run }"
        >
          <el-icon><View /></el-icon>
          {{ t('deployPreviewChange') }}
        </button>
        <button
          type="button"
          class="nav-action-btn deploy-btn"
          @click="emit('deploy')"
          :disabled="!canDeploy"
          :class="{ disabled: !canDeploy }"
        >
          <el-icon><Upload /></el-icon>
          {{ t('deployStart') }}
        </button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import {
  Document,
  Files,
  Edit,
  Connection,
  WarningFilled,
  InfoFilled,
  Loading,
  CircleCheckFilled,
  Delete,
  Plus,
  View,
  Upload
} from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/time'
import { stampUid } from '@/utils/uid.js'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  loading: { type: Boolean, default: false },
  devices: { type: Array, default: () => [] },
  backups: { type: Array, default: () => [] },
  templates: { type: Array, default: () => [] },
  availableVariables: { type: Array, default: () => [] },
  allVariables: { type: Array, default: () => [] },
  canDeploy: { type: Boolean, default: false }
})

const deployForm = defineModel('deploy-form', { type: Object, required: true })
const executionMode = defineModel('execution-mode', { type: String, default: 'serial' })
const parallelLimit = defineModel('parallel-limit', { type: Number, default: 1 })

const emit = defineEmits(['template-change', 'device-change', 'preview', 'deploy'])

const { t } = useI18n()

// 变量操作
const getVariablePlaceholder = (key) => {
  const v = props.allVariables.find(v => v.key === key)
  return v ? t('deployExample') + v.example : ''
}

const addVariable = () => {
  deployForm.value.variables.push(stampUid({ key: '', value: '' }))
}

const removeVariable = (index) => {
  deployForm.value.variables.splice(index, 1)
}
</script>

<style scoped>
/* ========================================
   使用全局 Theme Token（来自 tokens.css）
   不要重新定义变量，直接使用全局变量
   ======================================== */

/* ========================================
   操作按钮 - 通用按钮样式
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
   配置面板 - 更紧凑
   ======================================== */

.config-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
  height: 100%;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.config-panel::-webkit-scrollbar {
  width: var(--gap-xs);
}

.config-panel::-webkit-scrollbar-track {
  background: transparent;
}

.config-panel::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 3px;
}

.config-panel::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}

.panel-header {
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ========================================
   表单区域 - 现代 DevOps 风格
   ======================================== */

.form-section {
  margin-bottom: 16px;
}

.section-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.section-label.required::after {
  content: '';
  /* 不显示红色星号，更现代的方式 */
}

.section-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
  line-height: 1.4;
}

/* ========================================
   Input 输入框 - 更现代更细
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

/* Placeholder 提高可见度 */
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
   Select 选择器 - 更轻更科技
   ======================================== */

.config-form :deep(.el-select) {
  width: 100%;
}

.config-form :deep(.el-select .el-input__wrapper) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  height: 32px;
  padding: 0 32px 0 12px;
  box-shadow: none;
  transition: all 0.15s ease;
}

.config-form :deep(.el-select .el-input__wrapper:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-select .el-input__wrapper.is-focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

/* ========================================
   Radio Group - 扁平现代（完整样式）
   ======================================== */

.mode-radio-group {
  display: flex;
  width: 100%;
  gap: 2px;
  flex-wrap: nowrap;
}

.mode-radio-group :deep(.el-radio-button) {
  flex: 1;
  min-width: 0;
}

.mode-radio-group :deep(.el-radio-button__inner) {
  width: 100%;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s ease;
  box-shadow: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 激活状态 */
.mode-radio-group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: rgba(9, 132, 227, 0.1);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
  box-shadow: 0 0 0 1px var(--accent-secondary);
}

/* Hover */
.mode-radio-group :deep(.el-radio-button__inner:hover) {
  border-color: var(--accent-secondary);
}

.execution-mode-section {
  margin-top: var(--gap-md);
  padding: var(--gap-md);
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.mode-options {
  display: flex;
  align-items: center;
}

.mode-options :deep(.el-radio-group) {
  display: inline-flex;
}

.mode-option-content {
  display: inline-flex;
  align-items: center;
  gap: var(--gap-xs);
}

.mode-option-content .el-icon {
  width: 14px;
  height: 14px;
}

.parallel-limit-input {
  display: inline-flex;
  align-items: center;
  gap: var(--gap-sm);
  margin-top: var(--gap-md);
  padding-left: var(--gap-md);
}

.limit-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.limit-tip {
  font-size: 12px;
  color: var(--text-muted);
}

/* ========================================
   引擎选择
   ======================================== */

.engine-tag {
  margin-left: var(--gap-xs);
  font-size: 11px;
}

/* Engine 提示 - 固定在 radio-group 下面 */
.engine-tip {
  margin-top: var(--gap-sm);
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  padding: var(--gap-xs) 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  width: 100%;
}

.engine-tip.safe {
  background: var(--success-bg);
  color: var(--accent-primary);
}

.engine-tip.warning {
  background: var(--warning-bg);
  color: var(--accent-warning);
}

/* NAPALM 模式提示 - 固定在 radio-group 下面 */
.napalm-mode-tip {
  margin-top: var(--gap-xs);
  font-size: 12px;
  color: var(--text-secondary);
  padding: var(--gap-xs) 10px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  width: 100%;
}

/* Smart 模式提示 - 固定在 radio-group 下面 */
.smart-mode-tip {
  margin-top: var(--gap-sm);
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--gap-xs);
  padding: var(--gap-xs) 10px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  width: 100%;
}

.smart-mode-tip .tip-icon,
.smart-mode-tip .tip-text {
  color: var(--text-secondary);
  font-size: 12px;
}

/* ========================================
   Checkbox - 更现代
   ======================================== */

.config-form :deep(.el-checkbox) {
  height: auto;
  display: flex;
  align-items: center;
}

.config-form :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: var(--accent-secondary);
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-checkbox__inner) {
  transition: all 0.15s ease;
}

.config-form :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--text-primary);
}

/* 暗色模式 checkbox */
.dark .config-form :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

.dark .config-form :deep(.el-checkbox__label) {
  color: var(--text-secondary);
}

/* ========================================
   Engine radio 特殊样式
   ======================================== */

.config-form .el-radio-group :deep(.el-radio-button__inner) {
  padding: 6px 10px;
  font-size: 11px;
}

/* Engine tag 更小 */
.engine-tag {
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 3px;
}

/* ========================================
   选项样式
   ======================================== */

.backup-option,
.template-option,
.device-option {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
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
  color: var(--text-secondary);
}

/* ========================================
   变量区域
   ======================================== */

.variables-list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.variable-item {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.add-var-btn {
  margin-top: var(--gap-xs);
}

/* ========================================
   操作按钮
   ======================================== */

.actions-section {
  display: flex;
  gap: var(--gap-md);
  padding-top: var(--gap-md);
  border-top: 1px solid var(--border-subtle);
}

.preview-btn,
.deploy-btn {
  flex: 1;
  justify-content: center;
}

/* ========================================
   3. Focus effect on inputs
   ======================================== */

.config-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.12);
}

.dark .config-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.12);
}

/* 4. Smooth hover transitions for inputs */
.config-form :deep(.el-input__wrapper),
.config-form :deep(.el-select .el-input__wrapper),
.config-form :deep(.el-textarea__inner) {
  transition: all 0.15s ease;
}

/* ========================================
   暗色模式兼容
   ======================================== */

.dark .config-panel {
  background: var(--bg-card);
  border-color: var(--border-default);
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

.dark .config-form :deep(.el-select .el-input__wrapper) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-select .el-input__wrapper.is-focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

.dark .mode-radio-group :deep(.el-radio-button__inner) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .mode-radio-group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: rgba(0, 184, 148, 0.1);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}
</style>

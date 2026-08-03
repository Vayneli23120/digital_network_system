<template>
  <el-dialog
    v-model="visible"
    :title="t('complianceRulesTitle') + ' - ' + (currentRule?.rule_id || '')"
    width="650px"
    append-to-body
    draggable
    align-center
    class="compliance-dialog rule-detail-dialog"
  >
    <div class="rule-detail-content" v-if="currentRule">
      <!-- 编辑模式切换 -->
      <div class="edit-mode-bar">
        <el-checkbox v-model="ruleEditMode" @change="onEditModeChange">
          {{ t('complianceRuleEditMode') }}
        </el-checkbox>
      </div>

      <!-- 规则头部信息 -->
      <div class="rule-header-section">
        <div class="rule-title-row" v-if="!ruleEditMode">
          <span class="rule-id-badge">{{ currentRule.rule_id }}</span>
          <span class="rule-name-text">{{ currentRule.name }}</span>
        </div>
        <div class="rule-title-row" v-else>
          <span class="rule-id-badge">{{ currentRule.rule_id }}</span>
          <el-input v-model="ruleEditForm.name" class="rule-name-input" />
        </div>
        <div class="rule-meta-row" v-if="!ruleEditMode">
          <el-tag :type="categoryType(currentRule.category)" size="small">{{ currentRule.category }}</el-tag>
          <el-tag :type="severityType(currentRule.severity)" size="small">{{ currentRule.severity }}</el-tag>
          <el-tag :type="currentRule.source_type === 'auto' ? 'success' : 'info'" size="small">
            {{ currentRule.source_type === 'auto' ? t('complianceRuleSourceAuto') : t('complianceRuleSourceManual') }}
          </el-tag>
        </div>
        <div class="rule-meta-row" v-else>
          <el-select v-model="ruleEditForm.category" size="small" style="width: 120px">
            <el-option value="security" :label="t('complianceCategorySecurity')" />
            <el-option value="availability" :label="t('complianceCategoryAvailability')" />
            <el-option value="compliance" :label="t('complianceCategoryCompliance')" />
          </el-select>
          <el-select v-model="ruleEditForm.severity" size="small" style="width: 100px">
            <el-option value="critical" label="critical" />
            <el-option value="high" label="high" />
            <el-option value="medium" label="medium" />
            <el-option value="low" label="low" />
          </el-select>
        </div>
      </div>

      <!-- 匹配模式 -->
      <div class="rule-section">
        <div class="section-title">{{ t('complianceRulePattern') }}</div>
        <div class="pattern-box" v-if="!ruleEditMode">
          <code class="pattern-code">{{ currentRule.pattern || t('valueNa') }}</code>
        </div>
        <el-input v-else v-model="ruleEditForm.pattern" type="textarea" :rows="2" class="edit-input" />
      </div>

      <!-- 检查逻辑 -->
      <div class="rule-section">
        <div class="section-title">{{ t('complianceRuleLogic') }}</div>
        <div class="logic-text" v-if="!ruleEditMode">{{ currentRule.check_logic || t('valueNa') }}</div>
        <el-input v-else v-model="ruleEditForm.check_logic" type="textarea" :rows="3" class="edit-input" />
      </div>

      <!-- 修复建议 -->
      <div class="rule-section">
        <div class="section-title">{{ t('complianceFixRecommendation') }}</div>
        <div class="recommendation-box" v-if="!ruleEditMode">
          <pre class="recommendation-code">{{ currentRule.recommendation || t('valueNa') }}</pre>
        </div>
        <el-input v-else v-model="ruleEditForm.recommendation" type="textarea" :rows="4" class="edit-input" />
      </div>

      <!-- 规则状态 -->
      <div class="rule-status-section">
        <span class="status-label">{{ t('complianceRuleEnabled') }}:</span>
        <el-switch
          v-if="!ruleEditMode"
          v-model="currentRule.is_active"
          @change="emit('toggle-status', currentRule.id, currentRule.is_active)"
        />
        <el-switch
          v-else
          v-model="ruleEditForm.is_active"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <button class="nav-action-btn secondary" @click="visible = false" v-if="!ruleEditMode">
          {{ t('actionCancel') }}
        </button>
        <button class="nav-action-btn secondary" @click="cancelEdit" v-if="ruleEditMode">
          {{ t('actionCancel') }}
        </button>
        <button class="nav-action-btn deploy-btn" @click="saveRuleEdit" :disabled="savingRule" v-if="ruleEditMode">
          <el-icon v-if="savingRule" class="is-loading"><Loading /></el-icon>
          {{ t('save') }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { updateRule } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { categoryType, severityType } from '@/utils/compliance.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  currentRule: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'toggle-status'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const currentRule = computed(() => props.currentRule)

const ruleEditMode = ref(false)
const ruleEditForm = reactive({
  name: '',
  category: '',
  severity: '',
  pattern: '',
  check_logic: '',
  recommendation: '',
  is_active: true
})
const savingRule = ref(false)

// 打开时重置编辑模式并初始化表单
watch(() => props.modelValue, (val) => {
  if (val && props.currentRule) {
    ruleEditMode.value = false
    ruleEditForm.name = props.currentRule.name
    ruleEditForm.category = props.currentRule.category
    ruleEditForm.severity = props.currentRule.severity
    ruleEditForm.pattern = props.currentRule.pattern || ''
    ruleEditForm.check_logic = props.currentRule.check_logic || ''
    ruleEditForm.recommendation = props.currentRule.recommendation || ''
    ruleEditForm.is_active = props.currentRule.is_active
  }
})

// 编辑模式切换
const onEditModeChange = (val) => {
  if (val && currentRule.value) {
    // 进入编辑模式，重新初始化表单
    ruleEditForm.name = currentRule.value.name
    ruleEditForm.category = currentRule.value.category
    ruleEditForm.severity = currentRule.value.severity
    ruleEditForm.pattern = currentRule.value.pattern || ''
    ruleEditForm.check_logic = currentRule.value.check_logic || ''
    ruleEditForm.recommendation = currentRule.value.recommendation || ''
    ruleEditForm.is_active = currentRule.value.is_active
  }
}

// 取消编辑
const cancelEdit = () => {
  ruleEditMode.value = false
}

// 保存规则编辑（原位更新共享对象：props.currentRule 与父 rules 表格行是同一引用）
const saveRuleEdit = async () => {
  savingRule.value = true
  try {
    const data = await updateRule(props.currentRule.id, {
      name: ruleEditForm.name,
      category: ruleEditForm.category,
      severity: ruleEditForm.severity,
      pattern: ruleEditForm.pattern,
      check_logic: ruleEditForm.check_logic,
      recommendation: ruleEditForm.recommendation,
      is_active: ruleEditForm.is_active
    })

    if (data.success) {
      ElMessage.success(t('saveSuccess'))
      Object.assign(props.currentRule, data.rule)
      ruleEditMode.value = false
    } else {
      ElMessage.error(t('saveFailed') + ': ' + data.error)
    }
  } catch (e) {
    ElMessage.error(t('saveFailed'))
  } finally {
    savingRule.value = false
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
   对话框底部
   ======================================== */

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}

/* ========================================
   规则详情对话框
   ======================================== */

.rule-detail-dialog .rule-detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rule-header-section {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 16px;
}

.rule-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.rule-id-badge {
  background: var(--accent-secondary);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
}

.rule-name-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.rule-meta-row {
  display: flex;
  gap: 8px;
}

.rule-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.pattern-box {
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.pattern-code {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--accent-secondary);
}

.logic-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
}

.recommendation-box {
  background: rgba(0, 184, 148, 0.05);
  border: 1px solid rgba(0, 184, 148, 0.15);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.recommendation-code {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-primary);
  white-space: pre-wrap;
  margin: 0;
}

.rule-status-section {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.status-label {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 规则编辑模式样式 */
.edit-mode-bar {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0;
  margin-bottom: 8px;
}

.rule-name-input {
  flex: 1;
}

.rule-name-input :deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
}

.edit-input :deep(.el-textarea__inner) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
}

/* ========================================
   暗色模式
   ======================================== */

.dark .rule-header-section {
  background: rgba(13, 17, 23, 0.6);
}

.dark .rule-section {
  background: rgba(13, 17, 23, 0.4);
}

.dark .pattern-box {
  background: rgba(13, 17, 23, 0.6);
}

.dark .pattern-code {
  color: #58a6ff;
}

.dark .recommendation-box {
  background: rgba(0, 184, 148, 0.1);
}

.dark .rule-status-section {
  background: rgba(13, 17, 23, 0.6);
}
</style>

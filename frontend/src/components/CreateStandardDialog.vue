<template>
  <el-dialog
    v-model="visible"
    :title="t('complianceStandardCreate')"
    width="600px"
    append-to-body
    draggable
    align-center
    class="compliance-dialog"
  >
    <el-form :model="standardForm" label-width="100px" size="default" class="config-form">
      <el-form-item :label="t('complianceStandardName')">
        <el-input v-model="standardForm.name" />
      </el-form-item>
      <el-form-item :label="t('complianceStandardVersion')">
        <el-input v-model="standardForm.version" />
      </el-form-item>
      <el-form-item :label="t('complianceStandardDesc')">
        <el-input v-model="standardForm.description" />
      </el-form-item>
      <el-form-item :label="t('complianceStandardContent')">
        <el-input
          v-model="standardForm.content"
          type="textarea"
          :rows="10"
          :placeholder="t('complianceStandardContent')"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <button class="nav-action-btn secondary" @click="visible = false">
          {{ t('actionCancel') }}
        </button>
        <button class="nav-action-btn deploy-btn" @click="createStandard" :disabled="creatingStandard">
          <el-icon v-if="creatingStandard" class="is-loading"><Loading /></el-icon>
          {{ t('complianceStandardCreate') }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { createStandard as createStandardApi } from '@/api'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'created'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const standardForm = reactive({
  name: '',
  version: '1.0',
  description: '',
  content: ''
})

const creatingStandard = ref(false)

// 打开时重置表单
watch(() => props.modelValue, (val) => {
  if (val) {
    standardForm.name = ''
    standardForm.version = '1.0'
    standardForm.description = ''
    standardForm.content = ''
  }
})

// 创建标准文档
const createStandard = async () => {
  if (!standardForm.name || !standardForm.content) {
    ElMessage.warning(t('fieldRequired'))
    return
  }

  creatingStandard.value = true
  try {
    await createStandardApi(standardForm)
    ElMessage.success(t('complianceStandardCreate') + ' ' + t('success'))
    visible.value = false
    emit('created')
  } catch (e) {
    ElMessage.error(t('saveFailed'))
  } finally {
    creatingStandard.value = false
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

/* ========================================
   暗色模式
   ======================================== */

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
</style>

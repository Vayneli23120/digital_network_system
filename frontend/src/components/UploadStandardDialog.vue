<template>
  <el-dialog
    v-model="visible"
    :title="t('complianceStandardUpload')"
    width="500px"
    append-to-body
    draggable
    align-center
    class="compliance-dialog"
  >
    <el-upload
      ref="standardUploadRef"
      :auto-upload="false"
      :limit="1"
      :on-change="handleStandardFileChange"
      accept=".txt,.pdf,.md,.doc,.docx"
      drag
      class="config-upload"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        {{ t('complianceUploadConfigHint') }}
      </div>
    </el-upload>

    <template #footer>
      <div class="dialog-footer">
        <button class="nav-action-btn secondary" @click="visible = false">
          {{ t('actionCancel') }}
        </button>
        <button class="nav-action-btn deploy-btn" @click="uploadStandardDocument" :disabled="uploadingStandard">
          <el-icon v-if="uploadingStandard" class="is-loading"><Loading /></el-icon>
          {{ t('complianceStandardUpload') }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { uploadStandardDocument as uploadStandardDocumentApi } from '@/api'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'uploaded'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const standardUploadRef = ref(null)
const standardFile = ref(null)
const uploadingStandard = ref(false)

// 标准文档文件处理
const handleStandardFileChange = (file) => {
  standardFile.value = file.raw
}

// 上传标准文档
const uploadStandardDocument = async () => {
  if (!standardFile.value) {
    ElMessage.warning(t('selectFile'))
    return
  }

  uploadingStandard.value = true
  try {
    const formData = new FormData()
    formData.append('file', standardFile.value)

    await uploadStandardDocumentApi(formData)
    ElMessage.success(t('complianceStandardUpload') + ' ' + t('success'))
    visible.value = false
    emit('uploaded')
  } catch (e) {
    ElMessage.error(t('uploadFailed'))
  } finally {
    uploadingStandard.value = false
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
   上传区域
   ======================================== */

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

/* ========================================
   对话框底部
   ======================================== */

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}

/* ========================================
   暗色模式
   ======================================== */

.dark .config-upload :deep(.el-upload-dragger) {
  background: var(--bg-tertiary);
}
</style>

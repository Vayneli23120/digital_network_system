<template>
  <el-dialog
    v-model="visible"
    :title="t('deployPreviewDialog')"
    width="90%"
    top="5vh"
    destroy-on-close
    align-center
  >
    <el-skeleton v-if="previewLoading" :rows="10" animated />

    <div v-else class="preview-content">
      <!-- 影响分析摘要 -->
      <div class="impact-summary">
        <div class="impact-header">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ t('deployImpactAnalysis') }}</span>
        </div>
        <div class="impact-stats">
          <div class="impact-item">
            <span class="impact-label">{{ t('diffTotalChanges') }}</span>
            <span class="impact-value">{{ impactAnalysis.totalChanges }}</span>
          </div>
          <div class="impact-item">
            <span class="impact-label">{{ t('diffAffectedServices') }}</span>
            <span class="impact-value">
              {{ impactAnalysis.affectedServices.length > 0
                ? impactAnalysis.affectedServices.join(', ')
                : t('diffNoServices') }}
            </span>
          </div>
          <div class="impact-item">
            <span class="impact-label">{{ t('diffEstimatedDowntime') }}</span>
            <span class="impact-value">{{ impactAnalysis.estimatedDowntime }}s</span>
          </div>
          <div class="impact-item">
            <span class="impact-label">{{ t('diffRiskLevel') }}</span>
            <el-tag :type="getRiskLevelType(impactAnalysis.riskLevel)" size="large">
              {{ getRiskLevelText(impactAnalysis.riskLevel) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 设备选择 -->
      <div class="device-selector">
        <span class="selector-label">{{ t('diffSelectDevice') }}:</span>
        <el-select v-model="selectedPreviewDevice" style="width: 300px">
          <el-option
            v-for="result in previewResults"
            :key="result.device_id"
            :label="`${result.device_name} (${result.device_ip})`"
            :value="result"
          />
        </el-select>
      </div>

      <!-- 设备差异 -->
      <div v-if="selectedPreviewDevice" class="device-diff">
        <div class="diff-device-header">
          <div class="device-info">
            <h4>{{ selectedPreviewDevice.device_name }}</h4>
            <span class="device-ip">{{ selectedPreviewDevice.device_ip }}</span>
          </div>
          <el-tag
            :type="getRiskLevelType(selectedPreviewDevice.impact?.risk_level)"
            size="small"
          >
            {{ getRiskLevelText(selectedPreviewDevice.impact?.risk_level) }}
          </el-tag>
        </div>

        <DiffViewer
          v-if="selectedPreviewDevice.diff"
          :old-config="selectedPreviewDevice.old_config || ''"
          :new-config="selectedPreviewDevice.new_config || ''"
          :diff-data="selectedPreviewDevice.diff"
          :is-dark="isDark"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">
          {{ t('actionClose') }}
        </el-button>
        <el-button type="success" @click="emit('deploy')">
          <el-icon><Upload /></el-icon>
          {{ t('deployStart') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { WarningFilled, Upload } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { getRiskLevelType } from '@/utils/deploy.js'
import DiffViewer from '@/components/DiffViewer.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  previewLoading: { type: Boolean, default: false },
  previewResults: { type: Array, default: () => [] },
  impactAnalysis: { type: Object, default: () => ({}) },
  isDark: { type: Boolean, default: false }
})

const selectedPreviewDevice = defineModel('selectedPreviewDevice', { type: Object, default: null })

const emit = defineEmits(['update:modelValue', 'deploy'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const { t } = useI18n()

// 风险等级文本（依赖 i18n，保留在组件内）
const getRiskLevelText = (level) => {
  const texts = {
    low: t('diffRiskLow'),
    medium: t('diffRiskMedium'),
    high: t('diffRiskHigh')
  }
  return texts[level] || level
}
</script>

<style scoped>
.preview-content {
  max-height: 70vh;
  overflow-y: auto;
}

.impact-summary {
  background: var(--bg-hover);
  border-radius: var(--radius-lg);
  padding: var(--gap-lg);
  margin-bottom: var(--gap-lg);
  border: 1px solid var(--border-default);
}

.impact-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--gap-lg);
}

.impact-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--gap-lg);
}

.impact-item {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.impact-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.impact-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.device-selector {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
  padding: var(--gap-lg);
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.selector-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.device-diff {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.diff-device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--gap-md);
  background: var(--bg-hover);
  border-bottom: 1px solid var(--border-default);
}

.diff-device-header .device-info h4 {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
}

.diff-device-header .device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 设备信息（拷贝自父视图，父 device-card 仍保留自身定义） */
.device-info {
  display: flex;
  align-items: flex-start;
  gap: var(--gap-sm);
}

.device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}
</style>

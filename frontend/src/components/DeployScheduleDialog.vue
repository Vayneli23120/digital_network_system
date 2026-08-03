<template>
  <el-dialog
    v-model="visible"
    :title="t('deployScheduleDialog')"
    width="600px"
    align-center
  >
    <div class="schedule-content">
      <p class="schedule-desc">{{ t('deployScheduleDesc') }}</p>

      <el-form label-position="top">
        <el-form-item :label="t('deploySelectWindow')">
          <el-radio-group v-model="selectedWindow" class="window-options">
            <el-radio-button
              v-for="window in maintenanceWindows"
              :key="window.id"
              :label="window.id"
              :disabled="!window.available"
              class="window-option"
            >
              <div class="window-label">{{ getWindowLabel(window) }}</div>
              <div class="window-time">{{ window.start_time }} - {{ window.end_time }}</div>
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <div v-if="isScheduled" class="schedule-confirmation">
        <el-alert
          :title="t('deployScheduledConfirm', { time: scheduledTime })"
          type="success"
          :closable="false"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">
          {{ t('actionCancel') }}
        </el-button>
        <el-button type="primary" @click="emit('schedule')">
          {{ t('deployConfirmSchedule') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  maintenanceWindows: { type: Array, default: () => [] },
  isScheduled: { type: Boolean, default: false },
  scheduledTime: { type: String, default: null }
})

const selectedWindow = defineModel('selectedWindow', { default: null })

const emit = defineEmits(['update:modelValue', 'schedule'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const { t } = useI18n()

// 维护窗口标签生成（依赖 i18n，保留在组件内）
const getWindowLabel = (window) => {
  const dateStr = window.date ? window.date.slice(5) : ''  // 取 MM-DD
  const periodLabels = {
    morning: t('deployWindowMorning'),
    afternoon: t('deployWindowAfternoon'),
    evening: t('deployWindowEvening')
  }
  const periodText = periodLabels[window.period] || window.period
  return `${dateStr} ${periodText} (${window.start_time}-${window.end_time})`
}
</script>

<style scoped>
.schedule-content {
  padding: var(--gap-md) 0;
}

.schedule-desc {
  margin-bottom: var(--gap-lg);
  color: var(--text-secondary);
  font-size: 14px;
}

.window-options {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  width: 100%;
}

.window-option {
  width: 100%;
}

.window-option :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: var(--gap-md);
}

.window-label {
  font-weight: 500;
  font-size: 14px;
  color: var(--text-primary);
}

.window-time {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: var(--gap-xs);
}

.schedule-confirmation {
  margin-top: var(--gap-lg);
}

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}
</style>

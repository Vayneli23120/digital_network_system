<!-- Monitor3D 绑定设备对话框（item 946 切片 6）
从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
deviceId 经 defineModel 双向绑定父的 bindDeviceId，candidates/submitting 为 prop，
Cancel/Confirm 转发给父（父持有 pendingPlacement 并执行 API + rebuildScene）。 -->
<template>
  <el-dialog v-model="visible" :title="t('bindDeviceTitle')" width="400px">
    <el-select v-model="deviceId" :placeholder="t('monitorScreenSelectDevice')" filterable style="width:100%" popper-class="dark-select-popper">
      <el-option v-for="d in candidates" :key="d.id"
                 :label="`${d.name} (${d.ip || ''})`" :value="d.id" />
    </el-select>
    <template #footer>
      <el-button @click="emit('cancel')">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" :loading="submitting" @click="emit('confirm')">{{ t('actionConfirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  candidates: { type: Array, default: () => [] },
  submitting: { type: Boolean, default: false }
})

const deviceId = defineModel('deviceId', { default: null })

const emit = defineEmits(['update:modelValue', 'update:deviceId', 'cancel', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const { t } = useI18n()
</script>

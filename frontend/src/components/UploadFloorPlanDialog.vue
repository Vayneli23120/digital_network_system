<!-- Monitor3D 上传底图对话框（item 946 切片 6）
从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
表单状态留在父（planName 经 defineModel 双向绑定，fileName/uploading 为 prop），
选图由组件转发 file-change，Upload 由父 confirm 接管。 -->
<template>
  <el-dialog v-model="visible" :title="t('uploadFloorPlan')" width="400px">
    <el-form>
      <el-form-item :label="t('monitorScreenPlanName')">
        <el-input v-model="planName" :placeholder="t('monitorScreenPlanNamePlaceholder')" />
      </el-form-item>
      <el-form-item :label="t('monitorScreenPlanImage')">
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          accept="image/*"
          :on-change="handleFileChange"
        >
          <el-button type="primary">{{ t('monitorScreenSelectImage') }}</el-button>
          <template #tip>
            <div class="upload-tip">{{ fileName || t('monitorScreenSelectImage') }}</div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="emit('confirm')" :loading="uploading">
        {{ t('actionUpload') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  fileName: { type: String, default: '' },
  uploading: { type: Boolean, default: false }
})

const planName = defineModel('planName', { default: '' })

const emit = defineEmits(['update:modelValue', 'update:planName', 'file-change', 'confirm'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const { t } = useI18n()

const handleFileChange = (file) => {
  emit('file-change', file)
}
</script>

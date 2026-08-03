<template>
  <el-dialog
    v-model="visible"
    :title="t('deployVariableDialog')"
    width="800px"
    align-center
    draggable
  >
    <el-table :data="allVariables" style="width: 100%" stripe>
      <el-table-column prop="key" :label="t('deployVariableName')" width="200" />
      <el-table-column prop="description" :label="t('deployDescription')" />
      <el-table-column prop="example" :label="t('deployExampleValue')" width="200" />
    </el-table>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  allVariables: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const { t } = useI18n()
</script>

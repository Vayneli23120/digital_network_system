<template>
  <div class="permission-matrix">
    <!-- 顶部统计 -->
    <div class="header-bar">
      <span>{{ t('permissionSelected') }}: <strong>{{ selectedIds.length }}</strong> / {{ permissions.length }}</span>
      <div class="quick-actions">
        <el-button text size="small" @click="selectAllPerms">{{ t('selectAll') }}</el-button>
        <el-button text size="small" @click="clearAllPerms">{{ t('clearAll') }}</el-button>
      </div>
    </div>

    <!-- 权限表格 - DNAC风格 -->
    <div class="perm-table-wrapper">
      <table class="perm-table">
        <thead>
          <tr>
            <th class="th-module">{{ t('permissionModule') }}</th>
            <th class="th-check">
              <el-checkbox
                :model-value="allSelected"
                :indeterminate="partialSelected"
                @change="toggleAll"
              />
            </th>
            <th class="th-perm">{{ t('permissionPermission') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="resource in resourceGroups" :key="resource.name">
            <td class="td-module">
              <div class="module-info">
                <span class="module-label">{{ resourceLabels[resource.name] || resource.name }}</span>
                <span class="module-count">{{ resource.perms.length }}</span>
              </div>
            </td>
            <td class="td-check">
              <el-checkbox
                :model-value="resource.selected"
                :indeterminate="resource.partial"
                @change="(val) => toggleResource(resource, val)"
              />
            </td>
            <td class="td-perm">
              <div class="perm-tags">
                <el-checkbox-group v-model="selectedIds" @change="handleChange">
                  <el-checkbox
                    v-for="perm in resource.perms"
                    :key="perm.id"
                    :label="perm.id"
                    size="small"
                    class="perm-check"
                  >
                    <span class="perm-label">{{ perm.action }}</span>
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  permissions: {
    type: Array,
    default: () => []
  },
  resourceLabels: {
    type: Object,
    default: () => {}
  },
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const selectedIds = ref([...props.modelValue])

watch(() => props.modelValue, (val) => {
  selectedIds.value = [...val]
})

// 按模块分组
const resourceGroups = computed(() => {
  const groups = {}

  for (const perm of props.permissions) {
    if (!groups[perm.resource]) {
      groups[perm.resource] = {
        name: perm.resource,
        perms: []
      }
    }
    groups[perm.resource].perms.push(perm)
  }

  // 排序
  const sorted = Object.keys(groups).sort((a, b) => {
    if (a === 'admin') return -1
    if (b === 'admin') return 1
    const labelA = props.resourceLabels[a] || a
    const labelB = props.resourceLabels[b] || b
    return labelA.localeCompare(labelB, 'zh-CN')
  })

  return sorted.map(name => {
    const group = groups[name]
    const ids = group.perms.map(p => p.id)
    const selectedCount = ids.filter(id => selectedIds.value.includes(id)).length

    return {
      ...group,
      ids,
      selected: selectedCount === ids.length,
      partial: selectedCount > 0 && selectedCount < ids.length
    }
  })
})

// 全选状态
const allSelected = computed(() => {
  return props.permissions.length > 0 &&
    props.permissions.every(p => selectedIds.value.includes(p.id))
})

const partialSelected = computed(() => {
  const count = props.permissions.filter(p => selectedIds.value.includes(p.id)).length
  return count > 0 && count < props.permissions.length
})

// 操作
const toggleAll = (val) => {
  if (val) {
    selectedIds.value = props.permissions.map(p => p.id)
  } else {
    selectedIds.value = []
  }
  emit('update:modelValue', selectedIds.value)
}

const toggleResource = (resource, val) => {
  if (val) {
    const newIds = new Set(selectedIds.value)
    for (const id of resource.ids) {
      newIds.add(id)
    }
    selectedIds.value = Array.from(newIds)
  } else {
    selectedIds.value = selectedIds.value.filter(id => !resource.ids.includes(id))
  }
  emit('update:modelValue', selectedIds.value)
}

const handleChange = (val) => {
  emit('update:modelValue', val)
}

const selectAllPerms = () => {
  selectedIds.value = props.permissions.map(p => p.id)
  emit('update:modelValue', selectedIds.value)
}

const clearAllPerms = () => {
  selectedIds.value = []
  emit('update:modelValue', selectedIds.value)
}
</script>

<style scoped>
.permission-matrix {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  overflow: hidden;
}

/* 顶部条 */
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.header-bar strong {
  color: var(--el-color-primary);
  font-weight: 600;
}

.quick-actions {
  display: flex;
  gap: 4px;
}

/* 表格 */
.perm-table-wrapper {
  max-height: 360px;
  overflow-y: auto;
}

.perm-table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--el-fill-color-lighter);
}

thead th {
  padding: 8px 12px;
  font-weight: 600;
  font-size: 13px;
  color: var(--el-text-color-primary);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.th-module {
  width: 120px;
  text-align: left;
}

.th-check {
  width: 40px;
  text-align: center;
}

.th-perm {
  text-align: left;
}

tbody tr {
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

tbody tr:last-child {
  border-bottom: none;
}

tbody tr:hover {
  background: var(--el-fill-color-light);
}

.td-module {
  padding: 10px 12px;
  vertical-align: middle;
}

.module-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.module-label {
  font-weight: 500;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.module-count {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color);
  padding: 1px 5px;
  border-radius: 3px;
}

.td-check {
  padding: 10px 8px;
  text-align: center;
  vertical-align: middle;
}

.td-perm {
  padding: 8px 12px;
  vertical-align: middle;
}

.perm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.perm-tags .el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.perm-check {
  margin-right: 0 !important;
  margin-left: 0 !important;
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  height: 28px;
}

.perm-check .el-checkbox__input {
  display: inline-flex;
  align-items: center;
}

.perm-check .el-checkbox__label {
  display: inline-flex;
  align-items: center;
  padding-left: 8px;
}

.perm-check:hover {
  background: var(--el-fill-color);
}

.perm-check.is-checked {
  background: var(--el-color-primary-light-9);
}

.perm-check.is-checked .el-checkbox__label {
  color: var(--el-color-primary);
}

.perm-label {
  font-size: 13px;
  color: var(--el-text-color-primary);
}

/* 滚动条 */
.perm-table-wrapper::-webkit-scrollbar {
  width: 4px;
}

.perm-table-wrapper::-webkit-scrollbar-thumb {
  background: var(--el-border-color-lighter);
  border-radius: 2px;
}

/* 响应式 */
@media (max-width: 600px) {
  .th-module,
  .td-module {
    width: 80px;
  }

  .module-label {
    font-size: 13px;
  }

  .perm-tags {
    gap: 4px;
  }
}
</style>
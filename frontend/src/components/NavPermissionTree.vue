<template>
  <div class="nav-permission-tree">
    <div class="npt-group" v-for="group in groups" :key="group.resource">
      <label class="npt-group-header">
        <el-checkbox
          :model-value="group.allSelected"
          :indeterminate="group.partialSelected"
          @change="(val) => toggleGroup(group, val)"
        />
        <span class="npt-group-label">{{ getLabel(group.resource) }}</span>
        <span class="npt-count">{{ group.selectedCount }}/{{ group.permissions.length }}</span>
      </label>
      <div class="npt-children">
        <label
          v-for="perm in group.permissions"
          :key="perm.id"
          class="npt-child"
        >
          <el-checkbox
            :model-value="selectedIds.has(perm.id)"
            @change="() => togglePermission(perm.id)"
          />
          <span class="npt-child-label">{{ getActionLabel(perm.action) || perm.action }}</span>
        </label>
      </div>
    </div>
    <div v-if="sortedNavPerms.length === 0" class="npt-empty">
      {{ t('navPermEmpty') || '暂无可用的导航权限' }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  allPermissions: { type: Array, default: () => [] },
  resourceLabels: { type: Object, default: () => ({}) },
  actionLabels: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue'])

// Internal selected set (works with IDs)
const selectedIds = computed(() => new Set(props.modelValue))

// Filter to nav_* permissions only
const sortedNavPerms = computed(() => {
  return props.allPermissions
    .filter(p => p.resource && p.resource.startsWith('nav_'))
    .sort((a, b) => a.resource.localeCompare(b.resource) || a.action.localeCompare(b.action))
})

// Group by resource
const groups = computed(() => {
  const map = {}
  for (const perm of sortedNavPerms.value) {
    if (!map[perm.resource]) {
      map[perm.resource] = { resource: perm.resource, permissions: [] }
    }
    map[perm.resource].permissions.push(perm)
  }
  const result = Object.values(map)
  const selected = selectedIds.value
  for (const group of result) {
    const perms = group.permissions
    let count = 0
    for (const perm of perms) {
      if (selected.has(perm.id)) count++
    }
    group.allSelected = count === perms.length
    group.partialSelected = count > 0 && count < perms.length
    group.selectedCount = count
  }
  return result
})

function getLabel(resource) {
  return props.resourceLabels[resource] || resource
}

function getActionLabel(action) {
  return props.actionLabels[action] || action
}

function toggleGroup(group, val) {
  const selected = new Set(props.modelValue)
  for (const perm of group.permissions) {
    if (val) {
      selected.add(perm.id)
    } else {
      selected.delete(perm.id)
    }
  }
  emit('update:modelValue', Array.from(selected))
}

function togglePermission(id) {
  const selected = new Set(props.modelValue)
  if (selected.has(id)) {
    selected.delete(id)
  } else {
    selected.add(id)
  }
  emit('update:modelValue', Array.from(selected))
}
</script>

<style scoped>
.nav-permission-tree {
  border: 1px solid #e8ecf4;
  border-radius: 8px;
  padding: 16px;
  background: #fafcff;
}
.npt-group {
  margin-bottom: 12px;
}
.npt-group:last-child {
  margin-bottom: 0;
}
.npt-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #f0f4ff;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
}
.npt-group-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  flex: 1;
}
.npt-count {
  font-size: 11px;
  color: #909399;
  background: #fff;
  padding: 1px 6px;
  border-radius: 8px;
}
.npt-children {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 4px;
  padding: 6px 0 4px 34px;
}
.npt-child {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.npt-child:hover {
  background: #f0f5ff;
}
.npt-child-label {
  color: #475569;
}
.npt-empty {
  color: #909399;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}
</style>

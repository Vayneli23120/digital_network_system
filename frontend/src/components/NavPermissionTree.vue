<template>
  <div class="nav-permission-tree">
    <div
      class="npt-group"
      v-for="group in groups"
      :key="group.resource"
      role="group"
      :aria-labelledby="`npt-group-${group.resource}`"
    >
      <div class="npt-group-header">
        <el-checkbox
          :model-value="group.allSelected"
          :indeterminate="group.partialSelected"
          :aria-label="getLabel(group.resource)"
          @change="(val) => toggleGroup(group, val)"
        >
          <span :id="`npt-group-${group.resource}`" class="npt-group-label">
            {{ getLabel(group.resource) }}
          </span>
        </el-checkbox>
        <span class="npt-count">{{ group.selectedCount }}/{{ group.permissions.length }}</span>
      </div>
      <div class="npt-children">
        <el-checkbox
          v-for="perm in group.permissions"
          :key="perm.id"
          class="npt-child"
          :model-value="selectedIds.has(perm.id)"
          @change="() => togglePermission(perm.id)"
        >
          <span class="npt-child-label">{{ getPermLabel(perm) }}</span>
        </el-checkbox>
      </div>
    </div>
    <div v-if="sortedNavPerms.length === 0" class="npt-empty">
      {{ t('navPermEmpty') }}
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
  // Display names keyed by full permission name (nav_config:deploy -> 配置部署).
  // Nav actions are page names and collide with functional actions, so they
  // cannot share the action label namespace.
  navLabels: { type: Object, default: () => ({}) },
  // Group order (top tab order) and item order, as returned by the backend.
  // Falls back to alphabetical when not provided.
  navResourceOrder: { type: Array, default: () => [] },
  navOrder: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

// Internal selected set (works with IDs)
const selectedIds = computed(() => new Set(props.modelValue))

// Rank helper: known entries keep the backend-defined order, unknown ones go last
const rankIn = (list, key) => {
  const idx = list.indexOf(key)
  return idx === -1 ? Number.MAX_SAFE_INTEGER : idx
}

// Filter to nav_* permissions only (defensive: the parent already passes a
// pre-filtered list) and order them the way the menu itself is ordered
const sortedNavPerms = computed(() => {
  const resourceOrder = props.navResourceOrder
  const itemOrder = props.navOrder
  return props.allPermissions
    .filter(p => typeof p?.resource === 'string' && p.resource.startsWith('nav_'))
    .slice()
    .sort((a, b) => {
      const ra = rankIn(resourceOrder, a.resource)
      const rb = rankIn(resourceOrder, b.resource)
      if (ra !== rb) return ra - rb
      if (a.resource !== b.resource) return a.resource.localeCompare(b.resource)
      const ia = rankIn(itemOrder, a.name)
      const ib = rankIn(itemOrder, b.name)
      if (ia !== ib) return ia - ib
      return (a.action || '').localeCompare(b.action || '')
    })
})

// Group by resource (sortedNavPerms is already ordered, so groups follow menu order)
const groups = computed(() => {
  const map = new Map()
  for (const perm of sortedNavPerms.value) {
    if (!map.has(perm.resource)) {
      map.set(perm.resource, { resource: perm.resource, permissions: [] })
    }
    map.get(perm.resource).permissions.push(perm)
  }
  const selected = selectedIds.value
  const result = Array.from(map.values())
  for (const group of result) {
    const perms = group.permissions
    let count = 0
    for (const perm of perms) {
      if (selected.has(perm.id)) count++
    }
    group.allSelected = count > 0 && count === perms.length
    group.partialSelected = count > 0 && count < perms.length
    group.selectedCount = count
  }
  return result
})

function getLabel(resource) {
  return props.resourceLabels[resource] || resource
}

function getPermLabel(perm) {
  return props.navLabels[perm.name]
    || props.actionLabels[perm.action]
    || perm.description
    || perm.action
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
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  background: var(--el-fill-color-lighter);
  width: 100%;
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
  background: var(--el-fill-color);
  border-radius: 6px;
  user-select: none;
}
.npt-group-header :deep(.el-checkbox) {
  flex: 1;
  margin-right: 0;
  height: auto;
}
.npt-group-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.npt-count {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  background: var(--el-bg-color);
  padding: 1px 6px;
  border-radius: 8px;
}
.npt-children {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 4px;
  padding: 6px 0 4px 24px;
}
.npt-child {
  margin-right: 0;
  padding: 4px 8px;
  border-radius: 4px;
  height: auto;
}
.npt-child:hover {
  background: var(--el-fill-color-light);
}
.npt-child-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.npt-empty {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  text-align: center;
  padding: 20px;
}
</style>

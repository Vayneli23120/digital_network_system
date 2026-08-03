<!-- Monitor3D 拐点编辑对话框（item 946 切片 6）
从 frontend/src/views/Monitor3D.vue 拆分，4 个近克隆对话框（数据链路/主干光缆/分支光缆/TopoEdge）
参数化为单一组件，行为与原实现完全一致。waypoints 通过 defineModel 双向绑定父的 editingXWaypoints，
增删在组件内直接改共享响应式数组，save 由父接管。 -->
<template>
  <el-dialog v-model="visible" :title="title" width="500px">
    <p class="waypoint-hint">{{ t('waypointHint') }}</p>
    <div class="waypoint-list">
      <div v-for="(wp, idx) in waypoints" :key="wp._uid" class="waypoint-item">
        <span class="waypoint-index">{{ idx + 1 }}</span>
        <el-input-number v-model="wp.x" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointX')" />
        <el-input-number v-model="wp.y" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointY')" />
        <button class="icon-btn danger" :title="t('actionDelete')" @click="removeWaypoint(idx)">
          <el-icon><Delete /></el-icon>
        </button>
      </div>
      <div v-if="waypoints.length === 0" class="no-data">
        {{ t('noWaypoints') }}
      </div>
    </div>
    <el-button type="primary" size="small" @click="addWaypoint">
      <el-icon><Plus /></el-icon>
      {{ t('addWaypoint') }}
    </el-button>
    <template #footer>
      <el-button @click="visible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="emit('save')">{{ t('actionConfirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { stampUid } from '@/utils/uid.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' }
})

const waypoints = defineModel('waypoints', { default: () => [] })

const emit = defineEmits(['update:modelValue', 'save'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const { t } = useI18n()

const addWaypoint = () => {
  waypoints.value.push(stampUid({ x: 50, y: 50 }))
}

const removeWaypoint = (idx) => {
  waypoints.value.splice(idx, 1)
}
</script>

<style scoped>
/* 拐点编辑样式（从 Monitor3D.vue 逐字拷贝） */
.waypoint-hint {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 12px;
}

.waypoint-list {
  max-height: 200px;
  overflow-y: auto;
}

.waypoint-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  margin-bottom: 4px;
}

.waypoint-index {
  color: #22d3ee;
  font-size: 12px;
  font-weight: 500;
  min-width: 20px;
}

.waypoint-item .el-input-number {
  width: 80px;
}

.no-data {
  color: #6b7280;
  font-size: 12px;
  text-align: center;
  padding: 12px;
}

/* 图标按钮（从 Monitor3D.vue 逐字拷贝，对话框 teleport 到 body，父 scoped 够不到） */
.icon-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 34, 48, 0.6);
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 4px;
  color: #22d3ee;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
}

.icon-btn:hover {
  background: rgba(34, 211, 238, 0.2);
  border-color: rgba(34, 211, 238, 0.4);
  transform: scale(1.05);
}

.icon-btn.danger {
  color: #ff4d4f;
  border-color: rgba(255, 77, 79, 0.3);
}

.icon-btn.danger:hover {
  background: rgba(255, 77, 79, 0.15);
  border-color: rgba(255, 77, 79, 0.5);
}

.icon-btn .el-icon {
  font-size: 12px;
}
</style>

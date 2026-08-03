<!-- Monitor3D 画布右下角操作按钮（item 946 切片 7）
从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
纯展示组件：isEditMode/isFullscreen/discoveringNeighbors 为 prop，6 个动作转发给父
（toggleEditMode/resetView/topView/discoverNeighbors/打开上传对话框/toggleFullscreen 均耦合父 3D 场景）。 -->
<template>
  <div class="canvas-tools">
    <!-- 编辑模式状态提示 -->
    <div v-if="isEditMode" class="edit-mode-indicator">
      <el-tag type="warning" size="small">{{ t('monitorEditMode') }}</el-tag>
    </div>
    <!-- 编辑/查看模式切换 -->
    <el-button size="small" :type="isEditMode ? 'warning' : 'primary'" @click="emit('toggle-edit-mode')">
      {{ isEditMode ? t('monitorViewMode') : t('monitorEditMode') }}
    </el-button>
    <el-button size="small" @click="emit('reset-view')">{{ t('viewReset') }}</el-button>
    <el-button size="small" @click="emit('top-view')">{{ t('viewTop') }}</el-button>
    <el-button size="small" :loading="discoveringNeighbors" @click="emit('discover-neighbors')">
      {{ t('discoverNeighbors') }}
    </el-button>
    <el-button size="small" type="primary" @click="emit('upload')">
      {{ t('uploadFloorPlan') }}
    </el-button>
    <el-button size="small" :type="isFullscreen ? 'warning' : 'default'" @click="emit('toggle-fullscreen')">
      {{ isFullscreen ? t('exitFullscreen') : t('enterFullscreen') }}
    </el-button>
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'

defineProps({
  isEditMode: { type: Boolean, default: false },
  isFullscreen: { type: Boolean, default: false },
  discoveringNeighbors: { type: Boolean, default: false }
})

const emit = defineEmits(['toggle-edit-mode', 'reset-view', 'top-view', 'discover-neighbors', 'upload', 'toggle-fullscreen'])

const { t } = useI18n()
</script>

<style scoped>
/* 画布右下角工具按钮（避开侧边栏）（从 Monitor3D.vue 逐字拷贝） */
.canvas-tools {
  position: absolute;
  right: 276px;
  bottom: 16px;
  display: flex;
  gap: 8px;
  z-index: 5;
  transition: right 0.3s ease;
}

/* 编辑模式状态提示（从 Monitor3D.vue 逐字拷贝） */
.edit-mode-indicator {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  background: rgba(255, 161, 22, 0.9);
  padding: 8px 16px;
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
}
</style>

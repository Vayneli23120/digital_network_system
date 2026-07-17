<template>
  <aside class="sidebar" :class="{ collapsed, dark: darkMode }">
    <div class="sidebar-inner">
      <!-- Collapse Toggle -->
      <button class="collapse-toggle" @click="toggleCollapse">
        <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
      </button>

      <!-- Sidebar Groups -->
      <div class="sidebar-groups">
        <div v-for="group in sidebarGroups" :key="group.key" class="sg">
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            :class="['si', { active: isActive(item.path) }]"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span class="si-text" v-show="!collapsed">{{ item.text }}</span>
            <span class="si-badge" v-if="item.badge" v-show="!collapsed">{{ item.badge }}</span>
          </router-link>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Fold, Expand, DataBoard, Connection, Download, Warning, Tools, Upload, Document, Key, Aim, Box, Checked, List, Delete, Calendar, Bell, User } from '@element-plus/icons-vue'

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  },
  sidebarGroups: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['toggleCollapse'])

const route = useRoute()

const currentPath = computed(() => route.path)

// 前缀匹配激活状态：详情页时父菜单保持高亮
const isActive = (itemPath) => {
  const current = currentPath.value
  // 根路径精确匹配
  if (itemPath === '/') {
    return current === '/'
  }
  // 其他路径前缀匹配
  return current === itemPath || current.startsWith(itemPath + '/')
}

const toggleCollapse = () => {
  emit('toggleCollapse')
}
</script>

<style scoped>
/* ===== Sidebar ===== */
.sidebar {
  width: var(--layout-sidebar-w);
  /* 玻璃透明质感（呼应 3D 数字孪生工具面板） */
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(14px) saturate(150%);
  -webkit-backdrop-filter: blur(14px) saturate(150%);
  border-right: 1px solid rgba(0, 120, 212, 0.15);
  position: sticky;
  top: var(--layout-topbar-h);
  height: calc(100vh - var(--layout-topbar-h));
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.3s ease;
}

/* 暗色模式玻璃质感 */
.sidebar.dark {
  background: rgba(17, 22, 31, 0.58);
  border-right: 1px solid rgba(34, 211, 238, 0.18);
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-inner {
  padding: var(--gap-md);
}

/* Collapse Toggle */
.collapse-toggle {
  width: 100%;
  height: 36px;
  margin-bottom: var(--gap-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid rgba(0, 120, 212, 0.14);
  border-radius: var(--radius-md);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar.dark .collapse-toggle {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(34, 211, 238, 0.16);
}

.collapse-toggle:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.collapse-toggle .el-icon {
  font-size: 18px;
}

/* Sidebar Groups */
.sidebar-groups {
  display: flex;
  flex-direction: column;
  gap: var(--gap-lg);
}

.sg {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

/* Sidebar Item */
.si {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 10px 12px 10px 9px;
  border-left: 3px solid transparent;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  position: relative;
}

.si:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.si.active {
  background: var(--sidebar-active-bg);
  border-left-color: var(--sidebar-active-border);
  color: var(--sidebar-active-border);
}

/* Light mode active item */
.sidebar:not(.dark) .si.active {
  color: var(--color-gb);
}

/* Dark mode active item */
.sidebar.dark .si.active {
  color: #00b894;
}

.si .el-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.si-text {
  font-size: 14px;
  font-weight: 400;
  white-space: nowrap;
}

.si.active .si-text {
  font-weight: 500;
}

.si-badge {
  padding: 2px 8px;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: var(--accent-danger);
  border-radius: var(--radius-sm);
  margin-left: auto;
}

/* Collapsed state adjustments */
.sidebar.collapsed .sidebar-inner {
  padding: var(--gap-sm);
}

.sidebar.collapsed .collapse-toggle {
  width: 48px;
  margin: 0 auto var(--gap-md);
}

.sidebar.collapsed .si {
  justify-content: center;
  padding: 10px;
}

.sidebar.collapsed .si-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  padding: 2px 4px;
  font-size: 8px;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: var(--layout-topbar-h);
    bottom: 0;
    z-index: 1000;
    transform: translateX(0);
  }

  .sidebar.collapsed {
    transform: translateX(-100%);
  }
}
</style>
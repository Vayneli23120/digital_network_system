<template>
  <aside class="sidebar" :class="{ collapsed, dark: darkMode }">
    <div class="sidebar-inner">
      <!-- Collapse Toggle -->
      <button class="collapse-toggle" @click="toggleCollapse">
        <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
      </button>

      <!-- Sidebar Groups -->
      <div class="sidebar-groups">
        <div v-for="group in sidebarGroups" :key="group.label" class="sg">
          <div class="sg-label" v-show="!collapsed">{{ group.label }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            :class="['si', { active: currentPath === item.path }]"
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

const toggleCollapse = () => {
  emit('toggleCollapse')
}
</script>

<style scoped>
/* ===== Sidebar ===== */
.sidebar {
  width: var(--layout-sidebar-w);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-default);
  position: sticky;
  top: var(--layout-topbar-h);
  height: calc(100vh - var(--layout-topbar-h));
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-inner {
  padding: var(--gap-sm);
}

/* Collapse Toggle */
.collapse-toggle {
  width: 100%;
  height: 36px;
  margin-bottom: var(--gap-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.collapse-toggle:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
}

.collapse-toggle .el-icon {
  font-size: 16px;
}

/* Sidebar Groups */
.sidebar-groups {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.sg {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.sg-label {
  padding: 6px 12px;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Sidebar Item */
.si {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.15s;
  position: relative;
}

.si:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.si.active {
  background: var(--sidebar-active-bg);
  border-left: 2px solid var(--sidebar-active-border);
  padding-left: 10px;
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
  font-size: 16px;
  flex-shrink: 0;
}

.si-text {
  font-size: 13px;
  font-weight: 400;
  white-space: nowrap;
}

.si.active .si-text {
  font-weight: 500;
}

.si-badge {
  padding: 2px 6px;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: var(--accent-danger);
  border-radius: var(--radius-sm);
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
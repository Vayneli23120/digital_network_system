<template>
  <el-container class="layout-container">
    <!-- 移动端遮罩 -->
    <div v-if="isMobile && !collapsed" class="mobile-overlay" @click="collapsed = true" />

    <!-- 侧边栏 -->
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar" :class="{ collapsed }">
      <div class="logo">
        <el-icon><Monitor /></el-icon>
        <span v-show="!collapsed || isMobile">网络自动化</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed && !isMobile"
        :background-color="darkMode ? '#1a1a2e' : '#304156'"
        :text-color="darkMode ? '#a0a0b0' : '#bfcbd9'"
        active-text-color="#409EFF"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon>
          <template #title>仪表板</template>
        </el-menu-item>
        <el-menu-item index="/devices">
          <el-icon><Switch /></el-icon>
          <template #title>设备管理</template>
        </el-menu-item>
        <el-menu-item index="/backups">
          <el-icon><Download /></el-icon>
          <template #title>备份管理</template>
        </el-menu-item>
        <el-menu-item index="/faults">
          <el-icon><Warning /></el-icon>
          <template #title>故障管理</template>
        </el-menu-item>
        <el-menu-item index="/maintenance">
          <el-icon><Tools /></el-icon>
          <template #title>维修管理</template>
        </el-menu-item>
        <el-menu-item index="/console">
          <el-icon><Connection /></el-icon>
          <template #title>Console 配置</template>
        </el-menu-item>
        <el-menu-item index="/deploy">
          <el-icon><Upload /></el-icon>
          <template #title>配置部署</template>
        </el-menu-item>
        <el-menu-item index="/templates">
          <el-icon><Document /></el-icon>
          <template #title>配置模板</template>
        </el-menu-item>
        <el-menu-item index="/credentials">
          <el-icon><Key /></el-icon>
          <template #title>SSH 凭证</template>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <template #title>系统日志</template>
        </el-menu-item>
        <el-menu-item index="/discovery">
          <el-icon><Aim /></el-icon>
          <template #title>设备发现</template>
        </el-menu-item>
        <el-menu-item index="/spare-parts">
          <el-icon><Box /></el-icon>
          <template #title>备件管理</template>
        </el-menu-item>
        <el-menu-item index="/compliance">
          <el-icon><Checked /></el-icon>
          <template #title>配置合规</template>
        </el-menu-item>
        <el-menu-item index="/tool-logs">
          <el-icon><List /></el-icon>
          <template #title>工具日志</template>
        </el-menu-item>
        <el-menu-item index="/alert-settings">
          <el-icon><Bell /></el-icon>
          <template #title>告警通知</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="header" :class="{ dark: darkMode }">
        <div class="header-left">
          <el-button class="collapse-btn" text @click="collapsed = !collapsed">
            <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tooltip :content="darkMode ? '亮色模式' : '暗色模式'" placement="bottom">
            <el-button class="theme-btn" text @click="toggleDark">
              <el-icon><Sunny v-if="darkMode" /><Moon v-else /></el-icon>
            </el-button>
          </el-tooltip>
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" icon="User" />
              <span class="username">管理员</span>
            </span>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content" :class="{ dark: darkMode }">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Fold, Expand, Sunny, Moon } from '@element-plus/icons-vue'

const route = useRoute()
const collapsed = ref(false)
const darkMode = ref(localStorage.getItem('darkMode') === 'true')
const isMobile = ref(window.innerWidth < 768)

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '页面')

const toggleDark = () => {
  darkMode.value = !darkMode.value
  localStorage.setItem('darkMode', darkMode.value)
  if (darkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    collapsed.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  handleResize()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  overflow-x: hidden;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 64px;
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 60px;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  gap: 8px;
  white-space: nowrap;
  overflow: hidden;
}

.logo .el-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.sidebar-menu {
  border-right: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  transition: background-color 0.3s, border-color 0.3s;
}

.header.dark {
  background: var(--el-bg-color);
  border-color: var(--el-border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-btn, .theme-btn {
  font-size: 18px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.username {
  color: #606266;
}

.header.dark .username {
  color: var(--el-text-color-regular);
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
  transition: background-color 0.3s;
}

.main-content.dark {
  background: var(--el-bg-color-page);
}

/* 移动端遮罩 */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 998;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 999;
    width: 220px;
  }

  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }

  .sidebar.collapsed {
    transform: translateX(-220px);
  }

  .username {
    display: none;
  }

  .main-content {
    padding: 12px;
  }

  .header {
    padding: 0 12px;
  }
}

@media (max-width: 576px) {
  .logo span {
    font-size: 14px;
  }
}
</style>

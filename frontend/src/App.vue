<template>
  <el-config-provider :locale="locale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

const locale = ref(zhCn)
</script>

<style>
/* 字体回退到系统字体栈（不引入外部 Google Fonts CDN，避免内网/离线环境 ERR_NAME_NOT_RESOLVED） */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Geist', 'Satoshi', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
}

body {
  margin: 0;
  padding: 0;
  background: var(--bg);
}

/* Override Element Plus defaults */
.el-card {
  border-radius: var(--radius-md);
  border-color: var(--border);
}

.el-button {
  font-family: 'Geist', 'Satoshi', sans-serif;
  border-radius: var(--radius-sm);
}

.el-input__wrapper {
  border-radius: var(--radius-sm);
}

.el-table {
  font-family: 'Geist', sans-serif;
  font-size: 13px;
}

.el-table th.el-table__cell {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* Mono numbers */
.mono {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
}
</style>
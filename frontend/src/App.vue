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
/* Import DM Sans and DM Mono fonts (fallback to system fonts) */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@300;400;500&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: var(--font-body);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
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

/* Override Element Plus defaults for dense enterprise look */
.el-card {
  border-radius: var(--radius-panel);
  border-color: var(--border);
}

.el-button {
  font-family: var(--font-body);
  border-radius: var(--radius-sm);
}

.el-input__wrapper {
  border-radius: var(--radius-sm);
}

.el-table {
  font-size: 12.5px;
}

.el-table th.el-table__cell {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* Mono numbers */
.mono {
  font-family: var(--font-mono);
}
</style>
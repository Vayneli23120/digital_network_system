<template>
  <!-- B1 单独演示页：全屏深海暗流背景（临时路由 /demo/ocean-background，可随时删除） -->
  <div class="demo-page">
    <OceanBackground />

    <!-- 返回按钮（纯图标，避免硬编码文本） -->
    <button class="demo-back" aria-label="back" @click="$router.back()">
      <el-icon :size="20"><Back /></el-icon>
    </button>
  </div>
</template>

<script setup>
import { Back } from '@element-plus/icons-vue'
import OceanBackground from '@/components/OceanBackground.vue'
</script>

<style scoped>
.demo-page {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: #00010a;
}

.demo-back {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 209, 0, 0.4);
  border-radius: 50%;
  background: rgba(0, 15, 63, 0.6);
  color: #ffd100;
  cursor: pointer;
  transition: background 0.2s;
}

.demo-back:hover {
  background: rgba(10, 35, 66, 0.9);
}
</style>

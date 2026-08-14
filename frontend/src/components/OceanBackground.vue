<template>
  <!-- 深海暗流背景层（WebGL 流体模拟），铺满父容器 -->
  <canvas ref="canvasRef" class="ocean-canvas" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useOceanBackground } from '@/composables/useOceanBackground'

const canvasRef = ref(null)
const { start, stop } = useOceanBackground(canvasRef)

onMounted(start)
onBeforeUnmount(stop)
</script>

<style scoped>
.ocean-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>

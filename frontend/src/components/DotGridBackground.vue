<template>
  <!-- 点阵网格背景层（2D canvas），铺满父容器 -->
  <canvas ref="canvasRef" class="dot-grid-canvas" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useDotGrid } from '@/composables/useDotGrid'

const canvasRef = ref(null)
const { start, stop } = useDotGrid(canvasRef)

onMounted(start)
onBeforeUnmount(stop)
</script>

<style scoped>
.dot-grid-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>

<template>
  <div class="monitor3d">
    <!-- 左：3D 画布 -->
    <div ref="canvasHost" class="canvas-host"></div>

    <!-- 画布角落浮层按钮 -->
    <div class="viewport-tools">
      <el-button size="small" @click="resetView">{{ t('viewReset') }}</el-button>
      <el-button size="small" @click="topView">{{ t('viewTop') }}</el-button>
      <el-button size="small" type="primary" @click="showUploadDialog = true">
        {{ t('uploadFloorPlan') }}
      </el-button>
    </div>

    <!-- 上传底图对话框 -->
    <el-dialog v-model="showUploadDialog" :title="t('uploadFloorPlan')" width="400px">
      <el-form>
        <el-form-item :label="t('monitorScreenPlanName')">
          <el-input v-model="uploadPlanName" :placeholder="t('monitorScreenPlanNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('monitorScreenPlanImage')">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            :on-change="handleFileChange"
          >
            <el-button type="primary">{{ t('monitorScreenSelectImage') }}</el-button>
            <template #tip>
              <div class="upload-tip">{{ uploadFileName || t('monitorScreenSelectImage') }}</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="uploadFloorPlan" :loading="uploading">
          {{ t('actionUpload') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 右：操作面板 -->
    <aside class="side-panel">
      <div class="panel-header">
        <h3>{{ t('monitor3dTitle') }}</h3>
      </div>
      <div class="kpi-row">
        <div class="kpi">
          <span>{{ t('statusOnline') }}</span>
          <b class="online">{{ stats.online }}</b>
        </div>
        <div class="kpi danger">
          <span>{{ t('statusOffline') }}</span>
          <b class="offline">{{ stats.offline }}</b>
        </div>
        <div class="kpi">
          <span>{{ t('deviceTotal') }}</span>
          <b>{{ stats.total }}</b>
        </div>
      </div>
      <el-divider />

      <!-- 设备筛选 -->
      <div class="filter-section">
        <el-select v-model="filterType" :placeholder="t('filterDeviceType')" size="small" clearable>
          <el-option label="全部类型" value="" />
          <el-option label="交换机" value="switch" />
          <el-option label="核心交换机" value="core_switch" />
          <el-option label="AP" value="ap" />
        </el-select>
        <el-select v-model="filterStatus" :placeholder="t('filterDeviceStatus')" size="small" clearable style="margin-left: 8px;">
          <el-option label="全部状态" value="" />
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
        </el-select>
      </div>

      <el-divider />

      <!-- 选中设备详情 -->
      <div class="selected-box" v-if="selectedDevice">
        <h4>{{ selectedDevice.name }}</h4>
        <p><strong>IP:</strong> {{ selectedDevice.ip }}</p>
        <p><strong>{{ t('deviceType') }}:</strong> {{ selectedDevice.device_type }}</p>
        <p><strong>{{ t('deviceStatus') }}:</strong>
          <el-tag :type="selectedDevice.status === 'online' ? 'success' : 'danger'" size="small">
            {{ selectedDevice.status }}
          </el-tag>
        </p>
        <p v-if="selectedDevice.location"><strong>{{ t('deviceLocation') }}:</strong> {{ selectedDevice.location }}</p>
        <el-button type="primary" size="small" @click="goToDeviceDetail(selectedDevice.id)">
          {{ t('viewDetail') }}
        </el-button>
      </div>
      <div v-else class="hint">
        <el-icon><Pointer /></el-icon>
        <span>{{ t('clickDeviceHint') }}</span>
      </div>

      <el-divider />

      <!-- 图层控制 -->
      <div class="layer-control">
        <h4>{{ t('layerControl') }}</h4>
        <el-checkbox v-model="showLabels">{{ t('showLabels') }}</el-checkbox>
        <el-checkbox v-model="showLinks">{{ t('showLinks') }}</el-checkbox>
      </div>

      <!-- 告警列表 -->
      <el-divider />
      <div class="alert-section">
        <h4>{{ t('alertList') }}</h4>
        <div class="alert-list">
          <div
            v-for="alert in offlineDevices"
            :key="alert.id"
            class="alert-item"
            @click="focusDevice(alert)"
          >
            <el-icon class="alert-icon"><Warning /></el-icon>
            <span class="alert-name">{{ alert.name }}</span>
            <span class="alert-ip">{{ alert.ip }}</span>
          </div>
          <div v-if="offlineDevices.length === 0" class="no-alert">
            {{ t('noOfflineDevices') }}
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { ElMessage } from 'element-plus'
import { Pointer, Warning } from '@element-plus/icons-vue'
import axios from 'axios'
import { t } from '@/locales'

const router = useRouter()
const canvasHost = ref(null)
const selectedDevice = ref(null)
const filterType = ref('')
const filterStatus = ref('')
const showLabels = ref(true)
const showLinks = ref(true)

// 上传底图相关
const showUploadDialog = ref(false)
const uploadPlanName = ref('')
const uploadFile = ref(null)
const uploadFileName = ref('')
const uploading = ref(false)

// 设备数据
const devices = ref([])
const nodes = ref([])
const links = ref([])
const floorPlans = ref([])
const currentPlan = ref(null)

// 统计数据
const stats = computed(() => {
  const filtered = filteredDevices.value
  return {
    total: filtered.length,
    online: filtered.filter(d => d.status === 'online').length,
    offline: filtered.filter(d => d.status === 'offline').length,
  }
})

// 离线设备列表
const offlineDevices = computed(() => {
  return devices.value.filter(d => d.status === 'offline').slice(0, 10)
})

// 筛选后的设备
const filteredDevices = computed(() => {
  let result = devices.value
  if (filterType.value) {
    if (filterType.value === 'switch') {
      result = result.filter(d => ['office_switch', 'core_switch', 'server_switch', 'uce'].includes(d.device_type))
    } else {
      result = result.filter(d => d.device_type === filterType.value)
    }
  }
  if (filterStatus.value) {
    result = result.filter(d => d.status === filterStatus.value)
  }
  return result
})

// 用 shallowRef 持有 three 对象，避免 Vue 深度响应式代理
const ctx = shallowRef({
  scene: null,
  camera: null,
  renderer: null,
  labelRenderer: null,
  controls: null,
  deviceMeshes: null,
  linkLines: null,
  labels: null,
})

// 厂区真实尺寸（米）
const plan = {
  real_width_m: 1000,
  real_depth_m: 562.5,
  wall_height_m: 3
}

let raf = 0
const raycaster = new THREE.Raycaster()
const pointer = new THREE.Vector2()

// 颜色映射
const COLORS = {
  online: new THREE.Color(0x22d3ee),    // 青色
  offline: new THREE.Color(0xff4d4f),   // 红色
  maintenance: new THREE.Color(0xffa116), // 橙色
}

// 坐标转换：百分比 → 世界坐标（米）
function percentToWorld(xPercent, yPercent, elevation = 0) {
  const x = (Number(xPercent) / 100) * plan.real_width_m
  const z = (Number(yPercent) / 100) * plan.real_depth_m
  return { x, y: elevation, z }
}

// 初始化场景
function initScene() {
  const host = canvasHost.value
  const W = host.clientWidth
  const H = host.clientHeight

  // 场景
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0e16)

  // 相机
  const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 8000)
  camera.position.set(plan.real_width_m / 2, 700, plan.real_depth_m + 700)

  // WebGL 渲染器
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(W, H)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  host.appendChild(renderer.domElement)

  // CSS2D 标签渲染器
  const labelRenderer = new CSS2DRenderer()
  labelRenderer.setSize(W, H)
  labelRenderer.domElement.style.position = 'absolute'
  labelRenderer.domElement.style.top = '0'
  labelRenderer.domElement.style.pointerEvents = 'none'
  host.appendChild(labelRenderer.domElement)

  // 轨道控制
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
  controls.maxPolarAngle = Math.PI / 2.05
  controls.minDistance = 30
  controls.maxDistance = 3000

  // 灯光
  scene.add(new THREE.AmbientLight(0xffffff, 0.7))
  const dir = new THREE.DirectionalLight(0xffffff, 0.8)
  dir.position.set(100, 200, 100)
  scene.add(dir)

  // 地面网格（辅助）
  const gridHelper = new THREE.GridHelper(plan.real_width_m, 50, 0x1a2230, 0x1a2230)
  gridHelper.position.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
  scene.add(gridHelper)

  // 保存上下文
  Object.assign(ctx.value, { scene, camera, renderer, labelRenderer, controls, host })

  // 动画循环
  const animate = () => {
    raf = requestAnimationFrame(animate)
    controls.update()

    // 离线设备呼吸动画
    pulseOfflineDevices()

    renderer.render(scene, camera)
    labelRenderer.render(scene, camera)
  }
  animate()

  // 点击事件
  renderer.domElement.addEventListener('click', onCanvasClick)

  // 窗口大小变化
  window.addEventListener('resize', onResize)
}

// 窗口大小变化处理
function onResize() {
  const { camera, renderer, labelRenderer, host } = ctx.value
  if (!host) return
  const W = host.clientWidth
  const H = host.clientHeight
  camera.aspect = W / H
  camera.updateProjectionMatrix()
  renderer.setSize(W, H)
  labelRenderer.setSize(W, H)
}

// 视角复位
function resetView() {
  const { camera, controls } = ctx.value
  camera.position.set(plan.real_width_m / 2, 300, plan.real_depth_m + 200)
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
}

// 俯视图
function topView() {
  const { camera, controls } = ctx.value
  camera.position.set(plan.real_width_m / 2, 500, plan.real_depth_m / 2 + 0.1)
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
}

// 加载底图纹理
async function loadFloorPlanTexture() {
  const { scene, renderer } = ctx.value
  if (!currentPlan.value) return

  const loader = new THREE.TextureLoader()

  try {
    const tex = await loader.loadAsync(currentPlan.value.image_path)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy()

    const geo = new THREE.PlaneGeometry(plan.real_width_m, plan.real_depth_m)
    const mat = new THREE.MeshBasicMaterial({ map: tex })
    const ground = new THREE.Mesh(geo, mat)
    ground.rotation.x = -Math.PI / 2
    ground.position.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
    ground.name = 'ground'
    scene.add(ground)
  } catch (e) {
    console.error('加载底图失败:', e)
  }
}

// 构建设备 InstancedMesh
function buildDeviceInstances() {
  const { scene } = ctx.value

  // 按类型分组
  const switches = filteredDevices.value.filter(d =>
    ['office_switch', 'core_switch', 'server_switch', 'uce'].includes(d.device_type)
  )
  const aps = filteredDevices.value.filter(d => d.device_type === 'ap')
  const others = filteredDevices.value.filter(d =>
    !['office_switch', 'core_switch', 'server_switch', 'uce', 'ap'].includes(d.device_type)
  )

  const meshes = {}
  const dummy = new THREE.Object3D()

  // 交换机
  if (switches.length > 0) {
    const geo = new THREE.BoxGeometry(2, 1, 1.2)
    const mat = new THREE.MeshStandardMaterial({ metalness: 0.3, roughness: 0.6 })
    const mesh = new THREE.InstancedMesh(geo, mat, switches.length)

    switches.forEach((d, i) => {
      const node = nodes.value.find(n => n.device_id === d.id)
      if (!node) return

      const w = percentToWorld(node.x_percent, node.y_percent, 0.5)
      dummy.position.set(w.x, w.y, w.z)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)

      const c = COLORS[d.status] || COLORS.online
      mesh.setColorAt(i, c)
    })

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
    mesh.userData.devices = switches
    mesh.userData.type = 'switch'
    scene.add(mesh)
    meshes.switch = mesh
  }

  // AP
  if (aps.length > 0) {
    const geo = new THREE.BoxGeometry(1, 0.4, 1)
    const mat = new THREE.MeshStandardMaterial({ metalness: 0.3, roughness: 0.6 })
    const mesh = new THREE.InstancedMesh(geo, mat, aps.length)

    aps.forEach((d, i) => {
      const node = nodes.value.find(n => n.device_id === d.id)
      if (!node) return

      const w = percentToWorld(node.x_percent, node.y_percent, 0.2)
      dummy.position.set(w.x, w.y, w.z)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)

      const c = COLORS[d.status] || COLORS.online
      mesh.setColorAt(i, c)
    })

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
    mesh.userData.devices = aps
    mesh.userData.type = 'ap'
    scene.add(mesh)
    meshes.ap = mesh
  }

  ctx.value.deviceMeshes = meshes
}

// 构建链路
function buildLinks() {
  const { scene } = ctx.value

  const linkGroup = new THREE.Group()
  linkGroup.name = 'links'

  links.value.forEach(link => {
    const fromNode = nodes.value.find(n => n.id === link.from_node_id || n.device_id === link.from)
    const toNode = nodes.value.find(n => n.id === link.to_node_id || n.device_id === link.to)

    if (!fromNode || !toNode) return

    const a = percentToWorld(fromNode.x_percent, fromNode.y_percent, 1)
    const b = percentToWorld(toNode.x_percent, toNode.y_percent, 1)

    const points = [
      new THREE.Vector3(a.x, a.y, a.z),
      new THREE.Vector3(b.x, b.y, b.z)
    ]

    const geo = new THREE.BufferGeometry().setFromPoints(points)
    const mat = new THREE.LineBasicMaterial({
      color: link.status === 'broken' ? 0xff4d4f : 0x22d3ee,
      transparent: true,
      opacity: 0.5
    })

    const line = new THREE.Line(geo, mat)
    line.userData.link = link
    linkGroup.add(line)
  })

  scene.add(linkGroup)
  ctx.value.linkLines = linkGroup
}

// 构建设备标签
function buildLabels() {
  const { scene } = ctx.value

  const labelGroup = new THREE.Group()
  labelGroup.name = 'labels'

  // 只显示离线设备的标签（避免过多）
  offlineDevices.value.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return

    const w = percentToWorld(node.x_percent, node.y_percent, 2)

    const el = document.createElement('div')
    el.className = 'device-label offline'
    el.textContent = d.name

    const label = new CSS2DObject(el)
    label.position.set(w.x, w.y, w.z)
    labelGroup.add(label)
  })

  scene.add(labelGroup)
  ctx.value.labels = labelGroup
}

// 离线设备呼吸动画
let pulseTime = 0
function pulseOfflineDevices() {
  if (!ctx.value.deviceMeshes) return

  pulseTime += 0.05
  const pulse = Math.sin(pulseTime) * 0.3 + 0.7

  Object.values(ctx.value.deviceMeshes).forEach(mesh => {
    if (!mesh.userData.devices) return

    mesh.userData.devices.forEach((d, i) => {
      if (d.status === 'offline') {
        const c = new THREE.Color(0xff4d4f)
        c.multiplyScalar(pulse)
        mesh.setColorAt(i, c)
      }
    })

    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  })
}

// 点击拾取
function onCanvasClick(e) {
  const { camera, renderer, deviceMeshes } = ctx.value

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  const targets = Object.values(deviceMeshes || {})
  const hits = raycaster.intersectObjects(targets, false)

  if (hits.length > 0) {
    const hit = hits[0]
    const mesh = hit.object
    const device = mesh.userData.devices?.[hit.instanceId]

    if (device) {
      selectedDevice.value = device
      ElMessage.success(`${t('selected')}: ${device.name}`)
    }
  } else {
    selectedDevice.value = null
  }
}

// 聚焦到设备
function focusDevice(device) {
  const { camera, controls } = ctx.value

  const node = nodes.value.find(n => n.device_id === device.id)
  if (!node) return

  const w = percentToWorld(node.x_percent, node.y_percent, 0)

  controls.target.set(w.x, 50, w.z)
  camera.position.set(w.x + 50, 100, w.z + 50)

  selectedDevice.value = device
}

// 跳转设备详情
function goToDeviceDetail(deviceId) {
  router.push(`/devices/${deviceId}`)
}

// 文件选择
function handleFileChange(file) {
  uploadFile.value = file.raw
  uploadFileName.value = file.name
}

// 上传底图
async function uploadFloorPlan() {
  if (!uploadPlanName.value || !uploadFile.value) {
    ElMessage.warning(t('pleaseFillAllFields'))
    return
  }

  uploading.value = true

  try {
    const formData = new FormData()
    formData.append('name', uploadPlanName.value)
    formData.append('image', uploadFile.value)

    const res = await axios.post('/api/floor-plans', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    ElMessage.success(t('uploadSuccess'))

    // 重新加载数据
    await loadData()

    // 加载新底图纹理
    loadFloorPlanTexture()

    // 关闭对话框
    showUploadDialog.value = false
    uploadPlanName.value = ''
    uploadFile.value = null
    uploadFileName.value = ''

  } catch (e) {
    console.error('上传失败:', e)
    ElMessage.error(t('uploadFailed'))
  } finally {
    uploading.value = false
  }
}

// 加载数据
async function loadData() {
  try {
    // 加载平面图
    const plansRes = await axios.get('/api/floor-plans')
    floorPlans.value = plansRes.data.items || []
    if (floorPlans.value.length > 0) {
      currentPlan.value = floorPlans.value[0]
    }

    // 加载设备
    const devicesRes = await axios.get('/api/devices')
    devices.value = devicesRes.data.items || devicesRes.data || []

    // 加载节点
    if (currentPlan.value) {
      const nodesRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/nodes`)
      nodes.value = nodesRes.data.items || []

      const linksRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/links`)
      links.value = linksRes.data.items || []

      const topoRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topology`)
      if (topoRes.data.nodes) nodes.value = topoRes.data.nodes
      if (topoRes.data.links) links.value = topoRes.data.links
    }

  } catch (e) {
    console.error('加载数据失败:', e)
    ElMessage.error(t('loadDataFailed'))
  }
}

// 监听筛选变化，重建设备
watch([filterType, filterStatus], () => {
  if (ctx.value.scene) {
    // 清除旧设备
    Object.values(ctx.value.deviceMeshes || {}).forEach(mesh => {
      ctx.value.scene.remove(mesh)
      mesh.geometry?.dispose()
      mesh.material?.dispose()
    })
    // 重建
    buildDeviceInstances()
  }
})

// 监听图层控制
watch(showLinks, (val) => {
  if (ctx.value.linkLines) {
    ctx.value.linkLines.visible = val
  }
})

watch(showLabels, (val) => {
  if (ctx.value.labels) {
    ctx.value.labels.visible = val
  }
})

onMounted(async () => {
  initScene()
  await loadData()
  loadFloorPlanTexture()
  buildDeviceInstances()
  buildLinks()
  buildLabels()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', onResize)

  const { renderer, controls, host, labelRenderer, scene } = ctx.value

  // 清除事件
  renderer?.domElement?.removeEventListener('click', onCanvasClick)

  // 释放资源
  controls?.dispose()
  renderer?.dispose()

  // 清除场景
  scene?.traverse(obj => {
    obj.geometry?.dispose()
    obj.material?.dispose()
  })

  // 移除 DOM
  if (renderer?.domElement) host?.removeChild(renderer.domElement)
  if (labelRenderer?.domElement) host?.removeChild(labelRenderer.domElement)
})
</script>

<style scoped>
.monitor3d {
  display: flex;
  width: 100%;
  height: 100vh;
  background: #0a0e16;
}

.canvas-host {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.side-panel {
  width: 380px;
  flex-shrink: 0;
  padding: 16px;
  background: #11161f;
  color: #e5e7eb;
  overflow-y: auto;
  border-left: 1px solid #1f2937;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  color: #22d3ee;
}

.viewport-tools {
  position: absolute;
  left: 16px;
  bottom: 16px;
  display: flex;
  gap: 8px;
  z-index: 5;
}

.kpi-row {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.kpi {
  flex: 1;
  background: #1a2230;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.kpi span {
  font-size: 12px;
  color: #6b7280;
}

.kpi b {
  display: block;
  font-size: 24px;
  margin-top: 4px;
}

.kpi b.online {
  color: #22d3ee;
}

.kpi b.offline {
  color: #ff4d4f;
}

.filter-section {
  display: flex;
  align-items: center;
}

.selected-box {
  background: #1a2230;
  border-radius: 8px;
  padding: 12px;
}

.selected-box h4 {
  margin: 0 0 8px;
  color: #22d3ee;
}

.selected-box p {
  margin: 4px 0;
  font-size: 13px;
}

.hint {
  color: #6b7280;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.layer-control h4 {
  margin: 0 0 8px;
  font-size: 14px;
}

.alert-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
}

.alert-list {
  max-height: 200px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #1a2230;
  border-radius: 4px;
  margin-bottom: 4px;
  cursor: pointer;
}

.alert-item:hover {
  background: #243040;
}

.alert-icon {
  color: #ff4d4f;
}

.alert-name {
  color: #e5e7eb;
}

.alert-ip {
  color: #6b7280;
  font-size: 12px;
}

.no-alert {
  color: #6b7280;
  font-size: 13px;
}

/* 设备标签样式（CSS2D） */
:deep(.device-label) {
  padding: 4px 8px;
  background: rgba(26, 34, 48, 0.9);
  border-radius: 4px;
  color: #e5e7eb;
  font-size: 12px;
  white-space: nowrap;
}

:deep(.device-label.offline) {
  background: rgba(255, 77, 79, 0.9);
  color: #fff;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
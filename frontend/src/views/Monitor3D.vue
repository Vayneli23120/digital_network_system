<template>
  <div class="monitor3d" :class="{ 'fullscreen-mode': isFullscreen, 'panel-hidden': hidePanel }">
    <!-- 左：3D 画布 -->
    <div ref="canvasHost" class="canvas-host"></div>

    <!-- 画布右下角操作按钮 -->
    <div class="canvas-tools">
      <el-button size="small" @click="resetView">{{ t('viewReset') }}</el-button>
      <el-button size="small" @click="topView">{{ t('viewTop') }}</el-button>
      <el-button size="small" type="primary" @click="showUploadDialog = true">
        {{ t('uploadFloorPlan') }}
      </el-button>
      <el-button size="small" :type="isFullscreen ? 'warning' : 'default'" @click="toggleFullscreen">
        {{ isFullscreen ? t('exitFullscreen') : t('enterFullscreen') }}
      </el-button>
    </div>

    <!-- 右侧面板展开/收起按钮 -->
    <div class="panel-toggle" @click="hidePanel = !hidePanel">
      <el-icon><ArrowLeft v-if="!hidePanel" /><ArrowRight v-else /></el-icon>
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

    <!-- 右：操作面板（玻璃质感） -->
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

      <!-- 平面图切换 -->
      <div class="plan-switch" v-if="floorPlans.length > 0">
        <el-select v-model="currentPlanId" :placeholder="t('monitorScreenSelectPlan')" size="small" @change="switchPlan">
          <el-option
            v-for="plan in floorPlans"
            :key="plan.id"
            :label="plan.name"
            :value="plan.id"
          />
        </el-select>
      </div>
      <div v-else class="no-plan-hint">
        <el-button type="primary" size="small" @click="showUploadDialog = true">
          {{ t('uploadFloorPlan') }}
        </el-button>
      </div>

      <el-divider />

      <!-- 设备筛选 -->
      <div class="filter-section">
        <el-select v-model="filterType" :placeholder="t('filterDeviceType')" size="small" clearable>
          <el-option :label="t('monitorFilterAllTypes')" value="" />
          <el-option :label="t('deviceTypeSwitch')" value="switch" />
          <el-option :label="t('deviceTypeCoreSwitch')" value="core_switch" />
          <el-option :label="t('deviceTypeAP')" value="ap" />
        </el-select>
        <el-select v-model="filterStatus" :placeholder="t('filterDeviceStatus')" size="small" clearable style="margin-left: 8px;">
          <el-option :label="t('filterAllStatus')" value="" />
          <el-option :label="t('statusOnline')" value="online" />
          <el-option :label="t('statusOffline')" value="offline" />
        </el-select>
      </div>

      <el-divider />

      <!-- 选中设备详情 -->
      <div class="selected-box" v-if="selectedDevice">
        <h4>{{ selectedDevice.name }}</h4>
        <p><strong>IP:</strong> {{ selectedDevice.ip }}</p>
        <p><strong>{{ t('deviceStatus') }}:</strong>
          <el-tag :type="selectedDevice.status === 'online' ? 'success' : 'danger'" size="small">
            {{ selectedDevice.status }}
          </el-tag>
        </p>
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
        <div class="tilt-control">
          <span>{{ t('floorPlanTilt') }}:</span>
          <el-slider v-model="floorTiltAngle" :min="0" :max="90" :step="5" :show-tooltip="true" size="small" />
          <span class="tilt-value">{{ floorTiltAngle }}°</span>
        </div>
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
import { Pointer, Warning, Upload, FullScreen, Close, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import axios from 'axios'
import { t } from '@/locales'

const router = useRouter()
const canvasHost = ref(null)
const selectedDevice = ref(null)
const filterType = ref('')
const filterStatus = ref('')
const showLabels = ref(true)
const showLinks = ref(true)
const floorTiltAngle = ref(0)  // 底图倾斜角度，0=水平，90=垂直
const isFullscreen = ref(false)  // 全屏模式
const hidePanel = ref(false)  // 隐藏侧边栏

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
const currentPlanId = ref(null)

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
  controls.enablePan = true  // 允许平移
  controls.panSpeed = 1.5    // 平移速度
  controls.zoomSpeed = 1.2   // 缩放速度
  controls.enableZoom = false // 禁用默认滚轮缩放，使用自定义的
  controls.mouseButtons = {
    LEFT: THREE.MOUSE.PAN,     // 左键平移
    MIDDLE: THREE.MOUSE.DOLLY, // 中键缩放
    RIGHT: THREE.MOUSE.ROTATE  // 右键旋转
  }

  // 灯光
  scene.add(new THREE.AmbientLight(0xffffff, 0.7))
  const dir = new THREE.DirectionalLight(0xffffff, 0.8)
  dir.position.set(100, 200, 100)
  scene.add(dir)

  // 地面网格（已隐藏）
  // const gridHelper = new THREE.GridHelper(plan.real_width_m, 50, 0x1a2230, 0x1a2230)
  // gridHelper.position.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
  // scene.add(gridHelper)

  // 保存上下文
  Object.assign(ctx.value, { scene, camera, renderer, labelRenderer, controls, host })

  // 自定义滚轮缩放：以鼠标位置为中心
  renderer.domElement.addEventListener('wheel', (e) => {
    e.preventDefault()

    const { camera, controls } = ctx.value

    // 计算鼠标在场景中的位置
    const rect = renderer.domElement.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1
    const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1

    // 射线投射到地面（y=0）
    const raycasterLocal = new THREE.Raycaster()
    raycasterLocal.setFromCamera({ x: mouseX, y: mouseY }, camera)

    // 创建一个水平面用于计算交点
    const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
    const intersectPoint = new THREE.Vector3()
    raycasterLocal.ray.intersectPlane(groundPlane, intersectPoint)

    if (intersectPoint) {
      // 缩放因子
      const delta = e.deltaY > 0 ? 0.9 : 1.1
      const minDist = 30
      const maxDist = 3000

      // 当前相机到target的距离
      const currentDist = camera.position.distanceTo(controls.target)
      const newDist = Math.max(minDist, Math.min(maxDist, currentDist * (1 / delta)))

      // 以鼠标位置为中心缩放
      const direction = camera.position.clone().sub(controls.target).normalize()
      const offset = intersectPoint.clone().sub(controls.target)

      // 新的target位置（向鼠标位置移动）
      const factor = (newDist - currentDist) / currentDist
      controls.target.add(offset.multiplyScalar(factor * 0.5))

      // 新的相机位置
      camera.position.copy(controls.target).add(direction.multiplyScalar(newDist))
    }
  }, { passive: false })

  // 动画循环
  const animate = () => {
    raf = requestAnimationFrame(animate)
    controls.update()

    // 离线设备呼吸动画
    pulseOfflineDevices()

    // 根据相机距离更新标签可见性
    updateLabelVisibility()

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
  fitView()
}

// 俯视图
function topView() {
  const { camera, controls } = ctx.value
  camera.position.set(plan.real_width_m / 2, 500, plan.real_depth_m / 2 + 0.1)
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
}

// 自动框景 - 根据底图尺寸计算合适的相机距离
function fitView() {
  const { camera, controls } = ctx.value
  if (!camera) return

  const maxDim = Math.max(plan.real_width_m, plan.real_depth_m)
  // 根据FOV计算距离，让底图填满视野
  const fovRad = THREE.MathUtils.degToRad(camera.fov / 2)
  const dist = (maxDim / 2) / Math.tan(fovRad) * 1.5  // 1.5倍留边距

  camera.position.set(plan.real_width_m / 2, dist * 0.7, plan.real_depth_m / 2 + dist)
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
}

// 全屏切换
function toggleFullscreen() {
  if (!isFullscreen.value) {
    // 进入全屏
    const elem = document.querySelector('.monitor3d')
    if (elem.requestFullscreen) {
      elem.requestFullscreen()
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen()
    } else if (elem.msRequestFullscreen) {
      elem.msRequestFullscreen()
    }
    isFullscreen.value = true
  } else {
    // 退出全屏
    if (document.exitFullscreen) {
      document.exitFullscreen()
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen()
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen()
    }
    isFullscreen.value = false
  }
}

// 监听全屏变化
function onFullscreenChange() {
  isFullscreen.value = document.fullscreenElement !== null
}

// 加载底图纹理
async function loadFloorPlanTexture() {
  const { scene, renderer } = ctx.value
  if (!currentPlan.value) return

  // 清除旧底图
  const oldGround = scene?.getObjectByName('ground')
  if (oldGround) {
    scene.remove(oldGround)
    oldGround.geometry?.dispose()
    oldGround.material?.dispose()
  }

  // 转换本地路径到 HTTP URL
  const path = currentPlan.value.image_path
  const filename = path.split('/').pop()
  const imageUrl = '/photos/floor_plans/' + encodeURIComponent(filename)

  const loader = new THREE.TextureLoader()

  try {
    const tex = await loader.loadAsync(imageUrl)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy()

    const geo = new THREE.PlaneGeometry(plan.real_width_m, plan.real_depth_m)
    // 使用带亮度的材质，降低底图亮度
    const mat = new THREE.MeshBasicMaterial({
      map: tex,
      opacity: 0.85,  // 略微降低亮度
      transparent: true
    })
    const ground = new THREE.Mesh(geo, mat)

    // 根据倾斜角度设置旋转和位置
    // 0度 = 水平躺地 (-Math.PI/2)，90度 = 垂直站立 (0)
    const tiltRad = (floorTiltAngle.value / 90) * (Math.PI / 2)
    ground.rotation.x = -Math.PI / 2 + tiltRad

    // 垂直时底图立在场景后方
    const tiltFactor = floorTiltAngle.value / 90
    const yPos = tiltFactor * plan.real_depth_m / 2  // 垂直时提升到底图高度的一半
    const zPos = plan.real_depth_m / 2 - tiltFactor * plan.real_depth_m / 2  // 垂直时移到后方

    ground.position.set(plan.real_width_m / 2, yPos, zPos)
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

  // 交换机 - 放大到可见尺寸
  if (switches.length > 0) {
    const geo = new THREE.BoxGeometry(15, 10, 10)  // 15m x 10m x 10m
    const mat = new THREE.MeshStandardMaterial({ metalness: 0.3, roughness: 0.6 })
    const mesh = new THREE.InstancedMesh(geo, mat, switches.length)

    switches.forEach((d, i) => {
      const node = nodes.value.find(n => n.device_id === d.id)
      if (!node) return

      const w = percentToWorld(node.x_percent, node.y_percent, 5)  // 离地5m
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

  // AP - 放大到可见尺寸
  if (aps.length > 0) {
    const geo = new THREE.BoxGeometry(10, 6, 6)  // 10m x 6m x 6m
    const mat = new THREE.MeshStandardMaterial({ metalness: 0.3, roughness: 0.6 })
    const mesh = new THREE.InstancedMesh(geo, mat, aps.length)

    aps.forEach((d, i) => {
      const node = nodes.value.find(n => n.device_id === d.id)
      if (!node) return

      const w = percentToWorld(node.x_percent, node.y_percent, 3)  // 离地3m
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

  // 显示所有筛选后的设备标签
  filteredDevices.value.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return

    const w = percentToWorld(node.x_percent, node.y_percent, 2)

    const el = document.createElement('div')
    el.className = `device-label ${d.status}`
    el.textContent = d.name
    el.style.opacity = '0' // 初始隐藏，由 updateLabelVisibility 控制

    const label = new CSS2DObject(el)
    label.position.set(w.x, w.y, w.z)
    label.userData.deviceId = d.id
    label.userData.deviceStatus = d.status
    label.visible = false // 初始不可见
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

// 根据相机距离更新标签可见性
const LABEL_SHOW_DISTANCE = 200 // 相机距离小于200米时显示标签
function updateLabelVisibility() {
  const { camera, labels } = ctx.value
  if (!labels || !showLabels.value) return

  const cameraPos = camera.position
  const cameraHeight = cameraPos.y

  // 标签可见性：相机高度低于阈值时显示
  const shouldShowLabels = cameraHeight < LABEL_SHOW_DISTANCE

  labels.children.forEach(label => {
    // 计算标签与相机的距离
    const labelPos = label.position
    const dist = cameraPos.distanceTo(labelPos)

    // 近距离显示，远距离隐藏
    label.visible = shouldShowLabels && dist < LABEL_SHOW_DISTANCE * 2

    // 更新标签样式（近处更清晰）
    if (label.element) {
      const opacity = dist < LABEL_SHOW_DISTANCE ? 1 : 0.5
      label.element.style.opacity = opacity
    }
  })
}

// 点击拾取
let selectedInstanceId = null
let selectedMesh = null

function onCanvasClick(e) {
  const { camera, renderer, deviceMeshes, scene } = ctx.value

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  const targets = Object.values(deviceMeshes || {})
  const hits = raycaster.intersectObjects(targets, false)

  // 清除之前的高亮
  if (selectedMesh && selectedInstanceId !== null) {
    const prevDevice = selectedMesh.userData.devices?.[selectedInstanceId]
    if (prevDevice) {
      const c = COLORS[prevDevice.status] || COLORS.online
      selectedMesh.setColorAt(selectedInstanceId, c)
      if (selectedMesh.instanceColor) selectedMesh.instanceColor.needsUpdate = true
    }
  }

  if (hits.length > 0) {
    const hit = hits[0]
    const mesh = hit.object
    const device = mesh.userData.devices?.[hit.instanceId]

    if (device) {
      selectedDevice.value = device
      selectedInstanceId = hit.instanceId
      selectedMesh = mesh

      // 高亮选中设备（变亮）
      const highlightColor = new THREE.Color(0xffffff)
      mesh.setColorAt(hit.instanceId, highlightColor)
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true

      ElMessage.success(`${t('selected')}: ${device.name}`)

      // 相机聚焦到设备
      const node = nodes.value.find(n => n.device_id === device.id)
      if (node) {
        const w = percentToWorld(node.x_percent, node.y_percent, 0)
        ctx.value.controls.target.set(w.x, 30, w.z)
      }
    }
  } else {
    selectedDevice.value = null
    selectedInstanceId = null
    selectedMesh = null
  }
}
      
// 聚焦到设备（带平滑动画）
let focusAnimationId = null
function focusDevice(device) {
  const { camera, controls, deviceMeshes } = ctx.value

  const node = nodes.value.find(n => n.device_id === device.id)
  if (!node) return

  const w = percentToWorld(node.x_percent, node.y_percent, 0)

  // 取消之前的动画
  if (focusAnimationId) {
    cancelAnimationFrame(focusAnimationId)
  }

  // 目标位置
  const targetPos = { x: w.x + 50, y: 100, z: w.z + 50 }
  const targetLookAt = { x: w.x, y: 30, z: w.z }

  // 当前位置
  const startPos = { x: camera.position.x, y: camera.position.y, z: camera.position.z }
  const startLookAt = { x: controls.target.x, y: controls.target.y, z: controls.target.z }

  // 动画参数
  const duration = 60 // 约 1 秒 (60 帧)
  let frame = 0

  const animate = () => {
    frame++
    const progress = Math.min(frame / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3) // ease-out cubic

    // 插值相机位置
    camera.position.x = startPos.x + (targetPos.x - startPos.x) * ease
    camera.position.y = startPos.y + (targetPos.y - startPos.y) * ease
    camera.position.z = startPos.z + (targetPos.z - startPos.z) * ease

    // 插值观察目标
    controls.target.x = startLookAt.x + (targetLookAt.x - startLookAt.x) * ease
    controls.target.y = startLookAt.y + (targetLookAt.y - startLookAt.y) * ease
    controls.target.z = startLookAt.z + (targetLookAt.z - startLookAt.z) * ease

    if (progress < 1) {
      focusAnimationId = requestAnimationFrame(animate)
    } else {
      focusAnimationId = null
    }
  }
  animate()

  selectedDevice.value = device

  // 高亮该设备
  if (deviceMeshes) {
    Object.values(deviceMeshes).forEach(mesh => {
      if (!mesh.userData.devices) return

      mesh.userData.devices.forEach((d, i) => {
        if (d.id === device.id) {
          const highlightColor = new THREE.Color(0xffffff)
          mesh.setColorAt(i, highlightColor)
          if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
        }
      })
    })
  }
}

// 跳转设备详情
function goToDeviceDetail(deviceId) {
  router.push(`/devices/${deviceId}`)
}

// 切换平面图
async function switchPlan(planId) {
  if (!planId) return

  const plan = floorPlans.value.find(p => p.id === planId)
  if (!plan) return

  currentPlan.value = plan

  // 清除旧场景物体
  const { scene, deviceMeshes, linkLines, labels } = ctx.value

  // 清除旧设备
  Object.values(deviceMeshes || {}).forEach(mesh => {
    scene.remove(mesh)
    mesh.geometry?.dispose()
    mesh.material?.dispose()
  })
  ctx.value.deviceMeshes = null

  // 清除旧链路
  if (linkLines) {
    scene.remove(linkLines)
    ctx.value.linkLines = null
  }

  // 清除旧标签
  if (labels) {
    scene.remove(labels)
    ctx.value.labels = null
  }

  // 清除旧底图
  const oldGround = scene.getObjectByName('ground')
  if (oldGround) {
    scene.remove(oldGround)
    oldGround.geometry?.dispose()
    oldGround.material?.dispose()
  }

  // 重新加载节点和链路
  try {
    const nodesRes = await axios.get(`/api/floor-plans/${planId}/nodes`)
    nodes.value = nodesRes.data.items || []

    const linksRes = await axios.get(`/api/floor-plans/${planId}/links`)
    links.value = linksRes.data.items || []

    const topoRes = await axios.get(`/api/floor-plans/${planId}/topology`)
    if (topoRes.data.nodes) nodes.value = topoRes.data.nodes
    if (topoRes.data.links) links.value = topoRes.data.links

    // 重建场景
    loadFloorPlanTexture()
    buildDeviceInstances()
    buildLinks()
    buildLabels()

    // 重置视角
    resetView()

    ElMessage.success(`${t('monitorScreenPlanSwitched')}: ${plan.name}`)
  } catch (e) {
    console.error('切换平面图失败:', e)
    ElMessage.error(t('loadDataFailed'))
  }
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

    // 清除旧底图
    const { scene } = ctx.value
    const oldGround = scene?.getObjectByName('ground')
    if (oldGround) {
      scene.remove(oldGround)
      oldGround.geometry?.dispose()
      oldGround.material?.dispose()
    }

    // 重新加载平面图列表
    const plansRes = await axios.get('/api/floor-plans')
    floorPlans.value = plansRes.data.items || []

    // 设置当前平面图为新上传的
    const newPlan = floorPlans.value.find(p => p.id === res.data.id) || floorPlans.value[floorPlans.value.length - 1]
    if (newPlan) {
      currentPlan.value = newPlan
      currentPlanId.value = newPlan.id

      // 加载新底图纹理
      loadFloorPlanTexture()
    }

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
      currentPlanId.value = floorPlans.value[0].id
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

// 监听筛选变化，重建设备和标签
watch([filterType, filterStatus], () => {
  if (ctx.value.scene) {
    // 清除旧设备
    Object.values(ctx.value.deviceMeshes || {}).forEach(mesh => {
      ctx.value.scene.remove(mesh)
      mesh.geometry?.dispose()
      mesh.material?.dispose()
    })
    // 清除旧标签
    if (ctx.value.labels) {
      ctx.value.scene.remove(ctx.value.labels)
      ctx.value.labels = null
    }
    // 重建
    buildDeviceInstances()
    buildLabels()
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

// 监听底图倾斜角度变化
watch(floorTiltAngle, () => {
  const { scene } = ctx.value
  const ground = scene?.getObjectByName('ground')
  if (ground) {
    // 更新旋转和位置
    const tiltRad = (floorTiltAngle.value / 90) * (Math.PI / 2)
    ground.rotation.x = -Math.PI / 2 + tiltRad

    const tiltFactor = floorTiltAngle.value / 90
    const yPos = tiltFactor * plan.real_depth_m / 2
    const zPos = plan.real_depth_m / 2 - tiltFactor * plan.real_depth_m / 2

    ground.position.set(plan.real_width_m / 2, yPos, zPos)
  }
})

onMounted(async () => {
  initScene()
  await loadData()
  loadFloorPlanTexture()
  buildDeviceInstances()
  buildLinks()
  buildLabels()

  // 自动框景
  fitView()

  // 全屏事件监听
  document.addEventListener('fullscreenchange', onFullscreenChange)
  document.addEventListener('webkitfullscreenchange', onFullscreenChange)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', onResize)

  // 移除全屏事件监听
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', onFullscreenChange)

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
  position: relative;
  width: 100%;
  height: 100%;  /* 使用父容器约束，不溢出 */
  background: #0a0e16;
  overflow: hidden;
}

.canvas-host {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
}

/* 玻璃质感侧边栏（浮动覆盖） */
.side-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 200px;
  height: 100%;
  padding: 12px;
  background: rgba(17, 22, 31, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: #e5e7eb;
  overflow-y: auto;
  border-left: 1px solid rgba(34, 211, 238, 0.2);
  transition: transform 0.3s ease, opacity 0.3s ease;
  z-index: 10;
}

.monitor3d.panel-hidden .side-panel {
  transform: translateX(100%);
}

.monitor3d.fullscreen-mode .side-panel {
  display: none;
}

/* 侧边栏展开/收起按钮 */
.panel-toggle {
  position: absolute;
  right: 200px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 48px;
  background: rgba(17, 22, 31, 0.65);
  backdrop-filter: blur(12px);
  border-radius: 4px 0 0 4px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-right: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 11;
  transition: right 0.3s ease;
  color: #22d3ee;
}

.monitor3d.panel-hidden .panel-toggle {
  right: 0;
}

/* 画布右下角工具按钮（避开侧边栏） */
.canvas-tools {
  position: absolute;
  right: 216px;
  bottom: 16px;
  display: flex;
  gap: 8px;
  z-index: 5;
  transition: right 0.3s ease;
}

.monitor3d.panel-hidden .canvas-tools {
  right: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 14px;
  color: #22d3ee;
}

.plan-switch {
  margin-top: 8px;
}

.plan-switch .el-select {
  width: 100%;
}

.no-plan-hint {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #6b7280;
  font-size: 12px;
}

.kpi-row {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.kpi {
  flex: 1;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 6px;
  padding: 8px 4px;
  text-align: center;
}

.kpi span {
  font-size: 10px;
  color: #6b7280;
}

.kpi b {
  display: block;
  font-size: 16px;
  margin-top: 2px;
}

.kpi b.online {
  color: #22d3ee;
}

.kpi b.offline {
  color: #ff4d4f;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-section .el-select {
  width: 100%;
}

.selected-box {
  background: rgba(26, 34, 48, 0.5);
  border-radius: 6px;
  padding: 8px;
}

.selected-box h4 {
  margin: 0 0 6px;
  color: #22d3ee;
  font-size: 12px;
}

.selected-box p {
  margin: 2px 0;
  font-size: 11px;
}

.hint {
  color: #6b7280;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.layer-control h4 {
  margin: 0 0 6px;
  font-size: 12px;
}

.tilt-control {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tilt-control span {
  font-size: 12px;
  color: #6b7280;
}

.tilt-control .el-slider {
  width: 80px;
}

.tilt-value {
  color: #22d3ee;
  font-weight: 500;
  font-size: 11px;
}

.alert-section h4 {
  margin: 0 0 6px;
  font-size: 12px;
}

.alert-list {
  max-height: 150px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  margin-bottom: 4px;
  cursor: pointer;
}

.alert-item:hover {
  background: rgba(36, 48, 64, 0.6);
}

.alert-icon {
  color: #ff4d4f;
}

.alert-name {
  color: #e5e7eb;
  font-size: 11px;
}

.no-alert {
  color: #6b7280;
  font-size: 11px;
}

/* 设备标签样式（CSS2D） */
:deep(.device-label) {
  padding: 4px 8px;
  background: rgba(26, 34, 48, 0.9);
  border-radius: 4px;
  color: #e5e7eb;
  font-size: 12px;
  white-space: nowrap;
  transition: opacity 0.3s;
}

:deep(.device-label.online) {
  background: rgba(34, 211, 238, 0.9);
  color: #fff;
}

:deep(.device-label.offline) {
  background: rgba(255, 77, 79, 0.9);
  color: #fff;
  animation: pulse 1s infinite;
}

:deep(.device-label.maintenance) {
  background: rgba(255, 161, 22, 0.9);
  color: #fff;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
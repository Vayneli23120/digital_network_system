// Monitor3D 场景核（item 946 切片 9a）
// 从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
// 父侧单实例：sceneState 供 useSceneBuilders/useCanvasInteraction 共享；frameUpdate 由父在 initScene 前赋值；deps 惰性取父 ref。
import { shallowRef } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { getFloorPlanContent } from '@/api'

export function useThreeScene(deps) {
  // 用 shallowRef 持有 three 对象，避免 Vue 深度响应式代理
  const ctx = shallowRef({
    scene: null,
    camera: null,
    renderer: null,
    labelRenderer: null,
    controls: null,
    deviceGroup: null,
    linkLines: null,
    labels: null,
    fiberTrunkGroup: null,
    branchPointGroup: null,
    branchLinkGroup: null,
    dataLinkPaths: null,
  })

  // 厂区真实尺寸（米）
  const plan = {
    real_width_m: 1000,
    real_depth_m: 562.5,
    wall_height_m: 3,
  }

  // 设备尺寸比例系数 - 基于底图短边的百分比（调小以适应放大底图）
  const DEVICE_SIZE_RATIO = {
    switch: 0.008,       // 交换机占底图短边 0.8%
    core_switch: 0.010,  // 核心交换机 1%
    ap: 0.005,           // AP 0.5%
    server_switch: 0.008,
    uce: 0.008,
    router: 0.007,
    firewall: 0.008,
    wlc: 0.010,
  }

  // 状态颜色映射
  const STATUS_COLOR = { online: 0x22d3ee, offline: 0xff4d4f, maintenance: 0xffa116 }

  // 设备发光颜色（让设备在暗背景下更醒目）
  const STATUS_EMISSIVE = { online: 0x0a4a5e, offline: 0x5a1a1a, maintenance: 0x5a3a0a }

  // 复用的 emissive 颜色常量（避免每次 new THREE.Color）
  const EMISSIVE_ON = new THREE.Color(0x333333)
  const EMISSIVE_OFF = new THREE.Color(0x000000)

  // 计算设备基准尺寸（基于底图尺寸）
  function getDeviceBaseSize(deviceType) {
    const ref = Math.min(plan.real_width_m, plan.real_depth_m)  // 用短边做基准
    const ratio = DEVICE_SIZE_RATIO[deviceType] ?? 0.015
    return ref * ratio
  }

  // 坐标转换：百分比 → 世界坐标（米）
  function percentToWorld(xPercent, yPercent, elevation = 0) {
    const x = (Number(xPercent) / 100) * plan.real_width_m
    const z = (Number(yPercent) / 100) * plan.real_depth_m
    return { x, y: elevation, z }
  }

  // 供 useSceneBuilders / useCanvasInteraction 共享的纯对象（不可 reactive/ref 包裹，避免 deep-proxy 破坏 three 对象）
  const sceneState = {
    ctx,
    plan,
    raf: 0,
    raycaster: new THREE.Raycaster(),
    pointer: new THREE.Vector2(),
    DEVICE_SIZE_RATIO,
    STATUS_COLOR,
    STATUS_EMISSIVE,
    EMISSIVE_ON,
    EMISSIVE_OFF,
    getDeviceBaseSize,
    percentToWorld,
    floorPlanLoadId: 0,
    offlineGlowTexture: null,
    impactGlowTexture: null,
    focusAnimationId: null,
    autoFocusDebounceTimer: null,
    snmpIfaceCache: new Map(),
    snmpTrafficCache: new Map(),
    frameUpdate: null,
  }

  // 初始化场景
  function initScene() {
    const host = deps.canvasHost.value
    if (!host) return
    // 清除可能残留的旧画布（HMR/重复挂载防护，避免画布堆叠导致设备等重影）
    while (host.firstChild) host.removeChild(host.firstChild)
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

    // 保存上下文
    Object.assign(ctx.value, { scene, camera, renderer, labelRenderer, controls, host })

    // 动画循环（6 个逐帧函数由父在 initScene 前组合进 frameUpdate）
    const animate = () => {
      sceneState.raf = requestAnimationFrame(animate)
      controls.update()
      sceneState.frameUpdate?.()
      renderer.render(scene, camera)
      labelRenderer.render(scene, camera)
    }
    animate()

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

  // 自动框景 - 根据底图尺寸和画布宽高比计算合适的相机距离
  function fitView() {
    const { camera, controls } = ctx.value
    if (!camera) return

    const fovV = THREE.MathUtils.degToRad(camera.fov)            // 垂直 FOV
    const aspect = camera.aspect || 1

    // 垂直方向需要的距离（按底图"深度"）
    const distV = (plan.real_depth_m / 2) / Math.tan(fovV / 2)
    // 水平方向需要的距离（按底图"宽度"，换算水平 FOV）
    const fovH = 2 * Math.atan(Math.tan(fovV / 2) * aspect)
    const distH = (plan.real_width_m / 2) / Math.tan(fovH / 2)

    const dist = Math.max(distV, distH) * 1.05  // 取大者保证完整可见，1.05 微留边

    // 略微俯视角度（0.6 越小越接近俯视）
    camera.position.set(plan.real_width_m / 2, dist * 0.6, plan.real_depth_m / 2 + dist * 0.8)
    controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
  }

  // 全屏切换
  function toggleFullscreen() {
    if (!deps.isFullscreen.value) {
      // 进入全屏
      const elem = document.querySelector('.monitor3d')
      if (elem.requestFullscreen) {
        elem.requestFullscreen()
      } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen()
      } else if (elem.msRequestFullscreen) {
        elem.msRequestFullscreen()
      }
      deps.isFullscreen.value = true
    } else {
      // 退出全屏
      if (document.exitFullscreen) {
        document.exitFullscreen()
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen()
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen()
      }
      deps.isFullscreen.value = false
    }
  }

  // 监听全屏变化
  function onFullscreenChange() {
    deps.isFullscreen.value = document.fullscreenElement !== null
  }

  // 加载底图纹理
  async function loadFloorPlanTexture() {
    const { scene, renderer } = ctx.value
    if (!deps.currentPlan.value) return

    // 生成新的加载ID，用于并发控制
    const currentLoadId = ++sceneState.floorPlanLoadId

    // 清除旧底图
    const oldGround = scene?.getObjectByName('ground')
    if (oldGround) {
      scene.remove(oldGround)
      oldGround.geometry?.dispose()
      oldGround.material?.dispose()
    }

    const loader = new THREE.TextureLoader()
    let imageUrl = null

    try {
      const imageBlob = await getFloorPlanContent(deps.currentPlan.value.id)
      if (currentLoadId !== sceneState.floorPlanLoadId) return
      imageUrl = URL.createObjectURL(imageBlob)
      const tex = await loader.loadAsync(imageUrl)

      // 并发检查：如果这不是最新的加载请求，则放弃
      if (currentLoadId !== sceneState.floorPlanLoadId) {
        tex.dispose()
        return
      }

      tex.colorSpace = THREE.SRGBColorSpace
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy()

      const geo = new THREE.PlaneGeometry(plan.real_width_m, plan.real_depth_m)
      // 使用带亮度的材质，降低底图亮度
      const mat = new THREE.MeshBasicMaterial({
        map: tex,
        opacity: 0.85,  // 略微降低亮度
        transparent: true,
      })
      const ground = new THREE.Mesh(geo, mat)

      // 根据倾斜角度设置旋转和位置
      // 0度 = 水平躺地 (-Math.PI/2)，90度 = 垂直站立 (0)
      const tiltRad = (deps.floorTiltAngle.value / 90) * (Math.PI / 2)
      ground.rotation.x = -Math.PI / 2 + tiltRad

      // 垂直时底图立在场景后方
      const tiltFactor = deps.floorTiltAngle.value / 90
      const yPos = tiltFactor * plan.real_depth_m / 2  // 垂直时提升到底图高度的一半
      const zPos = plan.real_depth_m / 2 - tiltFactor * plan.real_depth_m / 2  // 垂直时移到后方

      ground.position.set(plan.real_width_m / 2, yPos, zPos)
      ground.name = 'ground'
      scene.add(ground)
    } catch (e) {
      console.error('加载底图失败:', e)
    } finally {
      if (imageUrl) URL.revokeObjectURL(imageUrl)
    }
  }

  // 聚焦到设备（带平滑动画）- 使用基于底图尺寸的距离
  function focusDevice(device) {
    const { camera, controls, deviceGroup } = ctx.value

    const node = deps.nodes.value.find(n => n.device_id === device.id)
    if (!node) return

    const w = percentToWorld(node.x_percent, node.y_percent, 0)

    // 取消之前的动画
    if (sceneState.focusAnimationId) {
      cancelAnimationFrame(sceneState.focusAnimationId)
    }

    // 基于底图尺寸计算聚焦距离
    const ref = Math.min(plan.real_width_m, plan.real_depth_m)
    const focusDist = ref * 0.08
    const focusHeight = ref * 0.05
    const lookAtHeight = ref * 0.03

    // 目标位置
    const targetPos = { x: w.x + focusDist, y: focusHeight, z: w.z + focusDist }
    const targetLookAt = { x: w.x, y: lookAtHeight, z: w.z }

    // 当前位置
    const startPos = { x: camera.position.x, y: camera.position.y, z: camera.position.z }
    const startLookAt = { x: controls.target.x, y: controls.target.y, z: controls.target.z }

    // 动画参数
    const duration = 60
    let frame = 0

    const animate = () => {
      frame++
      const progress = Math.min(frame / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3)

      camera.position.x = startPos.x + (targetPos.x - startPos.x) * ease
      camera.position.y = startPos.y + (targetPos.y - startPos.y) * ease
      camera.position.z = startPos.z + (targetPos.z - startPos.z) * ease

      controls.target.x = startLookAt.x + (targetLookAt.x - startLookAt.x) * ease
      controls.target.y = startLookAt.y + (targetLookAt.y - startLookAt.y) * ease
      controls.target.z = startLookAt.z + (targetLookAt.z - startLookAt.z) * ease

      if (progress < 1) {
        sceneState.focusAnimationId = requestAnimationFrame(animate)
      } else {
        sceneState.focusAnimationId = null
      }
    }
    animate()

    deps.selectedDevice.value = device

    // 高亮该设备（独立 Group）
    if (deviceGroup) {
      deviceGroup.children.forEach(model => {
        const d = model.userData.device
        if (d && d.id === device.id) {
          model.traverse(child => {
            if (child.material) {
              child.material.emissive = EMISSIVE_ON
            }
          })
        }
      })
    }
  }

  // 通用相机平滑动画（缓动到指定位置与注视点）
  function animateCameraTo(targetPos, targetLookAt, duration = 60) {
    const { camera, controls } = ctx.value
    if (!camera) return
    if (sceneState.focusAnimationId) cancelAnimationFrame(sceneState.focusAnimationId)

    const startPos = { x: camera.position.x, y: camera.position.y, z: camera.position.z }
    const startLookAt = { x: controls.target.x, y: controls.target.y, z: controls.target.z }
    let frame = 0

    const animate = () => {
      frame++
      const progress = Math.min(frame / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3)

      camera.position.x = startPos.x + (targetPos.x - startPos.x) * ease
      camera.position.y = startPos.y + (targetPos.y - startPos.y) * ease
      camera.position.z = startPos.z + (targetPos.z - startPos.z) * ease

      controls.target.x = startLookAt.x + (targetLookAt.x - startLookAt.x) * ease
      controls.target.y = startLookAt.y + (targetLookAt.y - startLookAt.y) * ease
      controls.target.z = startLookAt.z + (targetLookAt.z - startLookAt.z) * ease

      if (progress < 1) {
        sceneState.focusAnimationId = requestAnimationFrame(animate)
      } else {
        sceneState.focusAnimationId = null
      }
    }
    animate()
  }

  // 框住多台离线设备所在区域（多设备同时掉线时俯视取景）
  function focusOfflineCluster(list) {
    const { camera } = ctx.value
    if (!camera) return

    const pts = []
    list.forEach(d => {
      const node = deps.nodes.value.find(n => n.device_id === d.id)
      if (node) pts.push(percentToWorld(node.x_percent, node.y_percent, 0))
    })
    if (pts.length === 0) return

    // 计算包围盒中心与跨度
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity
    pts.forEach(p => {
      minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x)
      minZ = Math.min(minZ, p.z); maxZ = Math.max(maxZ, p.z)
    })
    const cx = (minX + maxX) / 2
    const cz = (minZ + maxZ) / 2
    const spanX = Math.max(maxX - minX, 1)
    const spanZ = Math.max(maxZ - minZ, 1)
    const ref = Math.min(plan.real_width_m, plan.real_depth_m)

    // 取景距离：用 FOV 反算容纳整个簇，并留边距
    const fovV = THREE.MathUtils.degToRad(camera.fov)
    const aspect = camera.aspect || 1
    const fovH = 2 * Math.atan(Math.tan(fovV / 2) * aspect)
    const distV = (spanZ / 2) / Math.tan(fovV / 2)
    const distH = (spanX / 2) / Math.tan(fovH / 2)
    let dist = Math.max(distV, distH) * 1.6 + ref * 0.04
    dist = Math.max(dist, ref * 0.1)   // 簇很小时也别贴太近

    const targetPos = { x: cx, y: dist * 0.6, z: cz + dist * 0.8 }
    const targetLookAt = { x: cx, y: 0, z: cz }
    animateCameraTo(targetPos, targetLookAt)
  }

  // 平滑复位到全景（与 fitView 同一取景，但带缓动动画）
  function resetViewAnimated() {
    const { camera } = ctx.value
    if (!camera) return
    const fovV = THREE.MathUtils.degToRad(camera.fov)
    const aspect = camera.aspect || 1
    const distV = (plan.real_depth_m / 2) / Math.tan(fovV / 2)
    const fovH = 2 * Math.atan(Math.tan(fovV / 2) * aspect)
    const distH = (plan.real_width_m / 2) / Math.tan(fovH / 2)
    const dist = Math.max(distV, distH) * 1.05
    const targetPos = { x: plan.real_width_m / 2, y: dist * 0.6, z: plan.real_depth_m / 2 + dist * 0.8 }
    const targetLookAt = { x: plan.real_width_m / 2, y: 0, z: plan.real_depth_m / 2 }
    animateCameraTo(targetPos, targetLookAt)
  }

  // 自动锁定离线设备（去抖：批量掉线/逐台恢复时合并判定）
  // 0 台离线 → 视角复位；1 台 → 锁定该设备；多台 → 框住整片受影响区域
  function scheduleAutoFocusOffline() {
    if (!deps.autoFocusOffline.value) return
    if (sceneState.autoFocusDebounceTimer) clearTimeout(sceneState.autoFocusDebounceTimer)
    sceneState.autoFocusDebounceTimer = setTimeout(() => {
      sceneState.autoFocusDebounceTimer = null
      if (!deps.autoFocusOffline.value) return
      const offline = deps.filteredDevices.value.filter(d =>
        deps.deviceMappings.isDeviceOffline(d) && deps.nodes.value.some(n => n.device_id === d.id)
      )
      if (offline.length === 0) {
        resetViewAnimated()           // 全部恢复，地图视角复位
      } else if (offline.length === 1) {
        focusDevice(offline[0])       // 仅剩一台，锁定该设备
      } else {
        focusOfflineCluster(offline)  // 多台仍离线，重新框住剩余区域
      }
    }, 600)
  }

  // 释放场景资源
  function dispose() {
    cancelAnimationFrame(sceneState.raf)
    if (sceneState.focusAnimationId) cancelAnimationFrame(sceneState.focusAnimationId)
    window.removeEventListener('resize', onResize)
    if (sceneState.autoFocusDebounceTimer) {
      clearTimeout(sceneState.autoFocusDebounceTimer)
      sceneState.autoFocusDebounceTimer = null
    }

    const { renderer, controls, host, labelRenderer, scene } = ctx.value

    // 释放资源
    controls?.dispose()
    renderer?.dispose()

    // 清除场景：材质可能是数组（MeshBasicMaterial[]），需逐个 dispose；
    // 同时释放材质上的纹理（如底图 map），避免 GPU 纹理残留
    scene?.traverse(obj => {
      obj.geometry?.dispose()
      const materials = Array.isArray(obj.material) ? obj.material : [obj.material]
      materials.forEach(mat => {
        mat?.dispose()
        if (mat?.map) mat.map.dispose()
      })
    })

    // 释放模块级纹理并置空，重挂载时 buildOfflineGlow / impact 逻辑会重建，不复用已释放实例
    if (sceneState.offlineGlowTexture) {
      sceneState.offlineGlowTexture.dispose()
      sceneState.offlineGlowTexture = null
    }
    if (sceneState.impactGlowTexture) {
      sceneState.impactGlowTexture.dispose()
      sceneState.impactGlowTexture = null
    }

    // 移除 DOM
    if (renderer?.domElement) host?.removeChild(renderer.domElement)
    if (labelRenderer?.domElement) host?.removeChild(labelRenderer.domElement)
  }

  return {
    sceneState,
    initScene,
    dispose,
    resetView,
    topView,
    fitView,
    toggleFullscreen,
    onFullscreenChange,
    loadFloorPlanTexture,
    focusDevice,
    scheduleAutoFocusOffline,
  }
}

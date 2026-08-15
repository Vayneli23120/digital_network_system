<template>
  <!--
    第 4 层：固特异飞艇粒子点云（three.js）——在整个 GOODYEAR 大 Logo 字标下方来回远航
    （漂移幅度横贯字标全宽），从登录面板前面（Logo 区域）缓缓飞过（z-index 由 Login.vue 的 .login-blimp 控制，高于面板）。
    飞艇形状在离屏 2D canvas 上程序化绘制（椭圆艇体 + 尾鳍 + 吊舱 + 缆绳，舷窗 destination-out 挖孔），
    按 alpha 阈值采样成黄色粒子点云（与第 3 层字标同一技术路线，无网络资源依赖）。
    飞艇在字标全宽来回巡航：匀速飞到一端后减速调头（艇首转身 180°——侧视下先变窄再展开反向，不倒立）再反向巡航，不倒飞；
    全程伴上下浮动与轻微摇摆（漂浮感），粒子带呼吸抖动。
    鼠标悬停（触屏设备除外）：漂移暂停、粒子变白并剧烈抖动，离开后平滑恢复。
    CSS screen 混合、pointer-events none，<768px 隐藏。
  -->
  <div ref="rootRef" class="blimp-particles">
    <canvas ref="canvasRef" class="blimp-canvas" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'

// ---- 可调参数（世界单位 = CSS px；时间单位 = 物理帧 tick，30fps 节流下 1 tick = 1/30s） ----
// 登录页整体按 75% 显示比例呈现：飞艇尺寸/速度/点尺寸等同比缩小（原值 ×0.75）。
const PARAMS = {
  blimpW: 165,             // 飞艇宽度（px）
  blimpH: 105,             // 飞艇高度（px）
  cruiseSpeed: 0.86,       // 巡航速度（px/tick，30fps 下约 25.8px/s，横穿字标约 24s）
  turnFrames: 48,          // 调头时长（tick，约 1.6s，艇首扫过 180°）
  bobAmp: 9,               // 上下浮动幅度（px）
  tiltAmp: 0.055,          // 艇身轻微摆动幅度（rad，叠加在朝向角上）
  jitterAmp: { x: 1.8, y: 2.25, z: 1.2 }, // 粒子呼吸抖动振幅
  hoverJitterBoost: 4.0,   // 悬停时抖动振幅增益（剧烈运动）
  hoverSpeedBoost: 2.0,    // 悬停时抖动角速度增益
  pointSize: 1.95,         // 点尺寸
  spring: 0.12,            // 弹簧回归系数（略硬于字标层，悬停抖动更急促）
  damping: 0.85,           // 速度阻尼
  hoverPad: 10,            // 悬停判定外扩（px）
  hoverRamp: 0.12,         // 悬停状态平滑系数（每物理帧）
  fps: 30,                 // 帧率节流
  maxDpr: 1.5,             // DPR 上限
}

// ---- 着色器：固特异黄双色 + 柔和圆点 + 悬停变白 ----
const VERT = /* glsl */ `
attribute float aBrightness;
uniform float uSize;
uniform float uPixelRatio;
varying float vBrightness;

void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = uSize * uPixelRatio * (1.0 + position.z * 0.02);
  vBrightness = aBrightness;
}
`

const FRAG = /* glsl */ `
precision mediump float;
varying float vBrightness;
uniform float uWhiten;

void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  float circle = smoothstep(0.5, 0.1, d);
  // 固特异黄双色（暗 #FFCC00 / 亮 #FFE9A8），暗点更通透、亮点更实
  vec3 col = mix(vec3(1.0, 0.8, 0.0), vec3(1.0, 0.914, 0.66), vBrightness);
  float shade = 0.2 + vBrightness * 0.92;
  float alpha = circle * smoothstep(0.02, 0.5, shade);
  col *= shade;
  // 悬停：向白色过渡
  col = mix(col, vec3(1.0), uWhiten);
  gl_FragColor = vec4(col, alpha);
}
`

const rootRef = ref(null)
const canvasRef = ref(null)
let state = null // { renderer, scene, camera, geometry, material, ... } 全部句柄

/**
 * 程序化绘制飞艇（64×64 视图放大 3.5 倍 → 224×224 离屏画布）。
 * 与登录卡片 Logo 同款造型；舷窗用 destination-out 挖孔保持镂空。
 */
function drawBlimpShape() {
  const S = 3.5
  const cv = document.createElement('canvas')
  cv.width = 224
  cv.height = 224
  const ctx = cv.getContext('2d', { willReadFrequently: true })
  ctx.scale(S, S)

  // 系留缆绳
  ctx.strokeStyle = '#FFD100'
  ctx.lineWidth = 1.6
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(23, 40)
  ctx.lineTo(25, 33)
  ctx.moveTo(28, 40)
  ctx.lineTo(29, 33)
  ctx.moveTo(33, 40)
  ctx.lineTo(33, 33)
  ctx.moveTo(38, 40)
  ctx.lineTo(37, 33)
  ctx.stroke()

  // 艇体 + 高光
  ctx.fillStyle = '#FFD100'
  ctx.beginPath()
  ctx.ellipse(29, 22, 23, 11.5, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = '#FFE9A8'
  ctx.beginPath()
  ctx.ellipse(24, 18.5, 13, 5.5, 0, 0, Math.PI * 2)
  ctx.fill()

  // 尾鳍（上下两片）
  ctx.fillStyle = '#FFD100'
  ctx.beginPath()
  ctx.moveTo(50, 15)
  ctx.lineTo(61, 6)
  ctx.lineTo(53.5, 23)
  ctx.closePath()
  ctx.fill()
  ctx.beginPath()
  ctx.moveTo(50, 29)
  ctx.lineTo(61, 38)
  ctx.lineTo(53.5, 21)
  ctx.closePath()
  ctx.fill()

  // 吊舱（老浏览器无 roundRect，直接矩形）
  ctx.fillStyle = '#FFE9A8'
  ctx.fillRect(22.5, 38, 14, 8)

  // 舷窗挖孔（粒子镂空，保持窗户轮廓）
  ctx.globalCompositeOperation = 'destination-out'
  ctx.beginPath()
  ctx.arc(26, 42, 1.6, 0, Math.PI * 2)
  ctx.fill()
  ctx.beginPath()
  ctx.arc(31, 42, 1.6, 0, Math.PI * 2)
  ctx.fill()

  return cv
}

/**
 * 按 alpha 阈值采样为归一化坐标点集 { u, v, b }（同步绘制，无需网络资源）。
 */
function sampleBlimp() {
  const cv = drawBlimpShape()
  const w = cv.width
  const h = cv.height
  const data = cv.getContext('2d').getImageData(0, 0, w, h).data
  const step = Math.max(2, Math.round(w / 110)) // ≈2px → 约 3000 粒子
  const pts = []
  for (let y = 0; y < h; y += step) {
    for (let x = 0; x < w; x += step) {
      const a = data[(y * w + x) * 4 + 3]
      if (a > 90) pts.push({ u: x / w, v: y / h, b: Math.random() })
    }
  }
  return pts
}

function start() {
  if (state) return // 幂等
  const root = rootRef.value
  const canvas = canvasRef.value
  if (!root || !canvas) return

  const s = {
    renderer: null,
    scene: null,
    camera: null,
    geometry: null,
    material: null,
    points: null,
    count: 0,
    W: 0,
    H: 0,
    dpr: 1,
    maxDrift: 0,     // 漂移幅度上限（随容器宽度自适应，避免飞出画布被裁掉）
    time: 0,          // 粒子抖动时钟（每物理帧 +1）
    wanderT: 0,       // 漂浮时钟（悬停时冻结 → 漂浮暂停）
    cloudDx: 0,       // 当前巡逻偏移（悬停命中判定用）
    cloudDy: 0,
    patrolDir: -1,    // 巡逻方向：-1 向左（艇首朝左），+1 向右（艇首转身朝右）
    yaw: 0,           // 偏航角（rad）：0 朝左 / π 朝右；调头时平滑扫过 180°（侧视转向）
    turn: 0,          // 调头进度（tick 计数）：0 = 巡航中；>0 调头中，每帧 +1 至 turnFrames
    turnFrom: 0,      // 调头起始偏航角
    turnTo: 0,        // 调头目标偏航角
    pos: null,        // 当前位移位置（Float32Array）
    base: null,       // 艇体本地基点（云中心为原点）
    vel: null,
    speed: null,      // 每点抖动角速度
    phase: null,      // 每点抖动相位
    u: null,          // 归一化采样坐标
    v: null,
    bright: null,
    hoverTarget: 0,   // 悬停目标（0/1）
    hoverSmooth: 0,   // 悬停平滑值（0..1，驱动变白与剧烈抖动）
    isTouch: false,
    raf: 0,
    lastTime: 0,
    io: null,
    ro: null,
    destroyed: false,
  }
  state = s

  // 触屏设备（无 hover）禁用悬停行为，飞艇保持常规漂浮
  s.isTouch = window.matchMedia('(hover: none)').matches

  try {
    s.renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true, // 透明画布，CSS screen 混合由外层容器完成
      antialias: false,
      powerPreference: 'high-performance',
    })
  } catch (err) {
    // WebGL 不可用/上下文创建失败：跳过飞艇粒子层，不得影响登录页
    console.warn('[BlimpParticles] WebGL 初始化失败，飞艇粒子层跳过：', err)
    state = null
    return
  }
  s.renderer.setClearColor(0x000000, 0)
  s.scene = new THREE.Scene()
  s.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100)
  s.camera.position.z = 10

  // 世界单位 = CSS px 的布局：正交相机半宽 = W/2，画布按 DPR 渲染
  function layout() {
    const W = root.clientWidth || 560
    const H = root.clientHeight || 200
    // <768px 时组件被 CSS 隐藏（宽度 0），跳过相机更新避免零范围投影矩阵
    if (W < 1 || H < 1) return
    s.W = W
    s.H = H
    s.maxDrift = Math.max(0, W / 2 - PARAMS.blimpW / 2 - 10)
    s.dpr = Math.min(window.devicePixelRatio || 1, PARAMS.maxDpr)
    s.camera.left = -W / 2
    s.camera.right = W / 2
    s.camera.top = H / 2
    s.camera.bottom = -H / 2
    s.camera.updateProjectionMatrix()
    s.renderer.setPixelRatio(s.dpr)
    s.renderer.setSize(W, H, false)
  }

  function buildGeometry(pts) {
    const n = pts.length
    s.count = n
    s.u = new Float32Array(n)
    s.v = new Float32Array(n)
    s.bright = new Float32Array(n)
    s.speed = new Float32Array(n)
    s.phase = new Float32Array(n)
    s.pos = new Float32Array(n * 3)
    s.base = new Float32Array(n * 3)
    s.vel = new Float32Array(n * 3)
    const bw = PARAMS.blimpW
    const bh = PARAMS.blimpH
    for (let i = 0; i < n; i++) {
      s.u[i] = pts[i].u
      s.v[i] = pts[i].v
      s.bright[i] = pts[i].b
      s.speed[i] = 0.4 + Math.random() * 0.5
      s.phase[i] = Math.random() * Math.PI * 2
      s.base[i * 3] = (pts[i].u - 0.5) * bw
      s.base[i * 3 + 1] = (0.5 - pts[i].v) * bh
    }

    s.geometry = new THREE.BufferGeometry()
    s.geometry.setAttribute('position', new THREE.BufferAttribute(s.pos, 3))
    s.geometry.setAttribute('aBrightness', new THREE.BufferAttribute(s.bright, 1))

    s.material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      transparent: true,
      depthTest: false,
      depthWrite: false,
      uniforms: {
        uSize: { value: PARAMS.pointSize },
        uPixelRatio: { value: s.dpr },
        uWhiten: { value: 0 },
      },
    })
    s.points = new THREE.Points(s.geometry, s.material)
    s.points.frustumCulled = false
    s.scene.add(s.points)
  }

  // ---- 垂直浮动：上下呼吸（悬停时 wanderT 冻结 → 暂停） ----
  function bob(t) {
    return PARAMS.bobAmp * Math.sin(t * 0.0085 + 1.0) + 5 * Math.sin(t * 0.021 + 0.6)
  }

  // ---- 巡逻巡航：匀速飞到一端 → 减速调头（艇首平滑扫过 180°）→ 反向巡航，不倒飞 ----
  function stepPatrol() {
    const P = PARAMS
    const limit = s.maxDrift
    if (s.turn === 0) {
      // 巡航：匀速前进，碰到端点开始调头
      s.cloudDx += s.patrolDir * P.cruiseSpeed
      if (s.cloudDx >= limit || s.cloudDx <= -limit) {
        s.cloudDx = Math.max(-limit, Math.min(limit, s.cloudDx))
        s.turnFrom = s.yaw
        s.turnTo = s.yaw === 0 ? Math.PI : 0
        s.turn = 1
      }
    } else {
      s.turn += 1
      if (s.turn >= P.turnFrames) {
        // 调头完成：翻转巡逻方向，恢复巡航
        s.yaw = s.turnTo
        s.turn = 0
        s.patrolDir *= -1
      } else {
        const p = s.turn / P.turnFrames
        // 速度余弦曲线：前半程减速停住，后半程朝新方向起步（位移净和≈0，近似原地调头）
        s.cloudDx += s.patrolDir * P.cruiseSpeed * Math.cos(Math.PI * p)
        // 偏航角 easeInOut 扫过 180°（两端缓、中间快）
        const e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2
        s.yaw = s.turnFrom + (s.turnTo - s.turnFrom) * e
      }
    }
  }

  // ---- 物理：弹簧向抖动目标回归 + 阻尼；悬停时抖动振幅/频率放大（剧烈运动） ----
  function stepPhysics() {
    const P = PARAMS
    const hover = s.hoverSmooth
    const dy = bob(s.wanderT)
    s.cloudDy = dy
    // 水平位置：巡逻偏移 + 轻微摇摆（整体钳制在 maxDrift 内，避免被画布边缘裁切）
    const limit = Math.max(0, s.maxDrift)
    const wob = Math.min(24, limit * 0.08)
    const dx = Math.max(-limit, Math.min(limit, s.cloudDx + wob * Math.sin(s.wanderT * 0.013 + 2.0)))
    // 朝向：偏航角 yaw（巡航 0/π，调头平滑扫过）→ 侧视转向表现为横向缩放 cos(yaw)：
    // 调头时艇身先变窄（近似正对镜头）再展开成反向，吊舱始终在下、不倒立；再叠轻微摆动
    const sx = Math.cos(s.yaw)
    const ang = P.tiltAmp * Math.sin(s.wanderT * 0.021)
    const cosT = Math.cos(ang)
    const sinT = Math.sin(ang)
    const m00 = cosT * sx
    const m10 = sinT * sx
    const ampX = P.jitterAmp.x * (1 + hover * P.hoverJitterBoost)
    const ampY = P.jitterAmp.y * (1 + hover * P.hoverJitterBoost)
    const ampZ = P.jitterAmp.z * (1 + hover * P.hoverJitterBoost)
    const spMul = 1 + hover * P.hoverSpeedBoost
    const { pos, base, vel, speed, phase } = s
    for (let i = 0; i < s.count; i++) {
      const i3 = i * 3
      const t = s.time
      // 抖动目标 = 朝向变换（偏航横向缩放 + 轻微摆动）后的基点 + 整体漂移 + 呼吸抖动
      const bx = base[i3]
      const by = base[i3 + 1]
      const jx = m00 * bx - sinT * by + dx + Math.sin(t * speed[i] * spMul + phase[i]) * ampX
      const jy = m10 * bx + cosT * by + dy + Math.sin(t * speed[i] * spMul * 0.83 + phase[i] * 1.7) * ampY
      const jz = base[i3 + 2] + Math.cos(t * speed[i] * spMul * 0.9 + phase[i]) * ampZ
      vel[i3] += (jx - pos[i3]) * P.spring
      vel[i3 + 1] += (jy - pos[i3 + 1]) * P.spring
      vel[i3 + 2] += (jz - pos[i3 + 2]) * P.spring
      vel[i3] *= P.damping
      vel[i3 + 1] *= P.damping
      vel[i3 + 2] *= P.damping
      pos[i3] += vel[i3]
      pos[i3 + 1] += vel[i3 + 1]
      pos[i3 + 2] += vel[i3 + 2]
    }
    if (s.count > 0) s.geometry.attributes.position.needsUpdate = true
  }

  // ---- 悬停判定：指针落入飞艇当前包围椭圆 → 暂停漂移 + 变白 + 剧烈抖动 ----
  function onPointerMove(e) {
    if (s.isTouch || s.destroyed) return
    const rect = root.getBoundingClientRect()
    const cx = rect.left + rect.width / 2 + s.cloudDx
    const cy = rect.top + rect.height / 2 - s.cloudDy
    const nx = (e.clientX - cx) / (PARAMS.blimpW / 2 + PARAMS.hoverPad)
    const ny = (e.clientY - cy) / (PARAMS.blimpH / 2 + PARAMS.hoverPad)
    s.hoverTarget = nx * nx + ny * ny <= 1 ? 1 : 0
  }

  function onPointerLeave() {
    if (s.isTouch) return
    s.hoverTarget = 0
  }

  function frame(now) {
    if (s.destroyed) return
    s.raf = requestAnimationFrame(frame)
    // 30fps 节流
    if (now - s.lastTime < 1000 / PARAMS.fps) return
    s.lastTime = now
    s.time += 1
    // 悬停状态平滑逼近；漂浮时钟与巡航悬停时冻结（暂停漂浮），离开后继续
    s.hoverSmooth += (s.hoverTarget - s.hoverSmooth) * PARAMS.hoverRamp
    if (s.hoverSmooth < 0.5) {
      s.wanderT += 1
      stepPatrol()
    }
    stepPhysics()
    if (!s.material) return // 采样失败时无几何/材质，跳过渲染
    s.material.uniforms.uWhiten.value = s.hoverSmooth
    s.material.uniforms.uPixelRatio.value = s.dpr
    s.renderer.render(s.scene, s.camera)
  }

  // ---- 生命周期监听 ----
  s.io = new IntersectionObserver((entries) => {
    if (s.destroyed) return
    const visible = entries[0]?.isIntersecting
    if (visible && s.raf === 0) {
      s.lastTime = performance.now()
      s.raf = requestAnimationFrame(frame)
    } else if (!visible && s.raf !== 0) {
      cancelAnimationFrame(s.raf)
      s.raf = 0
    }
  })
  s.io.observe(root)

  const onVisibility = () => {
    if (s.destroyed) return
    if (document.hidden && s.raf !== 0) {
      cancelAnimationFrame(s.raf)
      s.raf = 0
    } else if (!document.hidden && s.raf === 0) {
      s.lastTime = performance.now()
      s.raf = requestAnimationFrame(frame)
    }
  }
  document.addEventListener('visibilitychange', onVisibility)

  s.ro = new ResizeObserver(layout)
  s.ro.observe(root)

  window.addEventListener('pointermove', onPointerMove, { passive: true })
  window.addEventListener('pointerleave', onPointerLeave, { passive: true })

  s._destroy = () => {
    s.destroyed = true
    if (s.raf !== 0) cancelAnimationFrame(s.raf)
    s.io?.disconnect()
    s.ro?.disconnect()
    document.removeEventListener('visibilitychange', onVisibility)
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerleave', onPointerLeave)
    s.scene?.remove(s.points)
    s.geometry?.dispose()
    s.material?.dispose()
    s.renderer?.dispose()
    try {
      s.renderer?.forceContextLoss()
    } catch {
      /* 忽略上下文已丢失 */
    }
    state = null
  }

  layout()

  // 同步采样飞艇形状（无网络资源，失败仅告警不阻塞页面）
  try {
    buildGeometry(sampleBlimp())
  } catch (err) {
    console.warn('[BlimpParticles] 飞艇形状采样失败：', err)
  }

  s.lastTime = performance.now()
  s.raf = requestAnimationFrame(frame)
}

function stop() {
  if (state && state._destroy) state._destroy()
}

onMounted(start)
onBeforeUnmount(stop)
</script>

<style scoped>
.blimp-particles {
  position: absolute;
  width: min(825px, 75vw); /* 覆盖整个 GOODYEAR 字标宽度（字标为 min(750px, 69vw)，75% 比例）+ 漂移余量 */
  height: 200px;             /* 飞艇 140 + 浮动 24 + 余量 */
  pointer-events: none;      /* 不拦截鼠标事件，交互留给登录卡片 */
  mix-blend-mode: screen;    /* 与深海军蓝背景做屏幕混合 */
}

.blimp-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

/* 小屏（<768px）隐藏飞艇层 */
@media (max-width: 767px) {
  .blimp-particles {
    display: none;
  }
}
</style>

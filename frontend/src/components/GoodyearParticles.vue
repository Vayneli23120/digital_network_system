<template>
  <!--
    第 3 层：固特异飞足 + GOODYEAR 字标粒子点云（three.js）。
    点位置从 public/assets/goodyear-logo.png（透明底 PNG，3840×660）按 alpha 阈值采样，
    保证飞足翅膀与字母轮廓肉眼可辨。黄色双色 #FFCC00（暗）/ #FFE9A8（亮），
    光核在字标中线、X 跟随鼠标 ×1.05；鼠标 14px 半径内排斥（弹性回归 + 悬停抖动增强）。
    容器宽度 min(750px, 69vw)（75% 显示比例），高度按 PNG 实际宽高比 3840/660 计算。
    CSS screen 混合、pointer-events none、两端 mask 渐隐，<768px 隐藏。
  -->
  <div ref="rootRef" class="goodyear-particles">
    <canvas ref="canvasRef" class="particle-canvas" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'

// ---- 可调参数（世界单位 = CSS px） ----
const PARAMS = {
  aspect: 3840 / 660,      // PNG 实际宽高比（5.818:1）
  maxWidth: 750,           // 容器最大宽度（75% 显示比例；CSS 端同样限制 min(750px, 69vw)）
  jitterAmp: { x: 4.5, y: 5.5, z: 3 }, // 抖动振幅
  shadeMin: 0.2,           // 亮度下限（暗点）
  shadeMax: 1.12,          // 亮度上限（亮点）
  pointSize: 2.8,          // 点尺寸
  lightRadius: 76,         // 光核半径
  mouseRange: 14,          // 鼠标排斥半径（loose=1）
  mouseForce: 6,           // 排斥力峰值（速度脉冲 px/帧）
  mouseSmoothing: 0.3,     // 鼠标位置平滑系数
  hoverBoost: 1.3,         // 悬停时抖动振幅增益
  spring: 0.08,            // 弹性回归系数
  damping: 0.85,           // 速度阻尼
  fps: 30,                 // 帧率节流
  maxDpr: 1.5,             // DPR 上限
}

// ---- 着色器：逐点亮度 + 光核提亮 + 柔和圆点 ----
const VERT = /* glsl */ `
attribute float aBrightness;
attribute vec3 aBase;
uniform float uSize;
uniform float uPixelRatio;
uniform float uLightX;
uniform float uLightY;
uniform float uLightRadius;
uniform float uShadeMin;
uniform float uShadeMax;
uniform vec3 uColorDark;
uniform vec3 uColorLight;
varying float vShade;
varying float vCore;
varying vec3 vColor;

void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  // 点尺寸（正交相机下无透视缩放，仅乘 DPR）；z 抖动轻微影响大小
  gl_PointSize = uSize * uPixelRatio * (1.0 + position.z * 0.012);

  // 光核：基于基点位置（排斥位移不改变光核分布，避免鼠标推出暗洞）
  float distToLight = distance(aBase.xy, vec2(uLightX, uLightY));
  vCore = 1.0 - smoothstep(0.0, uLightRadius, distToLight);
  float shade = uShadeMin + aBrightness * (uShadeMax - uShadeMin);
  shade += vCore * uShadeMax * 0.55;
  vShade = shade;
  vColor = mix(uColorDark, uColorLight, aBrightness);
}
`

const FRAG = /* glsl */ `
precision mediump float;
varying float vShade;
varying float vCore;
varying vec3 vColor;

void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  float circle = smoothstep(0.5, 0.1, d);
  // 暗点更通透、亮点更实
  float alpha = circle * smoothstep(0.02, 0.5, vShade);
  vec3 col = vColor * vShade;
  // 光核区域轻微偏暖白
  col += vec3(1.0, 0.95, 0.8) * vCore * 0.25;
  gl_FragColor = vec4(col, alpha);
}
`

const rootRef = ref(null)
const canvasRef = ref(null)
let state = null // { renderer, scene, camera, geometry, material, ... } 全部句柄

// 采样完成后向父组件上报 PNG 内容边界（归一化 v 坐标），
// 供登录页把字标下沿精确对齐到登录面板上沿。
const emit = defineEmits(['bounds'])

/**
 * 加载 PNG 并按 alpha 阈值采样为归一化坐标点集 { u, v, b }。
 * 目标约 450 列采样点（≈2 万粒子），飞足翅膀 25-40px 笔画可保持 3-5 点宽度。
 */
function sampleLogo() {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      try {
        const scale = Math.min(1, 2048 / img.naturalWidth)
        const w = Math.round(img.naturalWidth * scale)
        const h = Math.round(img.naturalHeight * scale)
        const off = document.createElement('canvas')
        off.width = w
        off.height = h
        const octx = off.getContext('2d', { willReadFrequently: true })
        octx.drawImage(img, 0, 0, w, h)
        const data = octx.getImageData(0, 0, w, h).data
        const step = Math.max(2, Math.ceil(w / 450))
        const pts = []
        let minV = 1
        let maxV = 0
        // 右半区（飞足）下沿：PNG 中飞足在右、GOODYEAR 文字在左，
        // 两者下沿高度不同，单独统计右半区供对齐用。
        let footMinV = 1
        let footMaxV = 0
        const footX0 = Math.floor(w * 0.5)
        for (let y = 0; y < h; y += step) {
          for (let x = 0; x < w; x += step) {
            const a = data[(y * w + x) * 4 + 3]
            if (a > 90) {
              const v = y / h
              pts.push({ u: x / w, v, b: Math.random() })
              if (v < minV) minV = v
              if (v > maxV) maxV = v
              if (x >= footX0) {
                if (v < footMinV) footMinV = v
                if (v > footMaxV) footMaxV = v
              }
            }
          }
        }
        resolve({ pts, minV, maxV, footMinV, footMaxV })
      } catch (err) {
        reject(err)
      }
    }
    img.onerror = () => reject(new Error('logo image load failed'))
    img.src = '/assets/goodyear-logo.png'
  })
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
    time: 0,
    pos: null,   // 当前位移位置（Float32Array）
    base: null,  // 基点位置（光核 + 弹簧目标基准）
    vel: null,
    speed: null, // 每点抖动角速度
    phase: null, // 每点抖动相位
    u: null,     // 归一化采样坐标
    v: null,
    bright: null,
    mouse: { x: 0, y: 0, active: false },
    isTouch: false,
    raf: 0,
    lastTime: 0,
    io: null,
    ro: null,
    destroyed: false,
  }
  state = s

  // 触屏设备（无 hover）禁用鼠标扰动
  s.isTouch = window.matchMedia('(hover: none)').matches

  try {
    s.renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true, // 透明画布，CSS screen 混合由外层容器完成
      antialias: false,
      powerPreference: 'high-performance',
    })
  } catch (err) {
    // WebGL 不可用/上下文创建失败：跳过粒子层，不得影响登录页
    console.warn('[GoodyearParticles] WebGL 初始化失败，粒子层跳过：', err)
    state = null
    return
  }
  s.renderer.setClearColor(0x000000, 0)
  s.scene = new THREE.Scene()
  s.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100)
  s.camera.position.z = 10

  // 世界单位 = CSS px 的布局：正交相机半宽 = W/2，画布按 DPR 渲染
  function layout() {
    const W = root.clientWidth || PARAMS.maxWidth
    const H = W / PARAMS.aspect
    root.style.height = `${H}px`
    // <768px 时组件被 CSS 隐藏（宽度 0），跳过相机更新避免零范围投影矩阵
    if (W < 1) return
    s.W = W
    s.H = H
    s.dpr = Math.min(window.devicePixelRatio || 1, PARAMS.maxDpr)
    s.camera.left = -W / 2
    s.camera.right = W / 2
    s.camera.top = H / 2
    s.camera.bottom = -H / 2
    s.camera.updateProjectionMatrix()
    s.renderer.setPixelRatio(s.dpr)
    s.renderer.setSize(W, H, false)
    if (s.count > 0) {
      // 基点随容器缩放重算（弹簧会把现有粒子拉回新基点）
      for (let i = 0; i < s.count; i++) {
        const i3 = i * 3
        s.base[i3] = (s.u[i] - 0.5) * W
        s.base[i3 + 1] = (0.5 - s.v[i]) * H
      }
    }
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
    for (let i = 0; i < n; i++) {
      s.u[i] = pts[i].u
      s.v[i] = pts[i].v
      s.bright[i] = pts[i].b
      s.speed[i] = 0.4 + Math.random() * 0.5
      s.phase[i] = Math.random() * Math.PI * 2
    }
    layout() // 填充 base（依赖 W/H）

    s.geometry = new THREE.BufferGeometry()
    s.geometry.setAttribute('position', new THREE.BufferAttribute(s.pos, 3))
    s.geometry.setAttribute('aBrightness', new THREE.BufferAttribute(s.bright, 1))
    s.geometry.setAttribute('aBase', new THREE.BufferAttribute(s.base, 3))

    s.material = new THREE.ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      transparent: true,
      depthTest: false,
      depthWrite: false,
      uniforms: {
        uSize: { value: PARAMS.pointSize },
        uPixelRatio: { value: s.dpr },
        uLightX: { value: 0 },
        uLightY: { value: 0 },
        uLightRadius: { value: PARAMS.lightRadius },
        uShadeMin: { value: PARAMS.shadeMin },
        uShadeMax: { value: PARAMS.shadeMax },
        uColorDark: { value: new THREE.Color('#FFCC00') },
        uColorLight: { value: new THREE.Color('#FFE9A8') },
      },
    })
    s.points = new THREE.Points(s.geometry, s.material)
    s.points.frustumCulled = false
    s.scene.add(s.points)
  }

  // ---- 物理：弹簧向抖动目标回归 + 鼠标排斥 + 阻尼（弹性回归） ----
  function stepPhysics() {
    const P = PARAMS
    const boost = 1 + (s.mouse.active ? P.hoverBoost : 0)
    const ampX = P.jitterAmp.x * boost
    const ampY = P.jitterAmp.y * boost
    const ampZ = P.jitterAmp.z * boost
    const { pos, base, vel, speed, phase } = s
    for (let i = 0; i < s.count; i++) {
      const i3 = i * 3
      const t = s.time
      // 抖动目标（正弦，逐点相位/角速度不同，形成呼吸感）
      const jx = base[i3] + Math.sin(t * speed[i] + phase[i]) * ampX
      const jy = base[i3 + 1] + Math.sin(t * speed[i] * 0.83 + phase[i] * 1.7) * ampY
      const jz = base[i3 + 2] + Math.cos(t * speed[i] * 0.9 + phase[i]) * ampZ
      vel[i3] += (jx - pos[i3]) * P.spring
      vel[i3 + 1] += (jy - pos[i3 + 1]) * P.spring
      vel[i3 + 2] += (jz - pos[i3 + 2]) * P.spring
      // 鼠标排斥（线性衰减）
      if (s.mouse.active) {
        const dx = pos[i3] - s.mouse.x
        const dy = pos[i3 + 1] - s.mouse.y
        const dist = Math.hypot(dx, dy)
        if (dist < P.mouseRange && dist > 0.001) {
          const f = (1 - dist / P.mouseRange) * P.mouseForce
          vel[i3] += (dx / dist) * f
          vel[i3 + 1] += (dy / dist) * f
        }
      }
      vel[i3] *= P.damping
      vel[i3 + 1] *= P.damping
      vel[i3 + 2] *= P.damping
      pos[i3] += vel[i3]
      pos[i3 + 1] += vel[i3 + 1]
      pos[i3 + 2] += vel[i3 + 2]
    }
    if (s.count > 0) s.geometry.attributes.position.needsUpdate = true
  }

  // ---- 鼠标（世界坐标）：光核 X = 平滑鼠标 X × 1.05，限制在字标范围内 ----
  function onPointerMove(e) {
    if (s.isTouch || s.destroyed) return
    const rect = root.getBoundingClientRect()
    const wx = e.clientX - rect.left - rect.width / 2
    const wy = rect.height / 2 - (e.clientY - rect.top)
    s.mouse.x += (wx - s.mouse.x) * PARAMS.mouseSmoothing
    s.mouse.y += (wy - s.mouse.y) * PARAMS.mouseSmoothing
    s.mouse.active =
      Math.abs(wx) <= rect.width / 2 && Math.abs(wy) <= rect.height / 2
  }

  function onPointerLeave() {
    if (s.isTouch) return
    s.mouse.active = false
  }

  function updateUniforms() {
    if (!s.material) return
    let lightX = s.mouse.x * 1.05
    lightX = Math.max(-s.W / 2, Math.min(s.W / 2, lightX))
    s.material.uniforms.uLightX.value = lightX
    s.material.uniforms.uPixelRatio.value = s.dpr
  }

  function frame(now) {
    if (s.destroyed) return
    s.raf = requestAnimationFrame(frame)
    // 30fps 节流
    if (now - s.lastTime < 1000 / PARAMS.fps) return
    s.lastTime = now
    s.time += 1
    stepPhysics()
    updateUniforms()
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

  // 异步采样 PNG 后建几何（加载期间组件为空，失败仅告警不阻塞页面）
  sampleLogo()
    .then(({ pts, minV, maxV, footMinV, footMaxV }) => {
      if (s.destroyed) return
      buildGeometry(pts)
      emit('bounds', { minV, maxV, footMinV, footMaxV })
    })
    .catch((err) => {
      console.warn('[GoodyearParticles] logo 采样失败：', err)
    })

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
.goodyear-particles {
  position: absolute;
  width: min(750px, 69vw); /* 75% 显示比例（原 1000px/92vw） */
  pointer-events: none;      /* 不拦截鼠标事件，交互留给登录卡片 */
  mix-blend-mode: screen;    /* 与深海军蓝背景做屏幕混合 */
  /* 两端渐隐，避免字标边缘生硬 */
  mask-image: linear-gradient(to right, transparent, #000 10%, #000 90%, transparent);
  -webkit-mask-image: linear-gradient(to right, transparent, #000 10%, #000 90%, transparent);
}

.particle-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

/* 小屏（<768px）隐藏粒子层 */
@media (max-width: 767px) {
  .goodyear-particles {
    display: none;
  }
}
</style>

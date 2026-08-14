// 固特异品牌背景 · 第 1 层：深海暗流（WebGL 流体模拟）
//
// - 双 framebuffer ping-pong 稳定流体；仿真纹理跑 1/4 分辨率，渲染时上采样到全屏
// - 鼠标是"搅动棒"：只注入流体速度搅动暗流（不注入染料，光晕不随鼠标），扰动随时间衰减（decay≈0.925）
// - 纯深海三色渐变（#00010A → #001F3F → #0A2342，无亮带白光——极光效果已按反馈移除）+ 水平暗流漂移（≈swirl/3）
// - 性能：30fps 节流 / devicePixelRatio ≤ 1.5 / IntersectionObserver + 页面隐藏暂停 /
//   触摸设备（无 hover）禁用鼠标扰动只保留自动暗流 / 卸载时取消 RAF 并释放 WebGL 上下文
//
// 用法：
//   const { start, stop } = useOceanBackground(canvasRef)
//   onMounted(start); onBeforeUnmount(stop)

import { ref } from 'vue'

// =============================================================================
// 可调参数（不必逐字复刻，达到观感即可）
// =============================================================================

export const OCEAN_PARAMS = {
  speed: 28,             // 底流强度：暗流自动扰动与鼠标搅动的整体力度基准
  distortion: 18,        // 扰动量：每次 splat 注入的染料强度（0.18 ≈ 18 * 0.01）
  swirl: 20,             // 涡旋强度：vorticity confinement 的旋度力
  swirlIterations: 12,   // 压力求解迭代次数（越高越不可压缩、代价越大）
  scale: 0.85,           // 染料亮度 → 渐变色映射的增益（纯深蓝渐变，无亮带）
  grain: 0.005,          // 胶片噪点幅度
  vignette: 0.45,        // 暗角强度（略加重体现工业厚重感）
  mouseRadius: 0.09,     // 鼠标扰动半径（归一化屏幕坐标）
  mouseStrength: 1.8,    // 鼠标速度 → 流体速度的强度
  mouseSmoothing: 0.1,   // 鼠标位置平滑系数
  mouseVelocity: 0.2,    // 鼠标速度注入系数
  decay: 0.925,          // 扰动每步衰减（1 - dissipation）
  driftSpeed: 6.7,       // 水平暗流漂移（≈ swirl / 3，映射为慢速水平风力）
  ambientInterval: 2.6,  // 自动暗流扰动间隔（秒），无鼠标时也有"潜流涌动"
  simDivisor: 4,         // 仿真分辨率 = 显示分辨率 / simDivisor
  fps: 30,               // 动画帧率节流
  maxDpr: 1.5,           // devicePixelRatio 上限
}

// =============================================================================
// Shaders（GLSL ES 1.00，兼容 chrome63 扫码枪浏览器）
// =============================================================================

const VERT_BASE = `
  precision highp float;
  attribute vec2 aPosition;
  varying vec2 vUv;
  varying vec2 vL;
  varying vec2 vR;
  varying vec2 vT;
  varying vec2 vB;
  uniform vec2 texelSize;
  void main () {
    vUv = aPosition * 0.5 + 0.5;
    vL = vUv - vec2(texelSize.x, 0.0);
    vR = vUv + vec2(texelSize.x, 0.0);
    vT = vUv + vec2(0.0, texelSize.y);
    vB = vUv - vec2(0.0, texelSize.y);
    gl_Position = vec4(aPosition, 0.0, 1.0);
  }
`

// 拷贝 pass（初始清屏等）
const FRAG_COPY = `
  precision mediump float;
  precision mediump sampler2D;
  varying highp vec2 vUv;
  uniform sampler2D uTexture;
  void main () {
    gl_FragColor = texture2D(uTexture, vUv);
  }
`

// 清屏 pass（常量填充，不采样目标纹理，避免同纹理读写的反馈环）
const FRAG_CLEAR = `
  precision mediump float;
  uniform float value;
  void main () {
    gl_FragColor = vec4(value, 0.0, 0.0, 1.0);
  }
`

// 注入 pass：在 point 处以 radius 半径注入 color（染料或速度）
const FRAG_SPLAT = `
  precision mediump float;
  precision mediump sampler2D;
  varying highp vec2 vUv;
  uniform sampler2D uTarget;
  uniform float aspectRatio;
  uniform vec3 color;
  uniform vec2 point;
  uniform float radius;
  void main () {
    vec2 p = vUv - point.xy;
    p.x *= aspectRatio;
    vec3 splat = exp(-dot(p, p) / radius) * color;
    vec3 base = texture2D(uTarget, vUv).xyz;
    gl_FragColor = vec4(base + splat, 1.0);
  }
`

// 平流 pass：沿速度场搬运染料/速度；uWind 注入水平暗流漂移
const FRAG_ADVECTION = `
  precision highp float;
  precision highp sampler2D;
  varying vec2 vUv;
  uniform sampler2D uVelocity;
  uniform sampler2D uSource;
  uniform vec2 texelSize;
  uniform vec2 dyeTexelSize;
  uniform float dt;
  uniform float dissipation;
  uniform vec2 uWind;

  vec4 bilerp (sampler2D sam, vec2 uv, vec2 tsize) {
    vec2 st = uv / tsize - 0.5;
    vec2 iuv = floor(st);
    vec2 fuv = fract(st);
    vec4 a = texture2D(sam, (iuv + vec2(0.5, 0.5)) * tsize);
    vec4 b = texture2D(sam, (iuv + vec2(1.5, 0.5)) * tsize);
    vec4 c = texture2D(sam, (iuv + vec2(0.5, 1.5)) * tsize);
    vec4 d = texture2D(sam, (iuv + vec2(1.5, 1.5)) * tsize);
    return mix(mix(a, b, fuv.x), mix(c, d, fuv.x), fuv.y);
  }

  void main () {
    vec2 vel = bilerp(uVelocity, vUv, texelSize).xy;
    // 水平暗流风力直接加在位移上（texels/s），不累积进速度场，避免无界增长
    vec2 uv = vUv - dt * (vel + uWind) * texelSize;
    vec4 result = bilerp(uSource, uv, dyeTexelSize);
    float decay = 1.0 + dissipation * dt;
    gl_FragColor = result / decay;
  }
`

// 散度 pass
const FRAG_DIVERGENCE = `
  precision mediump float;
  precision mediump sampler2D;
  varying highp vec2 vUv;
  varying highp vec2 vL;
  varying highp vec2 vR;
  varying highp vec2 vT;
  varying highp vec2 vB;
  uniform sampler2D uVelocity;
  void main () {
    float L = texture2D(uVelocity, vL).x;
    float R = texture2D(uVelocity, vR).x;
    float T = texture2D(uVelocity, vT).y;
    float B = texture2D(uVelocity, vB).y;
    vec2 C = texture2D(uVelocity, vUv).xy;
    if (vL.x < 0.0) { L = -C.x; }
    if (vR.x > 1.0) { R = -C.x; }
    if (vT.y > 1.0) { T = -C.y; }
    if (vB.y < 0.0) { B = -C.y; }
    float div = 0.5 * (R - L + T - B);
    gl_FragColor = vec4(div, 0.0, 0.0, 1.0);
  }
`

// 旋度 pass
const FRAG_CURL = `
  precision mediump float;
  precision mediump sampler2D;
  varying highp vec2 vUv;
  varying highp vec2 vL;
  varying highp vec2 vR;
  varying highp vec2 vT;
  varying highp vec2 vB;
  uniform sampler2D uVelocity;
  void main () {
    float L = texture2D(uVelocity, vL).y;
    float R = texture2D(uVelocity, vR).y;
    float T = texture2D(uVelocity, vT).x;
    float B = texture2D(uVelocity, vB).x;
    float vorticity = R - L - T + B;
    gl_FragColor = vec4(0.5 * vorticity, 0.0, 0.0, 1.0);
  }
`

// 涡旋增强 pass：把旋度反馈回速度场，让暗流有卷曲的涡
const FRAG_VORTICITY = `
  precision highp float;
  precision highp sampler2D;
  varying vec2 vUv;
  varying vec2 vL;
  varying vec2 vR;
  varying vec2 vT;
  varying vec2 vB;
  uniform sampler2D uVelocity;
  uniform sampler2D uCurl;
  uniform float curl;
  uniform float dt;
  void main () {
    float L = texture2D(uCurl, vL).x;
    float R = texture2D(uCurl, vR).x;
    float T = texture2D(uCurl, vT).x;
    float B = texture2D(uCurl, vB).x;
    float C = texture2D(uCurl, vUv).x;
    vec2 force = 0.5 * vec2(abs(T) - abs(B), abs(R) - abs(L));
    force /= length(force) + 0.0001;
    force *= curl * C;
    force.y *= -1.0;
    vec2 velocity = texture2D(uVelocity, vUv).xy;
    velocity += force * dt;
    velocity = min(max(velocity, -1000.0), 1000.0);
    gl_FragColor = vec4(velocity, 0.0, 1.0);
  }
`

// 压力求解 pass（Jacobi 迭代）
const FRAG_PRESSURE = `
  precision mediump float;
  precision mediump sampler2D;
  varying highp vec2 vUv;
  varying highp vec2 vL;
  varying highp vec2 vR;
  varying highp vec2 vT;
  varying highp vec2 vB;
  uniform sampler2D uPressure;
  uniform sampler2D uDivergence;
  void main () {
    float L = texture2D(uPressure, vL).x;
    float R = texture2D(uPressure, vR).x;
    float T = texture2D(uPressure, vT).x;
    float B = texture2D(uPressure, vB).x;
    float C = texture2D(uPressure, vUv).x;
    float divergence = texture2D(uDivergence, vUv).x;
    float pressure = (L + R + B + T - divergence) * 0.25;
    gl_FragColor = vec4(pressure, 0.0, 0.0, 1.0);
  }
`

// 压力梯度减法 pass：投影回无散度速度场
const FRAG_GRADIENT_SUBTRACT = `
  precision mediump float;
  precision mediump sampler2D;
  varying highp vec2 vUv;
  varying highp vec2 vL;
  varying highp vec2 vR;
  varying highp vec2 vT;
  varying highp vec2 vB;
  uniform sampler2D uPressure;
  uniform sampler2D uVelocity;
  void main () {
    float L = texture2D(uPressure, vL).x;
    float R = texture2D(uPressure, vR).x;
    float T = texture2D(uPressure, vT).x;
    float B = texture2D(uPressure, vB).x;
    vec2 velocity = texture2D(uVelocity, vUv).xy;
    velocity.xy -= vec2(R - L, T - B);
    gl_FragColor = vec4(velocity, 0.0, 1.0);
  }
`

// 显示 pass：固特异深海三色渐变 + 噪点 + 暗角（极光/bloom 已按反馈移除）
const FRAG_DISPLAY = `
  precision highp float;
  precision highp sampler2D;
  varying vec2 vUv;
  uniform sampler2D uTexture;
  uniform float uTime;
  uniform float uScale;    // 染料 → 渐变的增益
  uniform float uVignette;
  uniform float uGrain;

  // 深海渐变：纯海军蓝三色（无亮带、无白光——极光效果已按反馈移除）
  vec3 goodyearGradient (float t) {
    vec3 c0 = vec3(0.0, 0.0039, 0.0392);    // #00010A
    vec3 c1 = vec3(0.0, 0.1216, 0.2471);    // #001F3F
    vec3 c2 = vec3(0.0392, 0.1373, 0.2588); // #0A2342
    vec3 col = mix(c0, c1, smoothstep(0.0, 0.45, t));
    col = mix(col, c2, smoothstep(0.45, 1.0, t));
    return col;
  }

  float hash (vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
  }

  void main () {
    vec4 dye = texture2D(uTexture, vUv);

    // 基底：静态垂直渐变（顶深底稍浅）+ 极缓呼吸，染料在其上叠加流动
    float baseT = 0.12 + 0.22 * (1.0 - vUv.y) + 0.03 * sin(vUv.x * 6.2831 + uTime * 0.05);
    float lum = dot(dye.rgb, vec3(0.299, 0.587, 0.114));
    float t = clamp(baseT + lum * uScale, 0.0, 1.0);
    vec3 col = goodyearGradient(t);

    // 胶片噪点
    col += (hash(vUv * vec2(997.0, 991.0) + fract(uTime) * 7.0) - 0.5) * uGrain;

    // 暗角（厚重感）
    vec2 vc = vUv - 0.5;
    col *= 1.0 - uVignette * dot(vc, vc) * 2.0;

    gl_FragColor = vec4(col, 1.0);
  }
`

// =============================================================================
// GL 工具
// =============================================================================

function compileShader(gl, type, source) {
  const shader = gl.createShader(type)
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader)
    gl.deleteShader(shader)
    throw new Error(`Shader compile error: ${info}`)
  }
  return shader
}

function createProgram(gl, vsSource, fsSource) {
  const program = gl.createProgram()
  gl.attachShader(program, compileShader(gl, gl.VERTEX_SHADER, vsSource))
  gl.attachShader(program, compileShader(gl, gl.FRAGMENT_SHADER, fsSource))
  gl.bindAttribLocation(program, 0, 'aPosition')
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(program)
    gl.deleteProgram(program)
    throw new Error(`Program link error: ${info}`)
  }
  const uniforms = {}
  const count = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS)
  for (let i = 0; i < count; i++) {
    const info = gl.getActiveUniform(program, i)
    uniforms[info.name] = gl.getUniformLocation(program, info.name)
  }
  return { program, uniforms }
}

function supportRenderTextureFormat(gl, internalFormat, format, type) {
  const texture = gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D, texture)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
  gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, 4, 4, 0, format, type, null)
  const fbo = gl.createFramebuffer()
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo)
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0)
  const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER)
  gl.deleteTexture(texture)
  gl.deleteFramebuffer(fbo)
  return status === gl.FRAMEBUFFER_COMPLETE
}

function getSupportedFormat(gl, internalFormat, format, type) {
  if (!supportRenderTextureFormat(gl, internalFormat, format, type)) {
    // 半精度不支持时逐级降级到 RGBA8
    if (internalFormat === gl.R16F) return getSupportedFormat(gl, gl.RG16F, gl.RG, type)
    if (internalFormat === gl.RG16F) return getSupportedFormat(gl, gl.RGBA16F, gl.RGBA, type)
    return null
  }
  return { internalFormat, format }
}

function createFBO(gl, w, h, { internalFormat, format }, type, filter) {
  gl.activeTexture(gl.TEXTURE0)
  const texture = gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D, texture)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
  gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, w, h, 0, format, type, null)
  const fbo = gl.createFramebuffer()
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo)
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0)
  gl.viewport(0, 0, w, h)
  gl.clear(gl.COLOR_BUFFER_BIT)
  return { texture, fbo, width: w, height: h, attach(id) { gl.activeTexture(gl.TEXTURE0 + id); gl.bindTexture(gl.TEXTURE_2D, texture) } }
}

function createDoubleFBO(gl, w, h, format, type, filter) {
  return { read: createFBO(gl, w, h, format, type, filter), write: createFBO(gl, w, h, format, type, filter), swap() { const t = this.read; this.read = this.write; this.write = t } }
}

function resizeFBO(gl, fbo, w, h, { internalFormat, format }, type, filter) {
  gl.activeTexture(gl.TEXTURE0)
  gl.bindTexture(gl.TEXTURE_2D, fbo.texture)
  gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, w, h, 0, format, type, null)
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo.fbo)
  gl.viewport(0, 0, w, h)
  gl.clear(gl.COLOR_BUFFER_BIT)
  fbo.width = w
  fbo.height = h
}

function resizeDoubleFBO(gl, double, w, h, format, type, filter) {
  resizeFBO(gl, double.read, w, h, format, type, filter)
  resizeFBO(gl, double.write, w, h, format, type, filter)
}

// =============================================================================
// 主 composable
// =============================================================================

export function useOceanBackground(canvasRef) {
  const running = ref(false)
  let state = null // { gl, ext, programs, fbos, ... } 全部句柄

  // ---- 全屏 quad 顶点 ----
  function createBlit(gl) {
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, -1, 1, 1, 1, 1, 1, 1, -1, -1, -1]), gl.STATIC_DRAW)
    gl.enableVertexAttribArray(0)
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0)
    return buffer
  }

  function blit(gl, target) {
    if (target == null) {
      gl.viewport(0, 0, state.displayWidth, state.displayHeight)
      gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    } else {
      gl.viewport(0, 0, target.width, target.height)
      gl.bindFramebuffer(gl.FRAMEBUFFER, target.fbo)
    }
    gl.drawArrays(gl.TRIANGLES, 0, 6)
  }

  /**
   * 纹理格式协商：
   * - WebGL2：优先 R16F/RG16F/RGBA16F（core 可渲染），全部失败降级 RGBA8。
   * - WebGL1：无 R16F/RGBA16F 枚举，半精度只能走 OES_texture_half_float 扩展的
   *   RGBA + HALF_FLOAT（扩展保证可作颜色附件），仍失败则降级 RGBA8。
   */
  function negotiateFormats(gl, isWebGL2) {
    const rgba8 = { internalFormat: gl.RGBA, format: gl.RGBA }
    if (isWebGL2) {
      const half = getSupportedFormat(gl, gl.RGBA16F, gl.RGBA, gl.HALF_FLOAT)
      if (half) {
        return {
          formatRGBA: half,
          formatRG: getSupportedFormat(gl, gl.RG16F, gl.RG, gl.HALF_FLOAT) || half,
          formatR: getSupportedFormat(gl, gl.R16F, gl.RED, gl.HALF_FLOAT) || half,
          halfFloatTexType: gl.HALF_FLOAT,
        }
      }
      return { formatRGBA: rgba8, formatRG: rgba8, formatR: rgba8, halfFloatTexType: gl.UNSIGNED_BYTE }
    }
    const halfFloat = gl.getExtension('OES_texture_half_float')
    if (halfFloat && supportRenderTextureFormat(gl, gl.RGBA, gl.RGBA, halfFloat.HALF_FLOAT)) {
      const rgbaHalf = { internalFormat: gl.RGBA, format: gl.RGBA }
      return { formatRGBA: rgbaHalf, formatRG: rgbaHalf, formatR: rgbaHalf, halfFloatTexType: halfFloat.HALF_FLOAT }
    }
    return { formatRGBA: rgba8, formatRG: rgba8, formatR: rgba8, halfFloatTexType: gl.UNSIGNED_BYTE }
  }

  function start() {
    if (state) return
    const canvas = canvasRef.value
    if (!canvas) return

    // WebGL2 优先；扫码枪等老浏览器（chrome63）回退 WebGL1
    const ctxOpts = { alpha: false, antialias: false, depth: false, stencil: false, preserveDrawingBuffer: false }
    let gl = canvas.getContext('webgl2', ctxOpts)
    const isWebGL2 = !!gl
    if (!gl) gl = canvas.getContext('webgl', ctxOpts) || canvas.getContext('experimental-webgl', ctxOpts)
    if (!gl) {
      console.warn('[useOceanBackground] WebGL 不可用，暗流背景层跳过（保留 CSS 渐变底色）')
      return
    }

    // ---- 扩展协商（半精度纹理 + 线性过滤，失败降级 RGBA8） ----
    const ext = negotiateFormats(gl, isWebGL2)
    const linearSupport = gl.getExtension('OES_texture_half_float_linear') || gl.getExtension('OES_texture_float_linear')
    const filter = ext.halfFloatTexType === gl.UNSIGNED_BYTE ? gl.LINEAR : (linearSupport ? gl.LINEAR : gl.NEAREST)

    // ---- 编译程序（失败则跳过本层，不得影响登录页） ----
    let programs
    try {
      programs = {
        copy: createProgram(gl, VERT_BASE, FRAG_COPY),
        clear: createProgram(gl, VERT_BASE, FRAG_CLEAR),
        splat: createProgram(gl, VERT_BASE, FRAG_SPLAT),
        advection: createProgram(gl, VERT_BASE, FRAG_ADVECTION),
        divergence: createProgram(gl, VERT_BASE, FRAG_DIVERGENCE),
        curl: createProgram(gl, VERT_BASE, FRAG_CURL),
        vorticity: createProgram(gl, VERT_BASE, FRAG_VORTICITY),
        pressure: createProgram(gl, VERT_BASE, FRAG_PRESSURE),
        gradientSubtract: createProgram(gl, VERT_BASE, FRAG_GRADIENT_SUBTRACT),
        display: createProgram(gl, VERT_BASE, FRAG_DISPLAY),
      }
    } catch (err) {
      console.warn('[useOceanBackground] 着色器编译失败，暗流背景层跳过：', err)
      gl.getExtension('WEBGL_lose_context')?.loseContext()
      return
    }

    const P = OCEAN_PARAMS

    // ---- 指针状态（只用于搅动流体，白光极光不跟随鼠标） ----
    const pointer = {
      active: false,
      targetX: 0.5, targetY: 0.5, // 目标位置（归一化）
      smoothX: 0.5, smoothY: 0.5, // 平滑位置
      velX: 0, velY: 0,           // 平滑速度
    }

    // ---- 帧循环与暂停控制 ----
    let raf = 0
    let lastTime = 0
    let ambientTimer = 0
    let destroyed = false

    const s = (state = {
      gl, ext, programs, pointer, filter,
      displayWidth: 0, displayHeight: 0,
      simWidth: 0, simHeight: 0,
      dye: null, velocity: null, divergence: null, curl: null, pressure: null,
      paused: false,
      interval: 1000 / P.fps,
    })

    createBlit(gl)

    // ---- 画布尺寸（DPR 上限 1.5；仿真 1/4 分辨率） ----
    function resizeCanvas() {
      const dpr = Math.min(window.devicePixelRatio || 1, P.maxDpr)
      const w = canvas.clientWidth || window.innerWidth
      const h = canvas.clientHeight || window.innerHeight
      const dw = Math.max(2, Math.floor(w * dpr))
      const dh = Math.max(2, Math.floor(h * dpr))
      if (canvas.width !== dw || canvas.height !== dh) {
        canvas.width = dw
        canvas.height = dh
      }
      s.displayWidth = dw
      s.displayHeight = dh
      s.simWidth = Math.max(64, Math.floor(dw / P.simDivisor))
      s.simHeight = Math.max(64, Math.floor(dh / P.simDivisor))
      // texelSize 供显示/平流 uniform 使用（归一化）
      s.texelSizeX = 1.0 / s.simWidth
      s.texelSizeY = 1.0 / s.simHeight
      s.dyeTexelSizeX = 1.0 / s.simWidth
      s.dyeTexelSizeY = 1.0 / s.simHeight

      if (s.dye) {
        resizeDoubleFBO(gl, s.dye, s.simWidth, s.simHeight, ext.formatRGBA, ext.halfFloatTexType, filter)
        resizeDoubleFBO(gl, s.velocity, s.simWidth, s.simHeight, ext.formatRG, ext.halfFloatTexType, filter)
        resizeFBO(gl, s.divergence, s.simWidth, s.simHeight, ext.formatR, ext.halfFloatTexType, filter)
        resizeFBO(gl, s.curl, s.simWidth, s.simHeight, ext.formatR, ext.halfFloatTexType, filter)
        resizeDoubleFBO(gl, s.pressure, s.simWidth, s.simHeight, ext.formatR, ext.halfFloatTexType, filter)
      } else {
        s.dye = createDoubleFBO(gl, s.simWidth, s.simHeight, ext.formatRGBA, ext.halfFloatTexType, filter)
        s.velocity = createDoubleFBO(gl, s.simWidth, s.simHeight, ext.formatRG, ext.halfFloatTexType, filter)
        s.divergence = createFBO(gl, s.simWidth, s.simHeight, ext.formatR, ext.halfFloatTexType, filter)
        s.curl = createFBO(gl, s.simWidth, s.simHeight, ext.formatR, ext.halfFloatTexType, filter)
        // 压力用双缓冲：Jacobi 迭代读写必须 ping-pong，避免同纹理反馈环
        s.pressure = createDoubleFBO(gl, s.simWidth, s.simHeight, ext.formatR, ext.halfFloatTexType, filter)
      }
    }

    resizeCanvas()

    // ---- 注入（染料/速度通用；withDye=false 时只搅动速度不注入光） ----
    function splat(x, y, dx, dy, color, withDye = true) {
      const p = programs.splat
      gl.useProgram(p.program)
      gl.uniform1i(p.uniforms.uTarget, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      gl.uniform1f(p.uniforms.aspectRatio, s.simWidth / s.simHeight)
      gl.uniform2f(p.uniforms.point, x, y)
      gl.uniform3f(p.uniforms.color, dx, dy, 0.0)
      gl.uniform1f(p.uniforms.radius, P.mouseRadius)
      blit(gl, s.velocity.write)
      s.velocity.swap()

      if (!withDye) return

      gl.uniform1i(p.uniforms.uTarget, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.dye.read.texture)
      gl.uniform3f(p.uniforms.color, color[0], color[1], color[2])
      blit(gl, s.dye.write)
      s.dye.swap()
    }

    // ---- 鼠标搅动：只搅动流体速度，不注入霞光染料（光晕不随鼠标） ----
    function splatPointer() {
      // 速度注入量级：velX 为 uv/s，×interval 还原为每帧位移；×6000 与经典流体实现
      // 的 SPLAT_FORCE 同量级，才能在平流中产生可见涡流（否则慢约 4 个数量级）
      const dx = pointer.velX * P.mouseStrength * P.mouseVelocity * s.interval * 6000
      const dy = pointer.velY * P.mouseStrength * P.mouseVelocity * s.interval * 6000
      splat(pointer.smoothX, pointer.smoothY, dx, dy, [0, 0, 0], false)
    }

    // ---- 自动暗流：无鼠标时也有"潜流涌动"（极缓水平漂移） ----
    function splatAmbient(dt) {
      const x = 0.15 + Math.random() * 0.7
      const y = 0.15 + Math.random() * 0.7
      const strength = 0.04 + Math.random() * 0.06
      const drift = P.driftSpeed // 水平漂移速度 ≈ swirl / 3
      // 青绿调染料经渐变映射呈现海军蓝暗流（不掺白）；速度注入极小（≈0.15 texels/帧级）
      splat(x, y, drift * 0.15, (Math.random() - 0.5) * drift * 0.1, [0.45 * strength, 0.9 * strength, 0.75 * strength])
      ambientTimer = 0
    }

    // ---- 单步仿真 ----
    function step(dt) {
      gl.disable(gl.BLEND)

      // 1. 注入：鼠标搅动 + 定时暗流
      if (pointer.active) splatPointer()
      ambientTimer += dt
      if (ambientTimer >= P.ambientInterval) splatAmbient(dt)

      // 2. 涡旋增强（swirl 旋度力）
      const vorticity = programs.vorticity
      gl.useProgram(vorticity.program)
      gl.uniform2f(vorticity.uniforms.texelSize, s.texelSizeX, s.texelSizeY)
      gl.uniform1i(vorticity.uniforms.uVelocity, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      gl.uniform1i(vorticity.uniforms.uCurl, 1)
      gl.activeTexture(gl.TEXTURE1)
      gl.bindTexture(gl.TEXTURE_2D, s.curl.texture)
      gl.uniform1f(vorticity.uniforms.curl, P.swirl)
      gl.uniform1f(vorticity.uniforms.dt, dt)
      blit(gl, s.velocity.write)
      s.velocity.swap()

      // 3. 散度 → 旋度 → 压力迭代 → 梯度减法（投影回无散度场）
      const divergence = programs.divergence
      gl.useProgram(divergence.program)
      gl.uniform2f(divergence.uniforms.texelSize, s.texelSizeX, s.texelSizeY)
      gl.uniform1i(divergence.uniforms.uVelocity, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      blit(gl, s.divergence)

      const curl = programs.curl
      gl.useProgram(curl.program)
      gl.uniform2f(curl.uniforms.texelSize, s.texelSizeX, s.texelSizeY)
      gl.uniform1i(curl.uniforms.uVelocity, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      blit(gl, s.curl)

      const clear = programs.clear
      gl.useProgram(clear.program)
      gl.uniform1f(clear.uniforms.value, 0)
      blit(gl, s.pressure.read)
      blit(gl, s.pressure.write)

      const pressure = programs.pressure
      gl.useProgram(pressure.program)
      gl.uniform2f(pressure.uniforms.texelSize, s.texelSizeX, s.texelSizeY)
      gl.uniform1i(pressure.uniforms.uDivergence, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.divergence.texture)
      for (let i = 0; i < P.swirlIterations; i++) {
        // 读 pressure.read、写 pressure.write，迭代后 swap（避免同纹理读写反馈环）
        gl.uniform1i(pressure.uniforms.uPressure, 1)
        gl.activeTexture(gl.TEXTURE1)
        gl.bindTexture(gl.TEXTURE_2D, s.pressure.read.texture)
        blit(gl, s.pressure.write)
        s.pressure.swap()
      }

      const gradSubtract = programs.gradientSubtract
      gl.useProgram(gradSubtract.program)
      gl.uniform2f(gradSubtract.uniforms.texelSize, s.texelSizeX, s.texelSizeY)
      gl.uniform1i(gradSubtract.uniforms.uPressure, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.pressure.read.texture)
      gl.uniform1i(gradSubtract.uniforms.uVelocity, 1)
      gl.activeTexture(gl.TEXTURE1)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      blit(gl, s.velocity.write)
      s.velocity.swap()

      // 4. 平流（含水平暗流漂移风力 + decay 衰减）
      const advection = programs.advection
      gl.useProgram(advection.program)
      gl.uniform2f(advection.uniforms.texelSize, s.texelSizeX, s.texelSizeY)
      gl.uniform2f(advection.uniforms.dyeTexelSize, s.dyeTexelSizeX, s.dyeTexelSizeY)
      gl.uniform1i(advection.uniforms.uVelocity, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      gl.uniform1i(advection.uniforms.uSource, 1)
      gl.activeTexture(gl.TEXTURE1)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      gl.uniform1f(advection.uniforms.dt, dt)
      gl.uniform1f(advection.uniforms.dissipation, 1.0 - P.decay)
      // 水平漂移风力 ≈ swirl / 3（texels/s，直接加在平流位移上）
      gl.uniform2f(advection.uniforms.uWind, P.driftSpeed, 0.0)
      blit(gl, s.velocity.write)
      s.velocity.swap()

      gl.uniform1i(advection.uniforms.uVelocity, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.velocity.read.texture)
      gl.uniform1i(advection.uniforms.uSource, 1)
      gl.activeTexture(gl.TEXTURE1)
      gl.bindTexture(gl.TEXTURE_2D, s.dye.read.texture)
      gl.uniform1f(advection.uniforms.dissipation, 1.0 - P.decay)
      gl.uniform2f(advection.uniforms.uWind, 0.0, 0.0) // 染料平流不重复注入风力
      blit(gl, s.dye.write)
      s.dye.swap()

      // 5. 显示（全屏上采样 + 固特异深海渐变）
      renderDisplay()
    }

    function renderDisplay() {
      const p = programs.display
      gl.useProgram(p.program)
      gl.uniform2f(p.uniforms.texelSize, 1.0 / s.displayWidth, 1.0 / s.displayHeight)
      gl.uniform1i(p.uniforms.uTexture, 0)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, s.dye.read.texture)
      gl.uniform1f(p.uniforms.uTime, performance.now() / 1000)
      gl.uniform1f(p.uniforms.uScale, P.scale)
      gl.uniform1f(p.uniforms.uVignette, P.vignette)
      gl.uniform1f(p.uniforms.uGrain, P.grain)
      blit(gl, null)
    }

    // ---- 帧循环（30fps 节流） ----
    function frame(now) {
      if (destroyed) return
      raf = requestAnimationFrame(frame)
      if (s.paused) return
      const elapsed = now - lastTime
      if (elapsed < s.interval) return
      const dt = Math.min(Math.max(elapsed / 1000, 0.016), 0.05)
      lastTime = now

      // 平滑鼠标位置与速度
      pointer.smoothX += (pointer.targetX - pointer.smoothX) * P.mouseSmoothing
      pointer.smoothY += (pointer.targetY - pointer.smoothY) * P.mouseSmoothing

      step(dt)
    }

    // ---- 事件：鼠标搅动（窗口级监听，登录卡片上移动也能搅动暗流） ----
    const touchDevice = window.matchMedia && window.matchMedia('(hover: none)').matches

    function toNorm(e) {
      return {
        x: e.clientX / window.innerWidth,
        y: 1.0 - e.clientY / window.innerHeight,
      }
    }

    function onPointerMove(e) {
      const n = toNorm(e)
      pointer.velX = (n.x - pointer.targetX) / Math.max(s.interval / 1000, 0.001)
      pointer.velY = (n.y - pointer.targetY) / Math.max(s.interval / 1000, 0.001)
      pointer.targetX = n.x
      pointer.targetY = n.y
      pointer.active = true
    }

    function onPointerLeave() {
      pointer.active = false
      pointer.velX = 0
      pointer.velY = 0
    }

    if (!touchDevice) {
      window.addEventListener('pointermove', onPointerMove, { passive: true })
      window.addEventListener('pointerdown', onPointerMove, { passive: true })
      window.addEventListener('pointerup', onPointerLeave)
      window.addEventListener('pointerleave', onPointerLeave)
      document.addEventListener('mouseleave', onPointerLeave)
    }

    // ---- 暂停控制：IntersectionObserver + 页面隐藏 + 上下文丢失 ----
    const io = new IntersectionObserver((entries) => {
      s.paused = !entries[0].isIntersecting
    })
    io.observe(canvas)

    function onVisibility() {
      if (document.hidden) {
        s.paused = true
        pointer.active = false
      }
    }
    document.addEventListener('visibilitychange', onVisibility)

    function onContextLost(e) {
      e.preventDefault()
      s.paused = true
    }
    canvas.addEventListener('webglcontextlost', onContextLost, false)

    const ro = new ResizeObserver(() => resizeCanvas())
    ro.observe(canvas)

    // ---- 启动 ----
    running.value = true
    lastTime = performance.now()
    raf = requestAnimationFrame(frame)

    // 注册清理句柄
    s._destroy = function destroy() {
      destroyed = true
      cancelAnimationFrame(raf)
      ro.disconnect()
      io.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
      canvas.removeEventListener('webglcontextlost', onContextLost)
      if (!touchDevice) {
        window.removeEventListener('pointermove', onPointerMove)
        window.removeEventListener('pointerdown', onPointerMove)
        window.removeEventListener('pointerup', onPointerLeave)
        window.removeEventListener('pointerleave', onPointerLeave)
        document.removeEventListener('mouseleave', onPointerLeave)
      }
      // 释放全部 GL 资源并主动丢失上下文
      Object.values(programs).forEach((m) => gl.deleteProgram(m.program))
      ;[s.dye, s.velocity, s.pressure].forEach((d) => {
        if (!d) return
        gl.deleteFramebuffer(d.read.fbo)
        gl.deleteFramebuffer(d.write.fbo)
        gl.deleteTexture(d.read.texture)
        gl.deleteTexture(d.write.texture)
      })
      ;[s.divergence, s.curl].forEach((f) => {
        if (!f) return
        gl.deleteFramebuffer(f.fbo)
        gl.deleteTexture(f.texture)
      })
      gl.getExtension('WEBGL_lose_context')?.loseContext()
      state = null
      running.value = false
    }
  }

  function stop() {
    if (state && state._destroy) state._destroy()
  }

  return { running, start, stop }
}

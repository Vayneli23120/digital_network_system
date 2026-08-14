/**
 * 第 2 层：2D 点阵网格背景（Goodyear 登录页）。
 *
 * - 约 90px 间距的白色点阵，相邻点连线 alpha 0.08、点 alpha 0.16
 * - 鼠标 140px 范围内排斥（最大 30，线性衰减）
 * - 弹簧回归 spring 0.05、速度阻尼 damping 0.85
 * - 靠近鼠标的点放大（半径 1.8 → 3.8）并提亮（alpha 0.16 → 0.56）
 * - 最大速度 < 0.01 时自动暂停 RAF，鼠标移动时唤醒
 *
 * 工程要求：30fps 节流、DPR 上限 1.5、IntersectionObserver 暂停、
 * 卸载时取消 RAF、触屏设备（无 hover）禁用鼠标扰动。
 */
import { ref } from 'vue'

export const DOT_GRID_PARAMS = {
  spacing: 90,           // 点阵间距（CSS px）
  lineAlpha: 0.08,       // 连线透明度
  dotAlpha: 0.16,        // 点基础透明度
  dotRadius: 1.8,        // 点基础半径
  nearMouseRadius: 3.8,  // 靠近鼠标时的点半径
  nearMouseAlpha: 0.56,  // 靠近鼠标时的点透明度
  repulsionRadius: 140,  // 鼠标排斥半径（CSS px）
  repulsionMax: 30,      // 排斥力峰值（速度脉冲，px/帧）
  spring: 0.05,          // 弹簧回归系数
  damping: 0.85,         // 速度阻尼
  idleSpeed: 0.01,       // 自动暂停阈值（最大速度）
  fps: 30,               // 帧率节流
  maxDpr: 1.5,           // DPR 上限
}

export function useDotGrid(canvasRef) {
  const running = ref(false)
  let state = null // { ctx, dots, mouse, io, ro, ... } 全部句柄

  /**
   * 按画布 CSS 尺寸重建点阵网格（resize 时调用，位移状态重建）。
   */
  function buildGrid(s) {
    const cols = Math.floor(s.w / DOT_GRID_PARAMS.spacing) + 1
    const rows = Math.floor(s.h / DOT_GRID_PARAMS.spacing) + 1
    const dots = []
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = c * DOT_GRID_PARAMS.spacing
        const y = r * DOT_GRID_PARAMS.spacing
        dots.push({ baseX: x, baseY: y, x, y, vx: 0, vy: 0, col: c, row: r })
      }
    }
    s.dots = dots
    s.cols = cols
    s.rows = rows
  }

  /**
   * 单帧推进：弹簧回归 + 鼠标排斥 + 阻尼，返回本帧最大速度（用于自动暂停判断）。
   */
  function stepPhysics(s) {
    const P = DOT_GRID_PARAMS
    let maxSpeed = 0
    for (const d of s.dots) {
      // 弹簧回归
      d.vx += (d.baseX - d.x) * P.spring
      d.vy += (d.baseY - d.y) * P.spring
      // 鼠标排斥（线性衰减）
      const dx = d.x - s.mouse.x
      const dy = d.y - s.mouse.y
      const dist = Math.hypot(dx, dy)
      if (dist < P.repulsionRadius && dist > 0.001) {
        const t = 1 - dist / P.repulsionRadius
        const f = t * P.repulsionMax
        d.vx += (dx / dist) * f
        d.vy += (dy / dist) * f
      }
      d.vx *= P.damping
      d.vy *= P.damping
      d.x += d.vx
      d.y += d.vy
      const sp = Math.abs(d.vx) + Math.abs(d.vy)
      if (sp > maxSpeed) maxSpeed = sp
    }
    return maxSpeed
  }

  /**
   * 绘制：先连线（底层）、再画点（上层）；靠近鼠标的点放大提亮。
   */
  function draw(s) {
    const P = DOT_GRID_PARAMS
    const ctx = s.ctx
    ctx.clearRect(0, 0, s.w, s.h)

    // 相邻点连线（右邻 + 下邻）
    ctx.strokeStyle = `rgba(255, 255, 255, ${P.lineAlpha})`
    ctx.lineWidth = 1
    ctx.beginPath()
    for (const d of s.dots) {
      const right = s.dots[d.row * s.cols + d.col + 1]
      const bottom = s.dots[(d.row + 1) * s.cols + d.col]
      if (d.col + 1 < s.cols && right) {
        ctx.moveTo(d.x, d.y)
        ctx.lineTo(right.x, right.y)
      }
      if (d.row + 1 < s.rows && bottom) {
        ctx.moveTo(d.x, d.y)
        ctx.lineTo(bottom.x, bottom.y)
      }
    }
    ctx.stroke()

    // 点
    for (const d of s.dots) {
      const dist = Math.hypot(d.x - s.mouse.x, d.y - s.mouse.y)
      let t = 0
      if (dist < P.repulsionRadius) t = 1 - dist / P.repulsionRadius
      const r = P.dotRadius + t * (P.nearMouseRadius - P.dotRadius)
      const a = P.dotAlpha + t * (P.nearMouseAlpha - P.dotAlpha)
      ctx.fillStyle = `rgba(255, 255, 255, ${a})`
      ctx.beginPath()
      ctx.arc(d.x, d.y, r, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  function start() {
    if (state) return // 幂等
    const canvas = canvasRef.value
    if (!canvas) return

    const P = DOT_GRID_PARAMS
    const s = {
      ctx: null,
      w: 0,
      h: 0,
      dots: [],
      cols: 0,
      rows: 0,
      mouse: { x: -1e4, y: -1e4 },
      isTouch: false,
      raf: 0,
      lastTime: 0,
      paused: false,
      io: null,
      ro: null,
      destroyed: false,
    }
    state = s

    s.ctx = canvas.getContext('2d')
    if (!s.ctx) return

    // 触屏设备（无 hover）禁用鼠标扰动
    s.isTouch = window.matchMedia('(hover: none)').matches

    function resize() {
      const rect = canvas.getBoundingClientRect()
      s.w = Math.max(1, rect.width)
      s.h = Math.max(1, rect.height)
      const dpr = Math.min(window.devicePixelRatio || 1, P.maxDpr)
      canvas.width = Math.round(s.w * dpr)
      canvas.height = Math.round(s.h * dpr)
      s.ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      buildGrid(s)
    }

    function onPointerMove(e) {
      if (s.isTouch || s.destroyed) return
      const rect = canvas.getBoundingClientRect()
      s.mouse.x = e.clientX - rect.left
      s.mouse.y = e.clientY - rect.top
      // 自动暂停后由鼠标移动唤醒
      if (s.paused) {
        s.paused = false
        s.lastTime = performance.now()
        s.raf = requestAnimationFrame(frame)
      }
    }

    function onPointerLeave() {
      if (s.isTouch) return
      s.mouse.x = -1e4
      s.mouse.y = -1e4
    }

    function frame(now) {
      if (s.destroyed) return
      s.raf = requestAnimationFrame(frame)
      // 30fps 节流
      if (now - s.lastTime < 1000 / P.fps) return
      s.lastTime = now

      const maxSpeed = stepPhysics(s)
      draw(s)

      // 自动暂停：全部点趋于静止且鼠标不在附近时停掉 RAF
      if (maxSpeed < P.idleSpeed) {
        s.paused = true
        cancelAnimationFrame(s.raf)
        s.raf = 0
      }
    }

    // IntersectionObserver：离开视口暂停，进入恢复
    s.io = new IntersectionObserver((entries) => {
      if (s.destroyed) return
      const visible = entries[0]?.isIntersecting
      if (visible && s.raf === 0) {
        s.paused = false
        s.lastTime = performance.now()
        s.raf = requestAnimationFrame(frame)
      } else if (!visible && s.raf !== 0) {
        cancelAnimationFrame(s.raf)
        s.raf = 0
      }
    })
    s.io.observe(canvas)

    // 页面隐藏时停帧（IO 多数情况会兜底，此处保险）
    const onVisibility = () => {
      if (s.destroyed) return
      if (document.hidden && s.raf !== 0) {
        cancelAnimationFrame(s.raf)
        s.raf = 0
      } else if (!document.hidden && s.raf === 0) {
        s.paused = false
        s.lastTime = performance.now()
        s.raf = requestAnimationFrame(frame)
      }
    }
    document.addEventListener('visibilitychange', onVisibility)

    s.ro = new ResizeObserver(resize)
    s.ro.observe(canvas)

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
      s.dots = []
      state = null
    }

    resize()
    running.value = true
    s.lastTime = performance.now()
    s.raf = requestAnimationFrame(frame)
  }

  function stop() {
    if (state && state._destroy) state._destroy()
    running.value = false
  }

  return { running, start, stop }
}

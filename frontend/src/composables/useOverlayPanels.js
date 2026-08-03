// Monitor3D 覆盖层可拖拽状态（item 946 切片 7）
// 从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
// 必须由父组件单次调用：reset_panels=1 的 URL 处理会 history.replaceState 清掉参数，
// 若每个面板各自调用 composable，第二个实例找不到参数、其位置不会被重置。
import { ref, reactive } from 'vue'

// 面板可拖拽位置（原 Monitor3D.vue 667-766，HEADER_H 为死代码已丢弃）

function loadPanelPos(key, defaultX, defaultY) {
  try {
    const saved = localStorage.getItem('monitor3d_panel_' + key)
    if (saved) return JSON.parse(saved)
  } catch {}
  return { x: defaultX, y: defaultY }
}
function savePanelPos(key, pos) {
  localStorage.setItem('monitor3d_panel_' + key, JSON.stringify({ x: pos.x, y: pos.y }))
}
const SNMP_PANEL_W = 260
const HEAT_PANEL_W = 188
const PANEL_MARGIN = 120  // 面板至少保留120px在视口内

/** 将面板位置限制在视口范围内 */
function clampPanelPos(pos, panelW) {
  const ww = window.innerWidth
  const wh = window.innerHeight
  // X：至少保留 60px 可见
  pos.x = Math.max(-(panelW - 60), Math.min(ww - 60, pos.x))
  // Y（bottom）：不超出底部，且至少 PANEL_MARGIN 在视口内
  pos.y = Math.max(0, Math.min(wh - PANEL_MARGIN, pos.y))
}

/** 若保存的位置已偏移到难以操作的范围，直接回退到默认值 */
function resetPanelIfOob(pos, panelW, defaultX, defaultY) {
  const ww = window.innerWidth
  const wh = window.innerHeight
  const maxY = wh - PANEL_MARGIN
  const maxX = ww - 60
  const minX = -(panelW - 60)
  if (pos.y < 0 || pos.y > maxY || pos.x < minX || pos.x > maxX) {
    pos.x = defaultX
    pos.y = defaultY
  }
}

export function useOverlayPanels() {
  const showSnmpHealth = ref(true)
  const showHeatLegend = ref(true)

  const snmpPos = reactive(loadPanelPos('snmp', 16, 200))
  const heatPos = reactive(loadPanelPos('heat', 16, 16))
  // 支持 ?reset_panels=1 强制重置面板到底部
  if (window.location.search.includes('reset_panels=1')) {
    localStorage.removeItem('monitor3d_panel_snmp')
    localStorage.removeItem('monitor3d_panel_heat')
    snmpPos.x = 16; snmpPos.y = 200
    heatPos.x = 16; heatPos.y = 16
    const url = new URL(window.location)
    url.searchParams.delete('reset_panels')
    window.history.replaceState({}, '', url)
  }
  // 加载后检查，如果位置超出可操作范围则重置
  resetPanelIfOob(snmpPos, SNMP_PANEL_W, 16, 200)
  resetPanelIfOob(heatPos, HEAT_PANEL_W, 16, 16)
  clampPanelPos(snmpPos, SNMP_PANEL_W)
  clampPanelPos(heatPos, HEAT_PANEL_W)

  let panelDragState = null

  function startDrag(e, pos, panelW) {
    e.preventDefault()
    panelDragState = {
      pos,
      panelW,
      startX: e.clientX,
      startY: e.clientY,
      origX: pos.x,
      origY: pos.y,
    }
    document.addEventListener('mousemove', onPanelDragMove)
    document.addEventListener('mouseup', onPanelDragEnd)
  }

  function onPanelDragMove(e) {
    if (!panelDragState) return
    const { pos, panelW, startX, startY, origX, origY } = panelDragState
    pos.x = origX + (e.clientX - startX)
    pos.y = origY - (e.clientY - startY)
    clampPanelPos(pos, panelW)
  }

  function onPanelDragEnd() {
    document.removeEventListener('mousemove', onPanelDragMove)
    document.removeEventListener('mouseup', onPanelDragEnd)
    if (panelDragState) {
      savePanelPos('snmp', snmpPos)
      savePanelPos('heat', heatPos)
      panelDragState = null
    }
  }

  function toggleSnmpHealth() {
    showSnmpHealth.value = !showSnmpHealth.value
    clampPanelPos(snmpPos, SNMP_PANEL_W)
  }
  function toggleHeatLegend() {
    showHeatLegend.value = !showHeatLegend.value
    clampPanelPos(heatPos, HEAT_PANEL_W)
  }

  return {
    snmpPos,
    heatPos,
    showSnmpHealth,
    showHeatLegend,
    startDrag,
    toggleSnmpHealth,
    toggleHeatLegend,
    SNMP_PANEL_W,
    HEAT_PANEL_W,
  }
}

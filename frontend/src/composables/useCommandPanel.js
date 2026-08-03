// Monitor3D 指挥面板状态（item 946 切片 8）
// 从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
// 父侧单实例调用：commandSummary 被场景 buildImpactGlow 共享；getPlanId 惰性取 currentPlanId。
import { ref } from 'vue'
import { authenticatedAxios as axios } from '@/api/request.js'

export function useCommandPanel(getPlanId) {
  const commandSummary = ref({ recent_events: [] })
  const monitorEvents = ref([])
  const eventWindow = ref('1h')

  async function loadCommandSummary() {
    try {
      const res = await axios.get('/api/monitor3d/command-summary', {
        params: getPlanId() ? { plan_id: getPlanId() } : {},
      })
      commandSummary.value = res.data || { recent_events: [] }
    } catch (e) {
      console.warn('加载故障指挥汇总失败:', e)
    }
  }

  async function loadMonitorEvents() {
    try {
      const res = await axios.get('/api/monitor3d/events', {
        params: { window: eventWindow.value, limit: 80 },
      })
      monitorEvents.value = res.data.items || []
    } catch (e) {
      console.warn('加载故障事件流失败:', e)
    }
  }

  function setEventWindow(windowValue) {
    eventWindow.value = windowValue
    loadMonitorEvents()
  }

  return { commandSummary, monitorEvents, eventWindow, loadCommandSummary, loadMonitorEvents, setEventWindow }
}

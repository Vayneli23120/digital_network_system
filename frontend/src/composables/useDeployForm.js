// Deploy 视图配置表单逻辑（item 946 切片 4）
// 从 frontend/src/views/Deploy.vue 拆分，行为与原实现完全一致。
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from '@/composables/useI18n'
import {
  getDevices,
  getBackups,
  getTemplates,
  getTemplate,
  getCompatibleVariables
} from '@/api'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import { stampUid } from '@/utils/uid.js'

export function useDeployForm() {
  const { t } = useI18n()

  // 执行模式控制
  const executionMode = ref('serial')  // serial | parallel
  const parallelLimit = ref(1)  // 并行数量，建议不超过3

  // 数据
  const devices = ref([])
  const backups = ref([])
  const templates = ref([])
  const allVariables = ref([])
  const availableVariables = ref([])
  const loading = ref(false)

  // 表单
  const deployForm = ref({
    mode: 'backup',
    engine: 'netmiko',  // napalm | netmiko，默认 netmiko（无需 SCP）
    napalm_mode: 'merge',  // merge | replace，默认 merge
    transfer_mode: 'inline',  // scp | inline，默认 inline（短配置适用，无需 SCP）
    backup_file: '',
    template_id: '',
    snippet: '',
    snippet_position: 'smart',
    base_backup_file: '',
    target_devices: [],
    variables: [],
    dry_run: false
  })

  // 计算属性
  const canDeploy = computed(() => {
    if (deployForm.value.target_devices.length === 0) return false
    if (deployForm.value.mode === 'backup') {
      return !!deployForm.value.backup_file
    }
    if (deployForm.value.mode === 'snippet') {
      return !!deployForm.value.snippet.trim()
    }
    return !!deployForm.value.template_id
  })

  // 加载数据
  const loadDevices = debounce(async (force = false) => {
    try {
      const data = await cachedRequest(
        () => getDevices(),
        'devices',
        {},
        { forceRefresh: force }
      )
      devices.value = data.items || []
    } catch (error) {
      if (error.name !== 'CanceledError') {
        ElMessage.error(t('deployLoadDeviceFailed'))
      }
    }
  }, 300)

  const loadBackups = debounce(async (force = false) => {
    try {
      const data = await cachedRequest(
        () => getBackups({ limit: 50 }),
        'backups',
        { limit: 50 },
        { forceRefresh: force }
      )
      backups.value = data.items || []
    } catch (error) {
      if (error.name !== 'CanceledError') {
        ElMessage.error(t('deployLoadBackupFailed'))
      }
    }
  }, 300)

  const loadTemplates = debounce(async (force = false) => {
    try {
      const data = await cachedRequest(
        () => getTemplates(),
        'templates',
        {},
        { forceRefresh: force }
      )
      templates.value = data.items || []
    } catch (error) {
      if (error.name !== 'CanceledError') {
        ElMessage.error(t('deployLoadTemplateFailed'))
      }
    }
  }, 300)

  const loadCompatibleVariables = async () => {
    try {
      const data = await cachedRequest(
        () => getCompatibleVariables(),
        'compatibleVariables',
        {},
        { ttl: 300000 }  // 缓存 5 分钟
      )
      allVariables.value = data.variables || []
    } catch (error) {
      // Silent fail
    }
  }

  const loadTemplateVariables = async (templateId) => {
    if (!templateId) {
      availableVariables.value = []
      deployForm.value.variables = []
      return
    }

    try {
      const data = await cachedRequest(
        () => getTemplate(templateId),
        'template',
        { id: templateId },
        { ttl: 60000 }  // 缓存 1 分钟
      )
      if (data.variables) {
        try {
          let vars = typeof data.variables === 'string'
            ? JSON.parse(data.variables)
            : data.variables

          // 处理两种格式：
          // 1. 对象格式: {"hostname": "SW-Office", "domain": "local"}
          // 2. 数组格式: [{key: "hostname", default: "SW-Office"}]
          if (vars && typeof vars === 'object' && !Array.isArray(vars)) {
            // 对象格式转为数组
            vars = Object.entries(vars).map(([key, value]) => ({
              key: key,
              default: typeof value === 'object' ? value.default || '' : value,
              description: typeof value === 'object' ? value.description || '' : ''
            }))
          }

          availableVariables.value = vars || []
          deployForm.value.variables = (vars || []).map(v => stampUid({
            key: v.key,
            value: v.default || ''
          }))
        } catch (e) {
          console.error('Parse template variables failed:', e)
          deployForm.value.variables = []
        }
      } else {
        deployForm.value.variables = []
      }
    } catch (error) {
      ElMessage.error(t('deployLoadTemplateVarFailed'))
    }
  }

  // 监听部署模式变化，模板和备份模式只支持 Netmiko
  watch(() => deployForm.value.mode, (newMode) => {
    if ((newMode === 'template' || newMode === 'backup') && deployForm.value.engine === 'napalm') {
      deployForm.value.engine = 'netmiko'
    }
  })

  return {
    deployForm,
    executionMode,
    parallelLimit,
    devices,
    backups,
    templates,
    allVariables,
    availableVariables,
    loading,
    canDeploy,
    loadDevices,
    loadBackups,
    loadTemplates,
    loadCompatibleVariables,
    loadTemplateVariables
  }
}

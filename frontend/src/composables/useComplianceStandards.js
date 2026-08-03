// Compliance 标准文档列表状态与请求（item 946 切片 2）
// 从 frontend/src/views/Compliance.vue 拆分，行为与原实现完全一致。
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getStandards, deleteStandard as deleteStandardApi, generateRulesForStandard } from '@/api'
import { debounce } from '@/utils/requestManager.js'
import { useI18n } from '@/composables/useI18n'

export function useComplianceStandards() {
  const { t } = useI18n()

  const standards = ref([])
  const standardsLoading = ref(false)
  const currentStandardId = ref(null)
  const generatingRules = ref(false)

  // 加载标准文档列表
  const loadStandards = debounce(async (force = false) => {
    standardsLoading.value = true
    try {
      const data = await getStandards()
      standards.value = data.standards || []
    } catch (e) {
      ElMessage.error(t('loadFailed'))
    } finally {
      standardsLoading.value = false
    }
  }, 300)

  // 生成规则
  const generateRules = async (standardId) => {
    generatingRules.value = true
    try {
      const data = await generateRulesForStandard(standardId)
      if (data.success) {
        ElMessage.success(`${t('complianceRulesGenerated')}: ${data.generated_count} rules`)
        loadStandards()
      } else {
        ElMessage.error(t('complianceRulesGenerateFailed') + ': ' + data.error)
      }
    } catch (e) {
      ElMessage.error(t('complianceRulesGenerateFailed'))
    } finally {
      generatingRules.value = false
    }
  }

  // 删除标准文档
  const deleteStandard = async (standardId) => {
    try {
      await ElMessageBox.confirm(t('confirmDelete'), t('warning'), { type: 'warning' })
      await deleteStandardApi(standardId)
      ElMessage.success(t('deleteSuccess'))
      loadStandards()
    } catch (e) {
      if (e !== 'cancel') {
        ElMessage.error(t('deleteFailed'))
      }
    }
  }

  return {
    standards,
    standardsLoading,
    currentStandardId,
    generatingRules,
    loadStandards,
    generateRules,
    deleteStandard
  }
}

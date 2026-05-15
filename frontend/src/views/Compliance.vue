<template>
  <div class="compliance">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('complianceTitle') }}</span>
          <el-button type="primary" @click="showCheckDialog">{{ t('complianceRunCheck') }}</el-button>
        </div>
      </template>

      <!-- 检查项列表 -->
      <el-table :data="checkItems" stripe border v-loading="loading">
        <el-table-column prop="id" :label="t('complianceCheckItem')" width="100" />
        <el-table-column prop="name" :label="t('complianceName')" width="200" />
        <el-table-column prop="category" :label="t('complianceCategory')" width="120">
          <template #default="{ row }">
            <el-tag :type="categoryType(row.category)">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" :label="t('complianceSeverity')" width="120">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 最近检查结果 -->
      <el-divider />
      <h3>{{ t('complianceRecentResults') }}</h3>
      <el-empty v-if="!report" :description="t('complianceNotRunYet')" />
      <template v-else>
        <el-row :gutter="16" class="stats-row">
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic :title="t('complianceTotalChecks')" :value="report.total_checks" />
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic :title="t('compliancePassed')" :value="report.passed" value-style="color: #67C23A" />
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic :title="t('complianceFailed')" :value="report.failed" value-style="color: #F56C6C" />
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic :title="t('complianceScore')" :suffix="'%'" :value="report.compliance_score" />
            </el-card>
          </el-col>
        </el-row>

        <el-table :data="report.results" stripe border>
          <el-table-column prop="check_id" label="ID" width="100" />
          <el-table-column prop="check_name" :label="t('complianceCheckItem')" width="200" />
          <el-table-column prop="category" :label="t('complianceCategory')" width="120" />
          <el-table-column prop="severity" :label="t('complianceLevel')" width="100">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('complianceResult')" width="80">
            <template #default="{ row }">
              <el-tag :type="row.passed ? 'success' : 'danger'">{{ row.passed ? t('compliancePassStatus') : t('complianceFailStatus') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" :label="t('complianceDetail')" />
          <el-table-column prop="recommendation" :label="t('complianceRecommendation')" />
        </el-table>
      </template>
    </el-card>

    <!-- 运行检查对话框 -->
    <el-dialog v-model="checkDialogVisible" :title="t('complianceRunDialogTitle')" width="600px" append-to-body draggable align-center class="compliance-dialog">
      <el-form :model="checkForm" label-width="90px" size="default">
        <!-- 设备信息 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Connection /></el-icon>
            <span>{{ t('complianceDeviceSection') }}</span>
          </div>
          <el-form-item :label="t('complianceDeviceName')" required>
            <el-input v-model="checkForm.device_name" />
          </el-form-item>
          <el-form-item :label="t('complianceDeviceIp')">
            <el-input v-model="checkForm.device_ip" />
          </el-form-item>
        </div>

        <!-- 配置内容 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <span>{{ t('complianceConfigSection') }}</span>
          </div>
          <el-form-item :label="t('complianceConfigText')" required>
            <el-input v-model="checkForm.config_text" type="textarea" :rows="10" :placeholder="t('complianceConfigPlaceholder')" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="checkDialogVisible = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="runCheck" :loading="checking">{{ t('complianceRunCheck') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Document } from '@element-plus/icons-vue'
import { getCheckItems, runComplianceCheck } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

const checkItems = ref([])
const report = ref(null)
const checkDialogVisible = ref(false)
const checking = ref(false)
const loading = ref(false)
const checkForm = reactive({ device_name: '', device_ip: '', config_text: '' })

const categoryType = (cat) => ({ security: 'danger', availability: 'warning', compliance: 'info' }[cat] || '')
const severityType = (sev) => ({ critical: 'danger', high: 'warning', medium: 'info', low: '' }[sev] || '')

const loadChecks = debounce(async (force = false) => {
  loading.value = true
  try {
    const { data } = await cachedRequest(
      () => getCheckItems(),
      'complianceCheckItems',
      {},
      { forceRefresh: force }
    )
    checkItems.value = data
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('complianceLoadCheckItemsFailed') + '：' + (e.response?.data?.detail || e.message))
    }
  } finally {
    loading.value = false
  }
}, 300)

const showCheckDialog = () => {
  checkForm.device_name = ''
  checkForm.device_ip = ''
  checkForm.config_text = ''
  checkDialogVisible.value = true
}

const runCheck = async () => {
  checking.value = true
  try {
    const { data } = await runComplianceCheck(checkForm)
    report.value = data
    ElMessage.success(`${t('complianceCheckComplete')}: ${data.compliance_score}%`)
    checkDialogVisible.value = false
  } catch (e) {
    ElMessage.error(t('complianceCheckFailed'))
  } finally {
    checking.value = false
  }
}

onMounted(loadChecks)
</script>

<style scoped>
.stats-row { margin: var(--gap-md) 0; }

/* 对话框样式 */
.compliance-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}
.compliance-dialog .section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}
.compliance-dialog .section-header .el-icon {
  color: var(--accent-primary);
}
.compliance-dialog .el-form-item {
  margin-bottom: 10px;
}

/* 暗黑模式 */
.dark .compliance-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}
.dark .compliance-dialog .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}
.dark .compliance-dialog .section-header .el-icon {
  color: #58a6ff;
}
</style>

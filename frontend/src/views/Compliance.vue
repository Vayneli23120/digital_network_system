<template>
  <div class="compliance">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>配置合规检查</span>
          <el-button type="primary" @click="showCheckDialog">运行检查</el-button>
        </div>
      </template>

      <!-- 检查项列表 -->
      <el-table :data="checkItems" stripe border>
        <el-table-column prop="id" label="检查项" width="100" />
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag :type="categoryType(row.category)">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重级别" width="120">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 最近检查结果 -->
      <el-divider />
      <h3>最近检查结果</h3>
      <el-empty v-if="!report" description="尚未运行检查" />
      <template v-else>
        <el-row :gutter="16" class="stats-row">
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic title="总检查项" :value="report.total_checks" />
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic title="通过" :value="report.passed" value-style="color: #67C23A" />
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic title="未通过" :value="report.failed" value-style="color: #F56C6C" />
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover">
              <el-statistic title="合规分数" :suffix="'%'" :value="report.compliance_score" />
            </el-card>
          </el-col>
        </el-row>

        <el-table :data="report.results" stripe border>
          <el-table-column prop="check_id" label="ID" width="100" />
          <el-table-column prop="check_name" label="检查项" width="200" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="severity" label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="row.passed ? 'success' : 'danger'">{{ row.passed ? '通过' : '未通过' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" label="详情" />
          <el-table-column prop="recommendation" label="建议" />
        </el-table>
      </template>
    </el-card>

    <!-- 运行检查对话框 -->
    <el-dialog v-model="checkDialogVisible" title="运行合规检查" width="600px">
      <el-form :model="checkForm" label-width="100px">
        <el-form-item label="设备名称" required>
          <el-input v-model="checkForm.device_name" />
        </el-form-item>
        <el-form-item label="设备 IP">
          <el-input v-model="checkForm.device_ip" />
        </el-form-item>
        <el-form-item label="配置文本" required>
          <el-input v-model="checkForm.config_text" type="textarea" :rows="10" placeholder="粘贴设备 show running-config 输出" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="checkDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="runCheck" :loading="checking">运行检查</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCheckItems, runComplianceCheck } from '@/api'

const checkItems = ref([])
const report = ref(null)
const checkDialogVisible = ref(false)
const checking = ref(false)
const checkForm = reactive({ device_name: '', device_ip: '', config_text: '' })

const categoryType = (cat) => ({ security: 'danger', availability: 'warning', compliance: 'info' }[cat] || '')
const severityType = (sev) => ({ critical: 'danger', high: 'warning', medium: 'info', low: '' }[sev] || '')

const loadChecks = async () => {
  try {
    const { data } = await getCheckItems()
    checkItems.value = data
  } catch (e) {
    console.error(e)
  }
}

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
    ElMessage.success(`检查完成，合规分数: ${data.compliance_score}%`)
    checkDialogVisible.value = false
  } catch (e) {
    ElMessage.error('检查失败')
  } finally {
    checking.value = false
  }
}

onMounted(loadChecks)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.stats-row { margin: 16px 0; }
</style>

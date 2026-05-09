<template>
  <div class="workflows-page">
    <!-- Header -->
    <div class="page-header">
      <h2>{{ $t('workflow.title') || '自动化工作流' }}</h2>
      <div class="header-actions">
        <el-button type="primary" @click="createRuleDialog">
          <el-icon><Plus /></el-icon>
          {{ $t('workflow.createRule') || '创建规则' }}
        </el-button>
        <el-button @click="initDefaultRules" :loading="initing">
          {{ $t('workflow.initDefaults') || '初始化默认规则' }}
        </el-button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ stats.total_rules || 0 }}</div>
            <div class="stat-label">{{ $t('workflow.totalRules') || '总规则数' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card success">
            <div class="stat-value">{{ stats.active_rules || 0 }}</div>
            <div class="stat-label">{{ $t('workflow.activeRules') || '活跃规则' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card info">
            <div class="stat-value">{{ stats.total_executions || 0 }}</div>
            <div class="stat-label">{{ $t('workflow.totalExecutions') || '总执行次数' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card warning">
            <div class="stat-value">{{ Object.keys(stats.by_trigger_type || {}).length }}</div>
            <div class="stat-label">{{ $t('workflow.triggerTypes') || '触发类型' }}</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Trigger & Action Types -->
    <div class="types-section">
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="types-card">
            <div class="card-title">{{ $t('workflow.availableTriggers') || '可用触发类型' }}</div>
            <div class="types-list">
              <div v-for="(desc, type) in triggerTypes.trigger_info" :key="type" class="type-item">
                <el-tag type="info" size="small">{{ type }}</el-tag>
                <span class="type-desc">{{ desc }}</span>
              </div>
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="types-card">
            <div class="card-title">{{ $t('workflow.availableActions') || '可用动作类型' }}</div>
            <div class="types-list">
              <div v-for="(desc, type) in actionTypes.action_info" :key="type" class="type-item">
                <el-tag type="success" size="small">{{ type }}</el-tag>
                <span class="type-desc">{{ desc }}</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Rules Table -->
    <div class="rules-section">
      <div class="section-header">
        <h3>{{ $t('workflow.rulesList') || '规则列表' }}</h3>
        <el-select v-model="triggerFilter" placeholder="触发类型筛选" clearable style="width: 180px">
          <el-option v-for="t in triggerTypes.triggers" :key="t" :label="t" :value="t" />
        </el-select>
      </div>

      <el-table :data="filteredRules" style="width: 100%" v-loading="loading">
        <el-table-column prop="priority" label="优先级" width="80" sortable />
        <el-table-column prop="name" label="规则名称" width="200" />
        <el-table-column prop="trigger_type" label="触发类型" width="150">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.trigger_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_conditions" label="触发条件" min-width="200">
          <template #default="{ row }">
            <code class="condition-code">{{ JSON.stringify(row.trigger_conditions) }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="action_type" label="执行动作" width="150">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.action_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="execution_count" label="执行次数" width="100" />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" @change="toggleRule(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="last_triggered_at" label="最后触发" width="160">
          <template #default="{ row }">
            {{ formatTime(row.last_triggered_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="editRule(row)">编辑</el-button>
            <el-button type="danger" size="small" link @click="deleteRule(row)">删除</el-button>
            <el-button type="info" size="small" link @click="testRule(row)">测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create/Edit Rule Dialog -->
    <el-dialog v-model="ruleDialogVisible" :title="editingRule ? '编辑规则' : '创建规则'" width="700px">
      <el-form :model="ruleForm" label-width="120px">
        <el-form-item label="规则名称" required>
          <el-input v-model="ruleForm.name" placeholder="输入规则名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="ruleForm.description" type="textarea" placeholder="规则描述" />
        </el-form-item>
        <el-form-item label="触发类型" required>
          <el-select v-model="ruleForm.trigger_type" placeholder="选择触发类型" style="width: 100%">
            <el-option v-for="t in triggerTypes.triggers" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发条件">
          <el-input
            v-model="ruleForm.trigger_conditions_json"
            type="textarea"
            :rows="4"
            placeholder="JSON格式触发条件，如: {&quot;health_score&quot;: {&quot;&lt;&quot;: 60}}"
          />
          <div class="form-tip">示例：{"health_score": {"<": 60}} 或 {"severity": "critical"}</div>
        </el-form-item>
        <el-form-item label="动作类型" required>
          <el-select v-model="ruleForm.action_type" placeholder="选择动作类型" style="width: 100%">
            <el-option v-for="a in actionTypes.actions" :key="a" :label="a" :value="a" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作配置">
          <el-input
            v-model="ruleForm.action_config_json"
            type="textarea"
            :rows="4"
            placeholder="JSON格式动作配置"
          />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="ruleForm.priority" :min="1" :max="1000" />
          <div class="form-tip">数字越小优先级越高</div>
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="ruleForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRule" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- Test Result Dialog -->
    <el-dialog v-model="testDialogVisible" title="测试结果" width="600px">
      <div v-if="testResult" class="test-result">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="触发类型">{{ testResult.trigger_type }}</el-descriptions-item>
          <el-descriptions-item label="匹配规则数">{{ testResult.rules_matched_count }}</el-descriptions-item>
          <el-descriptions-item label="执行动作数">{{ testResult.actions_count }}</el-descriptions-item>
          <el-descriptions-item label="执行状态">
            <el-tag :type="testResult.success ? 'success' : 'danger'">
              {{ testResult.success ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="testResult.actions_executed?.length > 0" class="actions-result">
          <h4>执行结果</h4>
          <div v-for="(action, idx) in testResult.actions_executed" :key="idx" class="action-item">
            <el-tag :type="action.success ? 'success' : 'danger'" size="small">
              {{ action.action }}
            </el-tag>
            <span>{{ action.message || action.error || '完成' }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/api/request'

// Data
const loading = ref(false)
const saving = ref(false)
const initing = ref(false)
const rules = ref([])
const stats = ref({})
const triggerTypes = ref({})
const actionTypes = ref({})
const triggerFilter = ref('')
const ruleDialogVisible = ref(false)
const testDialogVisible = ref(false)
const editingRule = ref(null)
const testResult = ref(null)

// Form
const ruleForm = ref({
  name: '',
  description: '',
  trigger_type: '',
  trigger_conditions_json: '',
  action_type: '',
  action_config_json: '',
  priority: 100,
  is_active: true
})

// Computed
const filteredRules = computed(() => {
  if (!triggerFilter.value) return rules.value
  return rules.value.filter(r => r.trigger_type === triggerFilter.value)
})

// Methods
const fetchRules = async () => {
  try {
    loading.value = true
    const res = await api.get('/workflows/rules')
    rules.value = res.rules || []
  } catch (error) {
    console.error('Failed to fetch rules:', error)
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await api.get('/workflows/stats')
    stats.value = res.rules || {}
    triggerTypes.value = { triggers: res.triggers_available || [], trigger_info: {} }
    actionTypes.value = { actions: res.actions_available || [], action_info: {} }
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

const fetchTriggerTypes = async () => {
  try {
    const res = await api.get('/workflows/triggers')
    triggerTypes.value = res
  } catch (error) {
    console.error('Failed to fetch trigger types:', error)
  }
}

const fetchActionTypes = async () => {
  try {
    const res = await api.get('/workflows/actions')
    actionTypes.value = res
  } catch (error) {
    console.error('Failed to fetch action types:', error)
  }
}

const initDefaultRules = async () => {
  try {
    initing.value = true
    const res = await api.post('/workflows/init-defaults')
    ElMessage.success(`初始化完成: ${res.created_count} 条规则`)
    await fetchRules()
    await fetchStats()
  } catch (error) {
    ElMessage.error('初始化失败')
    console.error(error)
  } finally {
    initing.value = false
  }
}

const toggleRule = async (rule) => {
  try {
    const res = await api.patch(`/workflows/rules/${rule.id}/toggle`)
    rule.is_active = res.is_active
    ElMessage.success(res.is_active ? '规则已启用' : '规则已禁用')
  } catch (error) {
    ElMessage.error('操作失败')
    console.error(error)
  }
}

const createRuleDialog = () => {
  editingRule.value = null
  ruleForm.value = {
    name: '',
    description: '',
    trigger_type: '',
    trigger_conditions_json: '',
    action_type: '',
    action_config_json: '',
    priority: 100,
    is_active: true
  }
  ruleDialogVisible.value = true
}

const editRule = (rule) => {
  editingRule.value = rule
  ruleForm.value = {
    name: rule.name,
    description: rule.description || '',
    trigger_type: rule.trigger_type,
    trigger_conditions_json: JSON.stringify(rule.trigger_conditions || {}),
    action_type: rule.action_type,
    action_config_json: JSON.stringify(rule.action_config || {}),
    priority: rule.priority || 100,
    is_active: rule.is_active
  }
  ruleDialogVisible.value = true
}

const saveRule = async () => {
  try {
    // Parse JSON fields
    let triggerConditions = {}
    let actionConfig = {}

    try {
      triggerConditions = JSON.parse(ruleForm.value.trigger_conditions_json || '{}')
    } catch (e) {
      ElMessage.warning('触发条件JSON格式错误')
      return
    }

    try {
      actionConfig = JSON.parse(ruleForm.value.action_config_json || '{}')
    } catch (e) {
      ElMessage.warning('动作配置JSON格式错误')
      return
    }

    saving.value = true

    if (editingRule.value) {
      // Update
      await api.put(`/workflows/rules/${editingRule.value.id}`, {
        name: ruleForm.value.name,
        description: ruleForm.value.description,
        trigger_type: ruleForm.value.trigger_type,
        trigger_conditions: triggerConditions,
        action_type: ruleForm.value.action_type,
        action_config: actionConfig,
        priority: ruleForm.value.priority,
        is_active: ruleForm.value.is_active
      })
      ElMessage.success('规则更新成功')
    } else {
      // Create
      await api.post('/workflows/rules', {
        name: ruleForm.value.name,
        description: ruleForm.value.description,
        trigger_type: ruleForm.value.trigger_type,
        trigger_conditions: triggerConditions,
        action_type: ruleForm.value.action_type,
        action_config: actionConfig,
        priority: ruleForm.value.priority,
        is_active: ruleForm.value.is_active
      })
      ElMessage.success('规则创建成功')
    }

    ruleDialogVisible.value = false
    await fetchRules()
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

const deleteRule = async (rule) => {
  try {
    await ElMessageBox.confirm('确定要删除该规则吗？', '确认删除', {
      type: 'warning'
    })

    await api.delete(`/workflows/rules/${rule.id}`)
    ElMessage.success('删除成功')
    await fetchRules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

const testRule = async (rule) => {
  try {
    // For testing, we need to create a mock event
    let eventData = {}

    if (rule.trigger_type === 'fault_created') {
      eventData = { fault_id: 1 }
    } else if (rule.trigger_type === 'device_health_low') {
      eventData = { device_id: 1 }
    } else if (rule.trigger_type === 'maintenance_completed') {
      eventData = { maintenance_id: 1 }
    }

    const res = await api.post('/workflows/trigger', {
      trigger_type: rule.trigger_type,
      event_data: eventData
    })

    testResult.value = res
    testDialogVisible.value = true
  } catch (error) {
    ElMessage.error('测试失败')
    console.error(error)
  }
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// Lifecycle
onMounted(() => {
  fetchRules()
  fetchStats()
  fetchTriggerTypes()
  fetchActionTypes()
})
</script>

<style scoped>
.workflows-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-section {
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  border: 1px solid #ebeef5;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
}

.stat-card.success .stat-value {
  color: #67c23a;
}

.stat-card.info .stat-value {
  color: #409eff;
}

.stat-card.warning .stat-value {
  color: #e6a23c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.types-section {
  margin-bottom: 20px;
}

.types-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}

.card-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 15px;
}

.types-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.type-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-desc {
  font-size: 12px;
  color: #606266;
}

.rules-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
}

.condition-code {
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.test-result {
  padding: 20px;
}

.actions-result {
  margin-top: 20px;
}

.actions-result h4 {
  margin-bottom: 10px;
  font-size: 14px;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
</style>
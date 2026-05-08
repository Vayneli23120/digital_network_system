<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>出入库记录</span>
        <el-button @click="loadMovements"><el-icon><Refresh /></el-icon> 刷新</el-button>
      </div>
    </template>

    <!-- 筛选工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="filter.keyword"
          placeholder="搜索名称/型号/序列号"
          clearable
          class="search-input"
          @keyup.enter="loadMovements"
          @clear="loadMovements"
        />
        <el-select v-model="filter.movement_type" placeholder="类型" clearable class="type-select" @change="loadMovements">
          <el-option label="入库" value="in" />
          <el-option label="出库" value="out" />
          <el-option label="报废入库" value="scrap_in" />
          <el-option label="报废出库" value="scrap_out" />
        </el-select>
        <el-date-picker
          v-model="filter.start_date"
          type="date"
          placeholder="开始日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          class="date-picker"
          @change="loadMovements"
        />
        <el-date-picker
          v-model="filter.end_date"
          type="date"
          placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          class="date-picker"
          @change="loadMovements"
        />
        <el-input
          v-model="filter.operator"
          placeholder="操作人"
          clearable
          class="operator-input"
          @keyup.enter="loadMovements"
          @clear="loadMovements"
        />
      </div>
      <div class="toolbar-right">
        <el-button size="small" @click="resetFilter">重置</el-button>
        <el-button size="small" type="primary" @click="loadMovements">搜索</el-button>
      </div>
    </div>

    <el-table :data="movements" v-loading="loading" stripe border @row-click="handleRowClick">
      <el-table-column prop="created_at" label="时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="name" label="备件名称" width="130">
        <template #default="{ row }">
          <el-button type="primary" link>{{ row.name || '-' }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="serial_number" label="序列号" width="120">
        <template #default="{ row }">{{ row.serial_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="po_number" label="PO号" width="80">
        <template #default="{ row }">{{ row.po_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="movement_type" label="类型" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="getMovementTypeTag(row.movement_type)" size="small">
            {{ getMovementTypeText(row.movement_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量" width="60" align="right" />
      <el-table-column prop="unit_price" label="单价" width="80">
        <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="设备" width="100">
        <template #default="{ row }">
          <span v-if="row.target_device_name">{{ row.target_device_name }}</span>
          <span v-else-if="row.source_device_name">{{ row.source_device_name }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="原因" min-width="120" show-overflow-tooltip />
    </el-table>
    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="page"
        :page-size="50"
        layout="total, prev, pager, next"
        :total="total"
        @current-change="loadMovements"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getMovements, getMovementDetail } from '@/api'
import { formatDateTime } from '@/utils/time'

const emit = defineEmits(['show-detail'])

const movements = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)

const filter = reactive({
  keyword: '',
  movement_type: '',
  start_date: '',
  end_date: '',
  operator: ''
})

// 出入库类型显示
const getMovementTypeTag = (type) => {
  const tags = { in: 'success', out: 'warning', scrap_in: 'info', scrap_out: 'danger' }
  return tags[type] || ''
}

const getMovementTypeText = (type) => {
  const texts = { in: '入库', out: '出库', scrap_in: '报废入库', scrap_out: '已报废' }
  return texts[type] || type
}

const loadMovements = async () => {
  loading.value = true
  try {
    const params = {
      skip: (page.value - 1) * 50,
      limit: 50,
      keyword: filter.keyword || undefined,
      movement_type: filter.movement_type || undefined,
      start_date: filter.start_date || undefined,
      end_date: filter.end_date || undefined,
      operator: filter.operator || undefined
    }
    const result = await getMovements(params)
    movements.value = result.items || []
    total.value = result.total || 0
  } catch (e) {
    ElMessage.error('加载出入库记录失败')
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  filter.keyword = ''
  filter.movement_type = ''
  filter.start_date = ''
  filter.end_date = ''
  filter.operator = ''
  page.value = 1
  loadMovements()
}

const handleRowClick = async (row) => {
  // 获取完整详情（包含同批次备件清单）
  try {
    const detail = await getMovementDetail(row.id)
    emit('show-detail', detail)
  } catch (e) {
    emit('show-detail', row)  // 失败时使用行数据
  }
}

onMounted(loadMovements)

defineExpose({ loadMovements })
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.search-input {
  width: 200px;
}
.type-select {
  width: 120px;
}
.date-picker {
  width: 140px;
}
.operator-input {
  width: 120px;
}
.toolbar-right {
  display: flex;
  gap: 8px;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
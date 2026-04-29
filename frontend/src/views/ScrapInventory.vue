<template>
  <div class="scrap-inventory-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>报废库存</span>
          <el-button type="primary" @click="loadScrapInventory">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索型号或名称"
          style="width: 220px"
          clearable
          @input="filterScrapItems"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="filterScrapItems"
        />
      </div>

      <el-table :data="filteredScrapItems" style="width: 100%" v-loading="loading">
        <el-table-column prop="part_number" label="型号" width="150" />
        <el-table-column prop="name" label="名称" width="180" />
        <el-table-column prop="quantity" label="数量" width="80">
          <template #default="{ row }">
            <el-tag type="info">{{ row.quantity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120">
          <template #default="{ row }">
            <el-tag type="warning" size="small">{{ row.source || '维修返回' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reference" label="关联维修单" width="150">
          <template #default="{ row }">
            <router-link v-if="row.maint_id" :to="`/maintenance/${row.maint_id}`" class="maint-link">
              {{ row.maint_no || row.reference }}
            </router-link>
            <span v-else>{{ row.reference || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" label="关联设备" width="150" />
        <el-table-column prop="created_at" label="入库时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="备注" min-width="150" />
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @size-change="loadScrapInventory"
          @current-change="loadScrapInventory"
        />
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-item">
            <el-icon class="stat-icon"><Delete /></el-icon>
            <div class="stat-content">
              <span class="stat-value">{{ stats.totalItems }}</span>
              <span class="stat-label">报废件总数</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-item">
            <el-icon class="stat-icon"><Box /></el-icon>
            <div class="stat-content">
              <span class="stat-value">{{ stats.totalQty }}</span>
              <span class="stat-label">总数量</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-item">
            <el-icon class="stat-icon"><Tools /></el-icon>
            <div class="stat-content">
              <span class="stat-value">{{ stats.fromMaintenance }}</span>
              <span class="stat-label">维修返回</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search, Delete, Box, Tools } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const scrapItems = ref([])
const filteredScrapItems = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const searchText = ref('')
const dateRange = ref([])

const stats = ref({
  totalItems: 0,
  totalQty: 0,
  fromMaintenance: 0
})

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

const filterScrapItems = () => {
  let result = [...scrapItems.value]

  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(item =>
      item.part_number?.toLowerCase().includes(search) ||
      item.name?.toLowerCase().includes(search) ||
      item.reference?.toLowerCase().includes(search)
    )
  }

  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(item => {
      const itemTime = dayjs(item.created_at)
      return itemTime.isAfter(startDate) && itemTime.isBefore(endDate)
    })
  }

  filteredScrapItems.value = result
}

const loadScrapInventory = async () => {
  loading.value = true
  try {
    // 查询报废入库记录（limit最大200）
    const res = await fetch(`/api/spare-movements/?movement_type=scrap_in&limit=200`)
    const data = await res.json()

    // 处理数据，关联维修记录
    const items = (data.items || []).map(item => ({
      id: item.id,
      part_id: item.part_id,
      part_number: item.part_number || '未知',
      name: item.name || item.part_number || '未知',
      quantity: item.quantity,
      source: '维修返回',
      reference: item.reference,
      reason: item.reason,
      created_at: item.created_at,
      maint_no: null,
      maint_id: null,
      device_name: null
    }))

    // 尝试从维修记录中获取更多关联信息
    const maintRes = await fetch('/api/maintenance?limit=200')
    const maintData = await maintRes.json()
    const maintenances = maintData.items || []

    // 关联维修单信息
    items.forEach(item => {
      const matchedMaint = maintenances.find(m =>
        m.parts_replaced && m.parts_replaced.includes(item.part_number)
      )
      if (matchedMaint) {
        item.maint_id = matchedMaint.id
        item.maint_no = matchedMaint.maint_no
        item.device_name = matchedMaint.device_name
      }
    })

    scrapItems.value = items
    total.value = items.length

    // 计算统计
    stats.value = {
      totalItems: items.length,
      totalQty: items.reduce((sum, i) => sum + i.quantity, 0),
      fromMaintenance: items.length
    }

    filterScrapItems()
  } catch (error) {
    console.error('加载报废库存失败:', error)
    ElMessage.error('加载报废库存失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadScrapInventory()
})
</script>

<style scoped>
.scrap-inventory-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.maint-link {
  color: #409EFF;
  text-decoration: none;
  font-weight: 500;
}

.maint-link:hover {
  text-decoration: underline;
  color: #66b1ff;
}

.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.stat-card {
  min-height: 80px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  font-size: 32px;
  color: #E6A23C;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}
</style>
<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>{{ t('movementHistory') }}</span>
        <el-button @click="loadMovements"><el-icon><Refresh /></el-icon> {{ t('actionRefresh') }}</el-button>
      </div>
    </template>

    <!-- 篮选工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="filter.keyword"
          :placeholder="t('spareSearchPlaceholder')"
          clearable
          class="search-input"
          @keyup.enter="loadMovements"
          @clear="loadMovements"
        />
        <el-select v-model="filter.movement_type" :placeholder="t('movementType')" clearable class="type-select" @change="loadMovements">
          <el-option :label="t('movementIn')" value="in" />
          <el-option :label="t('movementOut')" value="out" />
          <el-option :label="t('movementScrapIn')" value="scrap_in" />
          <el-option :label="t('movementScrapOut')" value="scrap_out" />
        </el-select>
        <el-date-picker
          v-model="filter.start_date"
          type="date"
          :placeholder="t('dashDays7')"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          class="date-picker"
          @change="loadMovements"
        />
        <el-date-picker
          v-model="filter.end_date"
          type="date"
          :placeholder="t('dashDays30')"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          class="date-picker"
          @change="loadMovements"
        />
        <el-input
          v-model="filter.operator"
          :placeholder="t('movementOperator')"
          clearable
          class="operator-input"
          @keyup.enter="loadMovements"
          @clear="loadMovements"
        />
      </div>
      <div class="toolbar-right">
        <el-button size="small" @click="resetFilter">{{ t('actionReset') }}</el-button>
        <el-button size="small" type="primary" @click="loadMovements">{{ t('actionSearch') }}</el-button>
      </div>
    </div>

    <el-table :data="movements" v-loading="loading" stripe border @row-click="handleRowClick">
      <el-table-column prop="created_at" :label="t('movementTime')" width="160">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="name" :label="t('spareName')" width="130">
        <template #default="{ row }">
          <el-button type="primary" link>{{ row.name || '-' }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="serial_number" :label="t('spareSerialNumber')" width="120">
        <template #default="{ row }">{{ row.serial_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="po_number" :label="t('sparePoNumber')" width="80">
        <template #default="{ row }">{{ row.po_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="movement_type" :label="t('movementType')" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="getMovementTypeTag(row.movement_type)" size="small">
            {{ getMovementTypeText(row.movement_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="quantity" :label="t('spareQuantity')" width="60" align="right" />
      <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="80">
        <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column :label="t('monitorScreenTotalDevices')" width="100">
        <template #default="{ row }">
          <span v-if="row.target_device_name">{{ row.target_device_name }}</span>
          <span v-else-if="row.source_device_name">{{ row.source_device_name }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="reason" :label="t('spareReason')" min-width="120" show-overflow-tooltip />
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
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()
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
  const texts = {
    in: t('movementIn'),
    out: t('movementOut'),
    scrap_in: t('movementScrapIn'),
    scrap_out: t('movementScrapOut')
  }
  return texts[type] || type
}

const loadMovements = debounce(async (force = false) => {
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
    const cacheKey = `movements_${page.value}_${JSON.stringify(params)}`
    const result = await cachedRequest(
      () => getMovements(params),
      cacheKey,
      params,
      { forceRefresh: force }
    )
    movements.value = result.items || []
    total.value = result.total || 0
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('msgLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

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
  try {
    const detail = await cachedRequest(
      () => getMovementDetail(row.id),
      `movement_detail_${row.id}`,
      { id: row.id }
    )
    emit('show-detail', detail)
  } catch (e) {
    if (e.name !== 'CanceledError') {
      emit('show-detail', row)
    }
  }
}

onMounted(loadMovements)

defineExpose({ loadMovements })
</script>

<style scoped>
.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
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
  gap: var(--gap-sm);
}
</style>
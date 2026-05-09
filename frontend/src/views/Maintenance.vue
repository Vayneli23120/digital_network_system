<template>
  <div class="maintenance-page">
    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-header">
        <span class="stats-title">{{ t('maintStatsTitle') }}</span>
        <button class="refresh-btn" @click="loadMaintenances" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
      <div class="stats-grid">
        <!-- 总维修单 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.total }}</div>
            <div class="metric-label">{{ t('maintStatsTotal') }}</div>
          </div>
        </div>
        <!-- 维修中 -->
        <div class="stat-card repairing" @click="filterByStatus('repairing')">
          <div class="card-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.repairing }}</div>
            <div class="metric-label">{{ t('maintStatsRepairing') }}</div>
          </div>
        </div>
        <!-- 待验证 -->
        <div class="stat-card verifying" @click="filterByStatus('verifying')">
          <div class="card-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.verifying }}</div>
            <div class="metric-label">{{ t('maintStatsVerifying') }}</div>
          </div>
        </div>
        <!-- 已完成 -->
        <div class="stat-card completed" @click="filterByStatus('completed')">
          <div class="card-icon">
            <el-icon><SuccessFilled /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.completed }}</div>
            <div class="metric-label">{{ t('maintStatsCompleted') }}</div>
          </div>
        </div>
        <!-- 超时工单 -->
        <div class="stat-card overdue" @click="filterByStatus('overdue')">
          <div class="card-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value danger">{{ stats.overdue }}</div>
            <div class="metric-label">{{ t('maintStatsOverdue') }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 高级筛选工具栏 -->
    <section class="filter-section">
      <div class="filter-toolbar">
        <!-- 搜索框 -->
        <el-input
          v-model="searchText"
          :placeholder="t('maintSearchPlaceholder')"
          class="search-input"
          clearable
          @input="filterMaintenances"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <el-tag
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >{{ t('maintFilterAll') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-created', { active: filterStatus === 'created' }]"
            @click="filterByStatus('created')"
          >{{ t('maintStatusLabelCreated') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-diagnosing', { active: filterStatus === 'diagnosing' }]"
            @click="filterByStatus('diagnosing')"
          >{{ t('maintStatusLabelDiagnosing') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-repairing', { active: filterStatus === 'repairing' }]"
            @click="filterByStatus('repairing')"
          >{{ t('maintStatusLabelRepairing') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-verifying', { active: filterStatus === 'verifying' }]"
            @click="filterByStatus('verifying')"
          >{{ t('maintStatusLabelVerifying') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-completed', { active: filterStatus === 'completed' }]"
            @click="filterByStatus('completed')"
          >{{ t('maintStatusLabelCompleted') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-overdue', { active: filterStatus === 'overdue' }]"
            type="danger"
            @click="filterByStatus('overdue')"
          >{{ t('maintFilterOverdue') }}</el-tag>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-select v-model="filterPriority" :placeholder="t('maintPriority')" clearable style="width: 100px" @change="filterMaintenances">
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
            <el-option label="P4" value="P4" />
          </el-select>
          <el-select v-model="filterMaintType" :placeholder="t('maintType')" clearable style="width: 120px" @change="filterMaintenances">
            <el-option :label="t('maintTypePreventive')" value="preventive" />
            <el-option :label="t('maintTypeCorrective')" value="corrective" />
            <el-option :label="t('maintTypeUpgrade')" value="upgrade" />
            <el-option :label="t('maintTypeEmergency')" value="emergency" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="t('maintDateTo')"
            :start-placeholder="t('maintDateStart')"
            :end-placeholder="t('maintDateEnd')"
            value-format="YYYY-MM-DD"
            style="width: 200px"
            @change="filterMaintenances"
          />
        </div>

        <!-- 新增按钮 -->
        <el-button type="primary" class="add-btn" @click="openAddDialog">
          <el-icon><Plus /></el-icon>
          {{ t('maintAddRecord') }}
        </el-button>
      </div>
    </section>

    <!-- 维修单数据面板 -->
    <section class="data-section">
      <el-table
        :data="filteredMaintenances"
        class="modern-table"
        v-loading="loading"
        :row-class-name="tableRowClassName"
      >
        <!-- 维修单号 -->
        <el-table-column prop="maint_no" :label="t('maintColNo')" width="180">
          <template #default="{ row }">
            <router-link :to="`/maintenance/${row.id}`" class="maint-no-link">
              <span class="maint-no-text">{{ row.maint_no }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column prop="status" :label="t('maintStatusLabel')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)" size="small" class="status-tag">
              {{ row.status_label || getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 优先级 -->
        <el-table-column prop="priority" :label="t('maintPriority')" width="70">
          <template #default="{ row }">
            <el-tag :type="getPriorityColor(row.priority)" size="small" class="priority-tag">
              {{ row.priority || 'P3' }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 设备 -->
        <el-table-column prop="device_name" :label="t('maintColDevice')" width="140" />

        <!-- 负责人 -->
        <el-table-column prop="current_owner" :label="t('maintOwner')" width="100">
          <template #default="{ row }">
            <span class="owner-cell">{{ row.current_owner || t('maintOwnerUnassigned') }}</span>
          </template>
        </el-table-column>

        <!-- 类型 -->
        <el-table-column prop="maint_type" :label="t('maintColType')" width="90">
          <template #default="{ row }">
            <el-tag :type="getMaintTypeType(row.maint_type)" size="small">
              {{ getMaintTypeText(row.maint_type) }}
            </el-tag>
          </template>
        </el-table-column>

        <!-- 进度 -->
        <el-table-column prop="progress_percent" :label="t('maintProgress')" width="100">
          <template #default="{ row }">
            <div class="mini-progress">
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: getProgressPercent(row.status) + '%' }" :class="row.status"></div>
              </div>
              <span class="progress-text">{{ getProgressPercent(row.status) }}%</span>
            </div>
          </template>
        </el-table-column>

        <!-- SLA -->
        <el-table-column prop="sla_remaining" :label="t('maintSlaDeadline')" width="100">
          <template #default="{ row }">
            <div class="sla-cell" :class="{ overdue: isOverdue(row) }">
              <span class="sla-time">{{ row.sla_remaining || '--' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 成本 -->
        <el-table-column prop="total_cost" :label="t('maintColTotalCost')" width="90">
          <template #default="{ row }">
            <span class="cost-value">¥{{ ((row.parts_cost || 0) + (row.labor_cost || 0)).toFixed(2) }}</span>
          </template>
        </el-table-column>

        <!-- 时间 -->
        <el-table-column prop="maint_time" :label="t('maintColTime')" width="140">
          <template #default="{ row }">{{ formatDateTime(row.maint_time || row.created_at) }}</template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('colOperation')" width="140" fixed="right">
          <template #default="{ row }">
            <div class="action-icons">
              <!-- 动态状态推进按钮 -->
              <el-tooltip :content="getActionTooltip(row.status)" placement="top" v-if="getNextAction(row.status)">
                <el-button :type="getActionButtonType(row.status)" link @click="handleStatusAction(row)" class="action-icon action-main">
                  <el-icon><component :is="getActionIcon(row.status)" /></el-icon>
                </el-button>
              </el-tooltip>
              <!-- 查看详情 -->
              <el-tooltip content="查看详情" placement="top">
                <el-button type="primary" link @click="viewDetail(row)" class="action-icon">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <!-- 删除 -->
              <el-tooltip content="删除" placement="top" v-if="row.status !== 'completed'">
                <el-button type="danger" link @click="deleteMaintenance(row)" class="action-icon">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="filteredTotal"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </section>

    <!-- 添加/编辑维修记录对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('maintDialogEdit') : t('maintDialogAdd')" width="1100px" class="edit-maint-dialog">
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Setting /></el-icon>
            {{ t('maintBasicInfo') || '基础信息' }}
          </div>
          <el-form :model="maintForm" label-width="80px">
            <el-form-item :label="t('faultDeviceLabel')" required>
              <el-select v-model="maintForm.device_id" :placeholder="t('maintSelectDevice')" style="width: 100%" :disabled="editMode" filterable>
                <el-option
                  v-for="device in devices"
                  :key="device.id"
                  :label="device.name"
                  :value="device.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('maintType')" required>
              <el-select v-model="maintForm.maint_type" style="width: 200px">
                <el-option :label="t('maintTypePreventiveFull')" value="preventive" />
                <el-option :label="t('maintTypeCorrectiveFull')" value="corrective" />
                <el-option :label="t('maintTypeUpgradeFull')" value="upgrade" />
                <el-option :label="t('maintTypeEmergencyFull')" value="emergency" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>

        <!-- 备件更换 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Box /></el-icon>
            {{ t('maintSparePartsSection') }}
          </div>
          <el-form :model="maintForm" label-width="80px">
            <el-form-item :label="t('maintSparePartsLabel')">
              <div class="spare-parts-section">
                <!-- 扫码功能条 -->
                <div class="scan-action-bar">
                  <el-button type="default" class="scan-btn" @click="openScanDialog">
                    <el-icon><Aim /></el-icon>
                    {{ t('maintScanAddSpare') }}
                  </el-button>
                  <div class="scan-tip-badge">
                    <el-icon><InfoFilled /></el-icon>
                    {{ t('maintScanTip') }}
                  </div>
                </div>

            <!-- 手动搜索添加备件 -->
            <div class="spare-search">
              <el-select
                v-model="selectedSparePart"
                :placeholder="t('maintSpareSearchPlaceholder')"
                filterable
                remote
                :remote-method="searchSpareParts"
                :loading="spareLoading"
                style="width: 100%"
                @change="addSparePartToForm"
                clearable
              >
                <el-option
                  v-for="part in sparePartOptions"
                  :key="part.id"
                  :label="`${part.part_number} - ${part.name}`"
                  :value="part.id"
                  :disabled="part.quantity_in_stock <= 0"
                >
                  <div class="spare-option">
                    <span class="spare-number">{{ part.part_number }}</span>
                    <span class="spare-name">{{ part.name }}</span>
                    <span class="spare-stock" :class="{ low: part.quantity_in_stock <= part.min_quantity }">
                      {{ t('maintSpareStock') }}: {{ part.quantity_in_stock }}
                    </span>
                  </div>
                </el-option>
              </el-select>
              <div class="spare-tip">{{ t('maintSpareSelectTip') }}</div>
            </div>

            <!-- 已选备件列表 -->
            <div class="selected-parts" v-if="maintForm.spare_parts.length > 0">
              <el-table :data="maintForm.spare_parts" size="small" border>
                <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('maintColModel')" width="150" />
                <el-table-column prop="name" :label="t('maintColName')" width="150" />
                <el-table-column prop="quantity" :label="t('maintColQuantity')" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" @change="updatePartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="80">
                  <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="total" :label="t('maintColSubtotal')" width="80">
                  <template #default="{ row }">¥{{ (row.quantity * (row.unit_price || 0)).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column :label="t('colOperation')" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeSparePart($index)">
                      {{ t('actionDelete') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">
                {{ t('maintSpareTotalCost') }}: <span class="total-cost">¥{{ maintForm.parts_cost.toFixed(2) }}</span>
              </div>
            </div>
            <div class="no-parts-tip" v-else>
              <el-icon><InfoFilled /></el-icon>
              <span>{{ t('maintNoSpareTip') }}</span>
            </div>
          </div>
            </el-form-item>
          </el-form>
        </div>

        <!-- 返回件 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><RefreshRight /></el-icon>
            {{ t('maintReturnPartsSection') }}
          </div>
          <el-form :model="maintForm" label-width="80px">
            <el-form-item :label="t('maintReturnPartsLabel')">
              <div class="return-parts-section">
                <!-- 扫码功能条 -->
                <div class="scan-action-bar return">
                  <el-input
                    v-model="returnScanInput"
                    :placeholder="t('maintReturnScanPlaceholder')"
                    style="width: 180px"
                    @keyup.enter="scanReturnPart"
                    clearable
                  >
                    <template #prefix><el-icon><Aim /></el-icon></template>
                  </el-input>
                  <el-button type="default" class="scan-btn" size="small" @click="scanReturnPart" :loading="returnScanLoading">
                    {{ t('spareQuery') }}
                  </el-button>
                  <div class="scan-tip-badge">
                    <el-icon><InfoFilled /></el-icon>
                    {{ t('maintReturnScanTip') }}
                  </div>
                </div>

            <!-- 扫码识别结果（如果找到历史记录） -->
            <div class="return-found-info" v-if="returnFoundInfo">
              <el-card size="small" shadow="never">
                <div class="found-header">
                  <el-tag type="success" size="small">{{ t('maintReturnFoundTag') }}</el-tag>
                  <span>{{ returnFoundInfo.serial_number }}</span>
                </div>
                <el-descriptions :column="3" size="small" border>
                  <el-descriptions-item :label="t('maintColModel')">{{ returnFoundInfo.part_number }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColName')">{{ returnFoundInfo.name }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColUnitPrice')">¥{{ (returnFoundInfo.unit_price || 0).toFixed(2) }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintReturnInStockAt')">{{ returnFoundInfo.in_stock_at ? formatDateTime(returnFoundInfo.in_stock_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintReturnOutAt')">{{ returnFoundInfo.out_at ? formatDateTime(returnFoundInfo.out_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item :label="t('faultStatus')">
                    <el-tag :type="returnFoundInfo.status === 'out' ? 'warning' : 'success'" size="small">
                      {{ returnFoundInfo.status === 'out' ? t('maintReturnStatusOut') : t('statusInStock') }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
                <div class="found-actions">
                  <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                  <el-checkbox v-model="returnPartScrap">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                  <el-button type="primary" size="small" @click="addFoundReturnPart">{{ t('maintReturnAddToList') }}</el-button>
                  <el-button size="small" @click="clearReturnFound">{{ t('actionReset') }}</el-button>
                </div>
              </el-card>
            </div>

            <!-- 手动添加返回件（未识别时） -->
            <div class="return-manual-area" v-if="!returnFoundInfo">
              <div class="return-manual-row">
                <el-select
                  v-model="selectedReturnPart"
                  :placeholder="t('maintReturnSelectFromSpare')"
                  filterable
                  remote
                  :remote-method="searchReturnParts"
                  :loading="spareLoading"
                  style="width: 180px"
                  clearable
                  @change="onReturnPartSelect"
                >
                  <el-option
                    v-for="part in sparePartOptions"
                    :key="part.id"
                    :label="`${part.part_number} - ${part.name}`"
                    :value="part.id"
                  />
                </el-select>
                <el-input v-model="returnPartSerial" :placeholder="t('maintReturnSerialPlaceholder')" style="width: 120px" />
                <el-input v-model="returnPartNumber" :placeholder="t('maintReturnModelManual')" style="width: 130px" />
                <el-input v-model="returnPartName" :placeholder="t('maintReturnNameDefault')" style="width: 130px" />
              </div>
              <div class="return-manual-row">
                <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                <el-button type="primary" size="small" :disabled="!returnPartSerial" @click="addReturnPart">{{ t('actionAdd') }}</el-button>
              </div>
              <div class="return-manual-tip">{{ t('maintReturnNotFoundTip') }}</div>
            </div>

            <div class="return-parts-table" v-if="maintForm.return_parts.length > 0">
              <el-table :data="maintForm.return_parts" size="small" border>
                <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('maintColModel')" width="150" />
                <el-table-column prop="name" :label="t('maintColName')" width="150" />
                <el-table-column prop="quantity" :label="t('maintColQuantity')" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" />
                  </template>
                </el-table-column>
                <el-table-column :label="t('maintColScrapIn')" width="120">
                  <template #default="{ row }">
                    <el-checkbox v-model="row.scrap_in" :disabled="!row.part_id" />
                    <span class="scrap-label" v-if="row.part_id && !row.scrap_in">{{ t('maintReturnNoScrap') }}</span>
                    <span class="scrap-label no-id" v-if="!row.part_id">{{ t('maintReturnNoPartId') }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('colOperation')" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeReturnPart($index)">
                      {{ t('actionDelete') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="return-tip">{{ t('maintReturnScrapTip') }}</div>
            </div>
            <div class="no-return-tip" v-else>
              <el-tag type="info">{{ t('maintReturnNoPartsTip') }}</el-tag>
            </div>
          </div>
            </el-form-item>
          </el-form>
        </div>

        <!-- 成本与描述 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Document /></el-icon>
            {{ t('maintCostDescSection') || '成本与描述' }}
          </div>
          <el-form :model="maintForm" label-width="80px">
            <el-form-item :label="t('maintLaborHours')">
              <el-input-number v-model="maintForm.labor_hours" :min="0" :precision="1" />
            </el-form-item>
            <el-form-item :label="t('maintLaborCost')">
              <el-input-number v-model="maintForm.labor_cost" :min="0" :precision="2" />
            </el-form-item>
            <el-form-item :label="t('maintVendor')">
              <el-input v-model="maintForm.vendor" />
            </el-form-item>
            <el-form-item :label="t('maintDesc')" required>
              <el-input v-model="maintForm.description" type="textarea" :rows="4" />
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateMaintenance() : addMaintenance()">{{ t('maintConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="t('maintScanSpareDialog')" width="900px">
      <ScanSession
        ref="scanSessionRef"
        default-type="out"
        :auto-start="scanDialogVisible"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, InfoFilled, Aim, Setting, Box, RefreshRight, Document, Edit, Delete, View, ArrowRight, Refresh, CircleCheck, SuccessFilled, WarningFilled } from '@element-plus/icons-vue'
import { getMaintenances, getDevices, createMaintenance, updateMaintenance as updateMaintenanceApi, deleteMaintenance as deleteMaintenanceApi, getPartList, createMovement, getPartBySerialNumber, transitionMaintenanceStatus } from '@/api'
import api from '@/api/request'
import ScanSession from '@/components/ScanSession.vue'
import { formatDateTime } from '@/utils/time'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const { t } = useI18n()

const maintenances = ref([])
const filteredMaintenances = ref([])
const devices = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const editMode = ref(false)

const searchText = ref('')
const filterStatus = ref('')
const filterPriority = ref('')
const filterMaintType = ref('')
const dateRange = ref([])
const sortBy = ref('maint_time_desc')

// 统计数据
const stats = computed(() => {
  const list = maintenances.value
  const totalCount = list.length
  const repairingCount = list.filter(m => m.status === 'repairing').length
  const verifyingCount = list.filter(m => m.status === 'verifying').length
  const completedCount = list.filter(m => m.status === 'completed').length
  const overdueCount = list.filter(m => {
    // 已完成或已取消的工单不算超期
    if (m.status === 'completed' || m.status === 'cancelled') return false
    if (m.sla_remaining && (m.sla_remaining === '已超期' || m.sla_remaining === 'Overdue')) return true
    if (m.sla_deadline) {
      return new Date(m.sla_deadline) < new Date()
    }
    return false
  }).length
  return {
    total: totalCount,
    repairing: repairingCount,
    verifying: verifyingCount,
    completed: completedCount,
    overdue: overdueCount
  }
})

// 分页后的总数
const filteredTotal = computed(() => filteredMaintenances.value.length)

// 状态颜色映射
const STATUS_COLORS = {
  'created': 'info',
  'diagnosing': 'primary',
  'repairing': 'warning',
  'verifying': '',
  'completed': 'success',
  'cancelled': 'danger'
}

const STATUS_LABELS = {
  'created': '创建',
  'diagnosing': '诊断',
  'repairing': '维修',
  'verifying': '验证',
  'completed': '完成',
  'cancelled': '取消'
}

const STATUS_PERCENT = {
  'created': 20,
  'diagnosing': 40,
  'repairing': 60,
  'verifying': 80,
  'completed': 100,
  'cancelled': 0
}

const getStatusColor = (status) => STATUS_COLORS[status] || 'info'
const getStatusLabel = (status) => STATUS_LABELS[status] || status
const getProgressPercent = (status) => STATUS_PERCENT[status] || 20

const getPriorityColor = (priority) => {
  const colors = { 'P1': 'danger', 'P2': 'warning', 'P3': 'info', 'P4': 'success' }
  return colors[priority] || 'info'
}

const isOverdue = (row) => {
  // 已完成或已取消的工单不算超期
  if (row.status === 'completed' || row.status === 'cancelled') return false

  // 后端已标记为超期
  if (row.sla_remaining && (row.sla_remaining === '已超期' || row.sla_remaining === 'Overdue')) return true

  // 直接比较截止时间
  if (row.sla_deadline) {
    return new Date(row.sla_deadline) < new Date()
  }
  return false
}

// 状态筛选
const filterByStatus = (status) => {
  filterStatus.value = status
  currentPage.value = 1
  filterMaintenances()
}

// 分页处理
const handlePageSizeChange = () => {
  currentPage.value = 1
}

const handlePageChange = () => {
  // 分页切换
}

// 表格行样式
const tableRowClassName = ({ row, rowIndex }) => {
  if (row.status === 'cancelled') return 'cancelled-row'
  if (isOverdue(row)) return 'overdue-row'
  return ''
}

// 查看详情
const viewDetail = (row) => {
  router.push(`/maintenance/${row.id}`)
}

// ===== 动态状态推进按钮 =====
const ACTION_BUTTONS = {
  'created': { action: 'diagnosing', label: '开始诊断', icon: 'Search', type: 'primary' },
  'diagnosing': { action: 'repairing', label: '开始维修', icon: 'Setting', type: 'warning' },
  'repairing': { action: 'verifying', label: '提交验证', icon: 'CircleCheck', type: 'info' },
  'verifying': { action: 'completed', label: '完成维修', icon: 'SuccessFilled', type: 'success' },
  'completed': { action: null, label: '查看详情', icon: 'View', type: 'default' },
  'cancelled': { action: null, label: '查看详情', icon: 'View', type: 'default' }
}

const getNextAction = (status) => {
  return ACTION_BUTTONS[status]?.action || null
}

const getActionTooltip = (status) => {
  return ACTION_BUTTONS[status]?.label || '查看详情'
}

const getActionIcon = (status) => {
  return ACTION_BUTTONS[status]?.icon || 'View'
}

const getActionButtonType = (status) => {
  return ACTION_BUTTONS[status]?.type || 'default'
}

// 处理状态推进操作
const handleStatusAction = async (row) => {
  const nextAction = getNextAction(row.status)
  if (!nextAction) {
    viewDetail(row)
    return
  }

  const actionLabel = ACTION_BUTTONS[row.status]?.label

  try {
    // 先获取状态建议
    const suggestResult = await api.post(`/api/maintenance/${row.id}/suggest-status`, {})

    // 弹出确认对话框
    await ElMessageBox.confirm(
      `是否执行「${actionLabel}」操作？\n状态将从「${suggestResult.current_status_label}」变为「${suggestResult.suggested_status_label || getNextStatusLabel(nextAction)}」`,
      '状态流转确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    // 调用自动状态推进 API
    const result = await api.post(`/api/maintenance/${row.id}/auto-transition`, {
      status: nextAction,
      operator: 'Web'
    })

    ElMessage.success(result.message || `状态已更新为 ${result.status_label}`)

    // 刷新列表
    await loadMaintenances()

  } catch (e) {
    if (e !== 'cancel') {
      const detail = e.response?.data?.detail || e.message
      ElMessage.error(detail)
    }
  }
}

const getNextStatusLabel = (status) => {
  const labels = {
    'diagnosing': '诊断',
    'repairing': '维修',
    'verifying': '验证',
    'completed': '完成',
    'cancelled': '取消'
  }
  return labels[status] || status
}

// 备件相关
const sparePartOptions = ref([])
const spareLoading = ref(false)
const selectedSparePart = ref(null)
const currentFoundPart = ref(null)  // 当前扫码找到的备件

// 扫码对话框
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)

// 返回件扫码相关
const returnScanInput = ref('')
const returnScanLoading = ref(false)
const returnFoundInfo = ref(null)  // 扫码识别到的返回件信息
const selectedReturnPart = ref(null)
const returnPartSerial = ref('')
const returnPartNumber = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

const openAddDialog = async () => {
  editMode.value = false
  resetForm()
  // 预加载备件列表
  await loadInitialSpareParts()
  showAddDialog.value = true
}

// 加载初始备件列表
const loadInitialSpareParts = async () => {
  spareLoading.value = true
  try {
    const result = await getPartList({ limit: 50 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    console.error(t('spareLoadFailed'), e)
  } finally {
    spareLoading.value = false
  }
}

const maintForm = ref({
  device_id: null,
  maint_type: 'corrective',
  spare_parts: [],  // 更换的备件列表
  return_parts: [], // 返回件列表（换下来的坏件）
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  vendor: '',
  description: ''
})

const getMaintTypeType = (type) => {
  const types = { preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }
  return types[type] || ''
}

const getMaintTypeText = (type) => {
  const texts = {
    preventive: t('maintTypePreventive'),
    corrective: t('maintTypeCorrective'),
    upgrade: t('maintTypeUpgrade'),
    emergency: t('maintTypeEmergency')
  }
  return texts[type] || type
}

// 搜索备件
const searchSpareParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    const result = await getPartList({ search: query, limit: 20 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    ElMessage.error(t('maintSearchFailed'))
  } finally {
    spareLoading.value = false
  }
}

// 搜索返回件备件（共用同一个搜索）
const searchReturnParts = async (query) => {
  await searchSpareParts(query)
}

// 扫码找到备件（只显示信息，不自动添加）
const onScanPartFound = (part) => {
  // 不自动添加，等用户点击按钮后再添加
  currentFoundPart.value = part
}

// 扫码添加备件（从ScanInput组件点击按钮）
const onScanPartAdded = (item) => {
  // 加入更换列表
  const existing = maintForm.value.spare_parts.find(p => p.part_id === item.id)
  if (existing) {
    existing.quantity += 1
    ElMessage.info(`${item.name} ${t('maintPartQtyAdded')}`)
  } else {
    maintForm.value.spare_parts.push({
      part_id: item.id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      quantity: 1
    })
    // 如果是出库操作，提示用户
    if (item.action === 'out') {
      ElMessage.success(`${t('maintAlreadyOut')}: ${item.name}`)
    } else {
      ElMessage.success(`${t('maintPartAdded')}: ${item.name}`)
    }
  }
  updatePartsCost()
  currentFoundPart.value = null
}

// 打开扫码对话框
const openScanDialog = () => {
  scanDialogVisible.value = true
}

// 扫码会话完成
const onScanSessionComplete = async (result) => {
  // 将扫描的备件加入更换列表（已在扫码会话中自动出库，标记跳过重复出库）
  for (const item of result.items) {
    const existing = maintForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      existing.quantity += 1
      ElMessage.info(`${item.name} ${t('maintPartQtyAdded')}`)
    } else {
      maintForm.value.spare_parts.push({
        part_id: item.part_id,
        part_number: item.part_number,
        name: item.name,
        serial_number: item.serial_number,
        unit_price: item.unit_price || 0,
        quantity: 1,
        is_from_scan: true  // 标记为扫码添加，已在扫码会话中出库
      })
      ElMessage.success(`${t('maintPartAdded')}: ${item.name}`)
    }
  }
  updatePartsCost()
  scanDialogVisible.value = false
  ElMessage.success(`${t('maintAddedCount')} ${result.items.length} ${t('maintPartAdded')}`)
}

// 添加备件到表单
const addSparePartToForm = () => {
  if (!selectedSparePart.value) return

  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return

  // 检查是否已添加
  const existing = maintForm.value.spare_parts.find(p => p.part_id === part.id)
  if (existing) {
    existing.quantity += 1
  } else {
    maintForm.value.spare_parts.push({
      part_id: part.id,
      part_number: part.part_number,
      name: part.name,
      unit_price: part.unit_price || 0,
      quantity: 1
    })
  }

  updatePartsCost()
  selectedSparePart.value = null
}

// 移除备件
const removeSparePart = (index) => {
  maintForm.value.spare_parts.splice(index, 1)
  updatePartsCost()
}

// 扫码查询返回件
const scanReturnPart = async () => {
  const serial = returnScanInput.value.trim()
  if (!serial || serial.length < 4) {
    ElMessage.warning(t('maintSerialMinLength'))
    return
  }

  returnScanLoading.value = true
  try {
    const info = await getPartBySerialNumber(serial)
    returnFoundInfo.value = info
    ElMessage.success(`${t('maintIdentified')}: ${info.name || info.part_number}`)
    // 自动填充表单
    returnPartSerial.value = info.serial_number
    returnPartNumber.value = info.part_number
    returnPartName.value = info.name
    selectedReturnPart.value = info.id
    returnPartScrap.value = true  // 有记录的默认入报废库
  } catch (e) {
    // 未找到，提示手动输入
    returnFoundInfo.value = null
    returnPartSerial.value = serial
    ElMessage.info(t('maintSerialNotFound'))
  } finally {
    returnScanLoading.value = false
  }
}

// 清除识别结果
const clearReturnFound = () => {
  returnFoundInfo.value = null
  returnScanInput.value = ''
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  selectedReturnPart.value = null
  returnPartQty.value = 1
}

// 添加识别到的返回件
const addFoundReturnPart = () => {
  if (!returnFoundInfo.value) return

  maintForm.value.return_parts.push({
    part_id: returnFoundInfo.value.id,
    part_number: returnFoundInfo.value.part_number,
    name: returnFoundInfo.value.name,
    serial_number: returnFoundInfo.value.serial_number,
    unit_price: returnFoundInfo.value.unit_price || 0,
    quantity: returnPartQty.value,
    scrap_in: returnPartScrap.value,
    is_from_scan: true,  // 标记为扫码识别
    history: returnFoundInfo.value.history  // 保存历史记录
  })

  ElMessage.success(`${t('maintReturnAdded')}: ${returnFoundInfo.value.serial_number}`)
  clearReturnFound()
}

// 选择备件型号时自动填充
const onReturnPartSelect = () => {
  if (!selectedReturnPart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
  if (part) {
    returnPartNumber.value = part.part_number
    returnPartName.value = part.name || part.part_number  // 名称默认用型号
    returnPartScrap.value = true
  }
}

// 手动添加返回件
const addReturnPart = () => {
  if (!returnPartSerial.value) {
    ElMessage.warning(t('maintSerialPrompt'))
    return
  }

  // 检查是否已添加过该序列号
  const existing = maintForm.value.return_parts.find(p => p.serial_number === returnPartSerial.value)
  if (existing) {
    ElMessage.warning(`${t('maintSerialDuplicate')} ${returnPartSerial.value}`)
    return
  }

  // 如果从备件库选择，使用备件信息
  let partNumber = returnPartNumber.value
  let partName = returnPartName.value || returnPartNumber.value  // 名称默认=型号
  let partId = null

  if (selectedReturnPart.value) {
    const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) {
      partId = part.id
      partNumber = part.part_number
      partName = part.name || part.part_number
    }
  }

  maintForm.value.return_parts.push({
    part_id: partId,
    part_number: partNumber,
    name: partName,
    serial_number: returnPartSerial.value,
    quantity: returnPartQty.value,
    scrap_in: selectedReturnPart.value ? returnPartScrap.value : false,
    is_from_scan: false
  })

  ElMessage.success(`${t('maintReturnAdded')}: ${returnPartSerial.value}`)

  // 清空输入
  returnScanInput.value = ''
  returnFoundInfo.value = null
  selectedReturnPart.value = null
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  returnPartQty.value = 1
  returnPartScrap.value = true
}

// 移除返回件
const removeReturnPart = (index) => {
  maintForm.value.return_parts.splice(index, 1)
}

// 更新备件成本
const updatePartsCost = () => {
  maintForm.value.parts_cost = maintForm.value.spare_parts.reduce(
    (sum, p) => sum + p.quantity * p.unit_price, 0
  )
}

const filterMaintenances = () => {
  let result = [...maintenances.value]

  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(m =>
      m.device_name?.toLowerCase().includes(search) ||
      m.maint_no?.toLowerCase().includes(search) ||
      m.description?.toLowerCase().includes(search)
    )
  }

  // 状态筛选
  if (filterStatus.value) {
    if (filterStatus.value === 'overdue') {
      result = result.filter(m => isOverdue(m))
    } else {
      result = result.filter(m => m.status === filterStatus.value)
    }
  }

  // 优先级筛选
  if (filterPriority.value) {
    result = result.filter(m => (m.priority || 'P3') === filterPriority.value)
  }

  if (filterMaintType.value) {
    result = result.filter(m => m.maint_type === filterMaintType.value)
  }

  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(m => {
      const maintTime = dayjs(m.maint_time || m.created_at)
      return maintTime.isAfter(startDate) && maintTime.isBefore(endDate)
    })
  }

  if (sortBy.value) {
    switch (sortBy.value) {
      case 'maint_time_desc':
        result.sort((a, b) => dayjs(b.maint_time || b.created_at) - dayjs(a.maint_time || a.created_at))
        break
      case 'maint_time_asc':
        result.sort((a, b) => dayjs(a.maint_time || a.created_at) - dayjs(b.maint_time || b.created_at))
        break
      case 'total_cost_desc':
        result.sort((a, b) => ((b.parts_cost || 0) + (b.labor_cost || 0)) - ((a.parts_cost || 0) + (a.labor_cost || 0)))
        break
      case 'total_cost_asc':
        result.sort((a, b) => ((a.parts_cost || 0) + (a.labor_cost || 0)) - ((b.parts_cost || 0) + (b.labor_cost || 0)))
        break
    }
  }

  filteredMaintenances.value = result
}

const loadMaintenances = async () => {
  loading.value = true
  try {
    const data = await getMaintenances({ limit: 500 })
    maintenances.value = data.items || []
    total.value = data.total || maintenances.value.length
    filterMaintenances()
  } catch (error) {
    ElMessage.error(t('maintLoadFailed'))
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (error) {
    ElMessage.error(t('maintDeviceLoadFailed'))
  }
}

const addMaintenance = async () => {
  if (!maintForm.value.device_id) {
    ElMessage.warning(t('maintSelectDevicePrompt'))
    return
  }
  if (!maintForm.value.description) {
    ElMessage.warning(t('maintDescPrompt'))
    return
  }

  try {
    // 创建维修记录 - 合并备件和返回件数据
    const device = devices.value.find(d => d.id === maintForm.value.device_id)
    const combinedParts = [
      ...maintForm.value.spare_parts.map(p => ({ ...p, is_return: false })),
      ...maintForm.value.return_parts.map(p => ({ ...p, is_return: true }))
    ]

    await createMaintenance({
      ...maintForm.value,
      device_name: device?.name,
      parts_replaced: JSON.stringify(combinedParts)
    })

    // 处理备件出库（只处理手动添加的，扫码添加的已在扫码会话中自动出库）
    for (const part of maintForm.value.spare_parts) {
      if (part.part_id && !part.is_from_scan) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'out',
          quantity: part.quantity,
          serial_number: part.serial_number,
          reason: `${t('spareReasonMaintenanceReplace')} - ${maintForm.value.maint_type}`,
          operator: 'Web',
          reference: device?.name
        })
      }
    }

    // 处理返回件入报废库
    for (const part of maintForm.value.return_parts) {
      if (part.scrap_in && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'scrap_in',
          quantity: part.quantity,
          serial_number: part.serial_number,
          reason: t('spareReasonReturnPartScrap'),
          operator: 'Web',
          reference: device?.name
        })
      }
    }

    ElMessage.success(t('maintAddSuccess'))
    showAddDialog.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
    ElMessage.error(`${t('maintAddFailed')}: ${error.response?.data?.detail || error.message}`)
  }
}

const editMaintenance = (row) => {
  editMode.value = true
  maintForm.value = {
    id: row.id,
    device_id: row.device_id,
    maint_type: row.maint_type,
    spare_parts: [],
    return_parts: [],
    parts_cost: row.parts_cost || 0,
    labor_hours: row.labor_hours || 0,
    labor_cost: row.labor_cost || 0,
    vendor: row.vendor || '',
    description: row.description
  }
  showAddDialog.value = true
}

const updateMaintenance = async () => {
  if (!maintForm.value.description) {
    ElMessage.warning(t('maintDescPrompt'))
    return
  }

  try {
    const device = devices.value.find(d => d.id === maintForm.value.device_id)
    await updateMaintenanceApi(maintForm.value.id, {
      ...maintForm.value,
      device_name: device?.name,
      parts_replaced: JSON.stringify(maintForm.value.spare_parts)
    })
    ElMessage.success(t('maintUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
    ElMessage.error(t('maintUpdateFailed'))
  }
}

const deleteMaintenance = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('maintConfirmDeletePrompt')} "${row.maint_no}"?`, t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteMaintenanceApi(row.id)
    ElMessage.success(t('maintDeleteSuccess'))
    loadMaintenances()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('maintDeleteFailed'))
    }
  }
}

const resetForm = () => {
  maintForm.value = {
    device_id: null,
    maint_type: 'corrective',
    spare_parts: [],
    return_parts: [],
    parts_cost: 0,
    labor_hours: 0,
    labor_cost: 0,
    vendor: '',
    description: ''
  }
  selectedSparePart.value = null
  sparePartOptions.value = []
  currentFoundPart.value = null
  returnScanInput.value = ''
  returnFoundInfo.value = null
  selectedReturnPart.value = null
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  returnPartQty.value = 1
  returnPartScrap.value = true
}

onMounted(() => {
  loadMaintenances()
  loadDevices()
})
</script>

<style scoped>
.maintenance-page {
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 统计 Dashboard ===== */
.stats-dashboard {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stats-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.refresh-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card:hover {
  background: var(--bg-hover);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 48, 135, 0.08);
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.stat-card.total .card-icon {
  background: rgba(9, 132, 227, 0.15);
  color: #0984e3;
}

.stat-card.repairing .card-icon {
  background: rgba(225, 112, 85, 0.15);
  color: #e17055;
}

.stat-card.verifying .card-icon {
  background: rgba(116, 185, 255, 0.15);
  color: #74b9ff;
}

.stat-card.completed .card-icon {
  background: rgba(0, 184, 148, 0.15);
  color: #00b894;
}

.stat-card.overdue .card-icon {
  background: rgba(214, 48, 49, 0.15);
  color: #d63031;
}

.card-body {
  flex: 1;
}

.metric-value {
  font-family: 'JetBrains Mono', 'Geist Mono', monospace;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1;
}

.metric-value.danger {
  color: #d63031;
}

.metric-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

/* ===== 筛选工具栏 ===== */
.filter-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  width: 220px;
}

.status-chips {
  display: flex;
  gap: 8px;
}

.status-chip {
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 6px;
}

.status-chip.active {
  box-shadow: 0 0 0 2px var(--accent-primary);
}

.status-chip.chip-created { background: rgba(9, 132, 227, 0.1); border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }
.status-chip.chip-diagnosing { background: rgba(9, 132, 227, 0.15); border-color: rgba(9, 132, 227, 0.4); color: #0984e3; }
.status-chip.chip-repairing { background: rgba(225, 112, 85, 0.1); border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.status-chip.chip-verifying { background: rgba(116, 185, 255, 0.1); border-color: rgba(116, 185, 255, 0.3); color: #74b9ff; }
.status-chip.chip-completed { background: rgba(0, 184, 148, 0.1); border-color: rgba(0, 184, 148, 0.3); color: #00b894; }

.more-filters {
  display: flex;
  gap: 8px;
}

.add-btn {
  margin-left: auto;
}

/* ===== 数据面板 ===== */
.data-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

/* 现代化表格 */
.modern-table {
  width: 100%;
}

.modern-table :deep(.el-table__header-wrapper) {
  border-bottom: 2px solid var(--border-default);
}

.modern-table :deep(th.el-table__cell) {
  background: var(--bg-tertiary);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.modern-table :deep(td.el-table__cell) {
  border-bottom: 1px solid var(--border-subtle);
}

.modern-table :deep(.el-table__row) {
  transition: all 0.2s;
}

.modern-table :deep(.el-table__row:hover > td) {
  background: var(--bg-hover) !important;
}

.modern-table :deep(.cancelled-row) {
  opacity: 0.6;
}

.modern-table :deep(.overdue-row) {
  background: rgba(214, 48, 49, 0.05);
}

/* 维修单号链接 */
.maint-no-link {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--accent-primary);
  text-decoration: none;
  font-family: 'JetBrains Mono', 'Geist Mono', monospace;
  font-weight: 500;
  font-size: 13px;
  transition: all 0.2s;
}

.maint-no-link:hover {
  color: var(--accent-secondary);
}

.maint-no-link:hover .link-arrow {
  opacity: 1;
  transform: translateX(4px);
}

.link-arrow {
  opacity: 0;
  transition: all 0.2s;
}

/* 状态标签 */
.status-tag {
  font-weight: 500;
}

/* 优先级标签 */
.priority-tag {
  font-family: 'JetBrains Mono', monospace;
}

/* 负责人 */
.owner-cell {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 进度条 */
.mini-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-track {
  width: 60px;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-fill.created { background: rgba(9, 132, 227, 0.4); }
.progress-fill.diagnosing { background: rgba(9, 132, 227, 0.6); }
.progress-fill.repairing { background: rgba(225, 112, 85, 0.7); }
.progress-fill.verifying { background: rgba(116, 185, 255, 0.8); }
.progress-fill.completed { background: #00b894; }
.progress-fill.cancelled { background: #d63031; }

.progress-text {
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-tertiary);
}

/* SLA */
.sla-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.sla-time {
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-secondary);
}

.sla-cell.overdue .sla-time {
  color: #d63031;
  font-weight: 500;
}

/* 成本 */
.cost-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

/* 操作图标 */
.action-icons {
  display: flex;
  gap: 4px;
}

.action-icon {
  padding: 4px;
}

.action-icon:hover {
  background: var(--bg-tertiary);
  border-radius: 6px;
}

/* 分页 */
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    width: 100%;
  }

  .status-chips {
    flex-wrap: wrap;
  }

  .more-filters {
    flex-wrap: wrap;
  }

  .add-btn {
    width: 100%;
    margin-left: 0;
  }
}

/* ===== 暗色模式 ===== */
.dark .stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 184, 148, 0.1);
}

.dark .stat-card.total .card-icon { background: rgba(9, 132, 227, 0.2); }
.dark .stat-card.repairing .card-icon { background: rgba(225, 112, 85, 0.2); }
.dark .stat-card.verifying .card-icon { background: rgba(116, 185, 255, 0.2); }
.dark .stat-card.completed .card-icon { background: rgba(0, 184, 148, 0.2); }
.dark .stat-card.overdue .card-icon { background: rgba(214, 48, 49, 0.2); }

.dark .status-chip.chip-created { background: rgba(9, 132, 227, 0.15); }
.dark .status-chip.chip-diagnosing { background: rgba(9, 132, 227, 0.2); }
.dark .status-chip.chip-repairing { background: rgba(225, 112, 85, 0.15); }
.dark .status-chip.chip-verifying { background: rgba(116, 185, 255, 0.15); }
.dark .status-chip.chip-completed { background: rgba(0, 184, 148, 0.15); }

.dark .modern-table :deep(.overdue-row) {
  background: rgba(214, 48, 49, 0.1);
}

/* ===== 编辑对话框样式 ===== */
.edit-dialog-content {
  max-width: 980px;
  margin: 0 auto;
}

.form-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  transition: all 0.2s;
}

.form-section:hover {
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.08);
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.form-section-title .el-icon {
  color: var(--color-gb);
}

/* 备件选择区域 */
.spare-parts-section {
  width: 100%;
}

.spare-search {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.spare-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.selected-parts {
  margin-top: 12px;
}

.no-parts-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 4px;
  color: #909399;
  font-size: 13px;
  margin-top: 12px;
}

.parts-summary {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  text-align: right;
}

.total-cost {
  font-weight: 600;
  color: #409EFF;
  font-size: 16px;
}

.spare-option {
  display: flex;
  align-items: center;
  gap: 12px;
}

.spare-number {
  font-weight: 500;
  color: #409EFF;
}

.spare-name {
  color: #606266;
}

.spare-stock {
  font-size: 12px;
  color: #909399;
}

.spare-stock.low {
  color: #F56C6C;
  font-weight: 500;
}

/* 返回件区域样式 */
.return-parts-section {
  width: 100%;
}

.return-found-info {
  margin-bottom: 16px;
}

.found-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.found-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.return-manual-area {
  margin-bottom: 12px;
}

.return-manual-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.return-manual-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.return-parts-table {
  margin-top: 8px;
}

.scrap-label {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.scrap-label.no-id {
  color: #E6A23C;
}

.return-tip {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 4px;
  color: #909399;
  font-size: 12px;
}

/* 扫码功能条 */
.scan-action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, var(--color-gb) 0%, var(--color-gb-mid) 100%);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.scan-action-bar.return {
  background: linear-gradient(135deg, #636e72 0%, #4a5455 100%);
}

.scan-action-bar .scan-btn {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.3);
  color: #fff;
  font-weight: 600;
  height: 36px;
  border-radius: 8px;
  transition: all 0.2s;
}

.scan-action-bar .scan-btn:hover {
  background: rgba(255,255,255,0.25);
  transform: translateY(-1px);
}

.scan-tip-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  color: rgba(255,255,255,0.9);
  font-size: 12px;
}

/* 暗色模式适配 */
.dark .form-section:hover {
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.1);
}

.dark .form-section-title .el-icon {
  color: var(--accent-primary);
}
</style>

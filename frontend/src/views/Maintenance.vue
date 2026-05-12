<template>
  <div class="maintenance-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuMaintenance') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn" @click="openAddDialog">
          <el-icon><Plus /></el-icon>
          <span>{{ t('maintAddRecord') }}</span>
        </button>
        <button class="nav-action-btn secondary" @click="loadMaintenances" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-grid">
        <!-- 总维修单 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.total }}</div>
              <div class="metric-label">{{ t('maintStatsTotal') }}</div>
            </div>
            <div class="card-trend stable">
              <span class="trend-icon">&#9679;</span>
            </div>
          </div>
        </div>
        <!-- 维修中 -->
        <div class="stat-card repairing" @click="filterByStatus('repairing')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Setting /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.repairing }}</div>
              <div class="metric-label">{{ t('maintStatsRepairing') }}</div>
            </div>
            <div class="card-progress">
              <div class="progress-ring" :style="{ '--percent': getRepairingPercent() }"></div>
            </div>
          </div>
        </div>
        <!-- 待验证 -->
        <div class="stat-card verifying" @click="filterByStatus('verifying')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.verifying }}</div>
              <div class="metric-label">{{ t('maintStatsVerifying') }}</div>
            </div>
            <div class="card-trend info">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <!-- 已完成 -->
        <div class="stat-card completed" @click="filterByStatus('completed')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><SuccessFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.completed }}</div>
              <div class="metric-label">{{ t('maintStatsCompleted') }}</div>
            </div>
            <div class="card-trend success">
              <el-icon><SuccessFilled /></el-icon>
            </div>
          </div>
        </div>
        <!-- 超时工单 -->
        <div class="stat-card overdue" @click="filterByStatus('overdue')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.overdue }}</div>
              <div class="metric-label">{{ t('maintStatsOverdue') }}</div>
            </div>
            <div class="card-trend warning" v-if="stats.overdue > 0">
              <el-icon><Warning /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 高级筛选工具栏 -->
    <section class="filter-section">
      <div class="filter-toolbar">
        <!-- 搜索框 -->
        <div class="search-box">
          <el-icon class="search-icon"><Search /></el-icon>
          <el-input
            v-model="searchText"
            :placeholder="t('maintSearchPlaceholder')"
            class="search-input"
            clearable
            @input="filterMaintenances"
          />
        </div>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <div
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >
            <span class="chip-label">{{ t('maintFilterAll') }}</span>
            <span class="chip-count">{{ stats.total }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-created', { active: filterStatus === 'created' }]"
            @click="filterByStatus('created')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelCreated') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-diagnosing', { active: filterStatus === 'diagnosing' }]"
            @click="filterByStatus('diagnosing')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelDiagnosing') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-repairing', { active: filterStatus === 'repairing' }]"
            @click="filterByStatus('repairing')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelRepairing') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-verifying', { active: filterStatus === 'verifying' }]"
            @click="filterByStatus('verifying')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelVerifying') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-completed', { active: filterStatus === 'completed' }]"
            @click="filterByStatus('completed')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelCompleted') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-overdue', { active: filterStatus === 'overdue' }]"
            @click="filterByStatus('overdue')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintFilterOverdue') }}</span>
          </div>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-select v-model="filterPriority" :placeholder="t('maintPriority')" clearable style="width: 90px" @change="filterMaintenances">
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
            style="width: 220px"
            @change="filterMaintenances"
          />
        </div>
      </div>
    </section>

    <!-- 维修单数据面板 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">Work Order List</span>
        <span class="table-count">{{ filteredTotal }} records</span>
      </div>

      <el-table
        :data="paginatedMaintenances"
        class="enterprise-table"
        v-loading="loading"
        :row-class-name="tableRowClassName"
        :header-cell-style="{ background: 'transparent' }"
      >
        <!-- 维修单号 -->
        <el-table-column prop="maint_no" :label="t('maintColNo')" width="220">
          <template #default="{ row }">
            <router-link :to="`/maintenance/${row.id}`" class="maint-no-link">
              <span class="maint-no-badge">{{ row.maint_no }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column prop="status" :label="t('maintStatusLabel')" width="100">
          <template #default="{ row }">
            <div :class="['status-badge', row.status]">
              <span class="status-dot"></span>
              <span class="status-text">{{ row.status_label || getStatusLabel(row.status) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 优先级 -->
        <el-table-column prop="priority" :label="t('maintPriority')" width="90">
          <template #default="{ row }">
            <div :class="['priority-badge', getPriorityBadgeClass(row.priority)]">
              <span class="priority-icon">
                <el-icon v-if="getPriorityBadgeClass(row.priority) === 'P1'"><Warning /></el-icon>
                <el-icon v-else-if="getPriorityBadgeClass(row.priority) === 'P2'"><InfoFilled /></el-icon>
              </span>
              <span class="priority-text">{{ row.priority || 'P3' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 设备 -->
        <el-table-column prop="device_name" :label="t('maintColDevice')" width="180">
          <template #default="{ row }">
            <div class="device-cell">
              <el-icon class="device-icon"><Connection /></el-icon>
              <span class="device-name">{{ row.device_name || '--' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 负责人 -->
        <el-table-column prop="current_owner" :label="t('maintOwner')" width="120">
          <template #default="{ row }">
            <div class="owner-cell">
              <div class="owner-avatar">{{ (row.current_owner || '?')[0] }}</div>
              <span class="owner-name">{{ row.current_owner || t('maintOwnerUnassigned') }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 类型 -->
        <el-table-column prop="maint_type" :label="t('maintColType')" width="120">
          <template #default="{ row }">
            <div :class="['type-badge', row.maint_type || 'other']">
              <span class="type-text">{{ getMaintTypeText(row.maint_type) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 进度 -->
        <el-table-column prop="progress_percent" :label="t('maintProgress')" width="140">
          <template #default="{ row }">
            <div class="progress-cell">
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" :style="{ width: getProgressPercent(row.status) + '%' }" :class="row.status"></div>
              </div>
              <span class="progress-percent">{{ getProgressPercent(row.status) }}%</span>
            </div>
          </template>
        </el-table-column>

        <!-- SLA -->
        <el-table-column prop="sla_remaining" :label="t('maintSlaDeadline')" width="100">
          <template #default="{ row }">
            <div :class="['sla-cell', { overdue: isOverdue(row), critical: isSlaCritical(row) }]">
              <el-icon v-if="isOverdue(row)" class="sla-icon"><Warning /></el-icon>
              <span class="sla-text">{{ row.sla_remaining || '--' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 成本 -->
        <el-table-column prop="total_cost" :label="t('maintColTotalCost')" width="120">
          <template #default="{ row }">
            <div class="cost-cell">
              <span class="cost-currency">&#165;</span>
              <span class="cost-value">{{ ((row.parts_cost || 0) + (row.labor_cost || 0)).toFixed(2) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 时间 -->
        <el-table-column prop="maint_time" :label="t('maintColTime')" width="180">
          <template #default="{ row }">
            <div class="time-cell">
              <el-icon class="time-icon"><Clock /></el-icon>
              <span class="time-text">{{ formatDateTime(row.maint_time || row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('colOperation')" width="120" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <button class="action-btn advance" @click="handleStatusAction(row)" v-if="getNextAction(row.status)" :title="getActionTooltip(row.status)">
                <el-icon><component :is="getActionIcon(row.status)" /></el-icon>
              </button>
              <button class="action-btn view" @click="viewDetail(row)" title="查看详情">
                <el-icon><View /></el-icon>
              </button>
              <button class="action-btn delete" @click="deleteMaintenance(row)" v-if="row.status !== 'completed'" title="删除">
                <el-icon><Delete /></el-icon>
              </button>
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
                  <template #default="{ row }">&#165;{{ (row.unit_price || 0).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="total" :label="t('maintColSubtotal')" width="80">
                  <template #default="{ row }">&#165;{{ (row.quantity * (row.unit_price || 0)).toFixed(2) }}</template>
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
                {{ t('maintSpareTotalCost') }}: <span class="total-cost">&#165;{{ maintForm.parts_cost.toFixed(2) }}</span>
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

            <div class="return-found-info" v-if="returnFoundInfo">
              <el-card size="small" shadow="never">
                <div class="found-header">
                  <el-tag type="success" size="small">{{ t('maintReturnFoundTag') }}</el-tag>
                  <span>{{ returnFoundInfo.serial_number }}</span>
                </div>
                <el-descriptions :column="3" size="small" border>
                  <el-descriptions-item :label="t('maintColModel')">{{ returnFoundInfo.part_number }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColName')">{{ returnFoundInfo.name }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColUnitPrice')">&#165;{{ (returnFoundInfo.unit_price || 0).toFixed(2) }}</el-descriptions-item>
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
import { Plus, Search, InfoFilled, Aim, Setting, Box, RefreshRight, Document, Edit, Delete, View, ArrowRight, Refresh, CircleCheck, SuccessFilled, WarningFilled, Warning, Connection } from '@element-plus/icons-vue'
import { getMaintenances, getDevices, createMaintenance, updateMaintenance as updateMaintenanceApi, deleteMaintenance as deleteMaintenanceApi, getPartList, createMovement, getPartBySerialNumber, transitionMaintenanceStatus } from '@/api'
import api from '@/api/request'
import ScanSession from '@/components/ScanSession.vue'
import { formatDateTime, dayjs } from '@/utils/time'
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

const stats = computed(() => {
  const list = maintenances.value
  const totalCount = list.length
  const repairingCount = list.filter(m => m.status === 'repairing').length
  const verifyingCount = list.filter(m => m.status === 'verifying').length
  const completedCount = list.filter(m => m.status === 'completed').length
  const overdueCount = list.filter(m => {
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

const filteredTotal = computed(() => filteredMaintenances.value.length)

const paginatedMaintenances = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredMaintenances.value.slice(start, end)
})

const getRepairingPercent = () => {
  if (stats.value.total === 0) return 0
  return Math.round((stats.value.repairing / stats.value.total) * 100)
}

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

const getPriorityBadgeClass = (priority) => priority || 'P3'

const isOverdue = (row) => {
  if (row.status === 'completed' || row.status === 'cancelled') return false
  if (row.sla_remaining && (row.sla_remaining === '已超期' || row.sla_remaining === 'Overdue')) return true
  if (row.sla_deadline) return new Date(row.sla_deadline) < new Date()
  return false
}

const isSlaCritical = (row) => {
  if (row.status === 'completed' || row.status === 'cancelled') return false
  if (row.sla_remaining) {
    const match = row.sla_remaining.match(/(\d+)h/)
    if (match && parseInt(match[1]) <= 4) return true
  }
  return false
}

const filterByStatus = (status) => {
  filterStatus.value = status
  currentPage.value = 1
  filterMaintenances()
}

const handlePageSizeChange = () => { currentPage.value = 1 }
const handlePageChange = () => {}

const tableRowClassName = ({ row }) => {
  if (row.status === 'cancelled') return 'cancelled-row'
  if (isOverdue(row)) return 'overdue-row'
  return ''
}

const viewDetail = (row) => { router.push(`/maintenance/${row.id}`) }

const ACTION_BUTTONS = {
  'created': { action: 'diagnosing', label: '开始诊断', icon: 'Search' },
  'diagnosing': { action: 'repairing', label: '开始维修', icon: 'Setting' },
  'repairing': { action: 'verifying', label: '提交验证', icon: 'CircleCheck' },
  'verifying': { action: 'completed', label: '完成维修', icon: 'SuccessFilled' },
  'completed': { action: null, label: '查看详情', icon: 'View' },
  'cancelled': { action: null, label: '查看详情', icon: 'View' }
}

const getNextAction = (status) => ACTION_BUTTONS[status]?.action || null
const getActionTooltip = (status) => ACTION_BUTTONS[status]?.label
const getActionIcon = (status) => ACTION_BUTTONS[status]?.icon || 'View'

const handleStatusAction = async (row) => {
  const nextAction = getNextAction(row.status)
  if (!nextAction) { viewDetail(row); return }
  const actionLabel = ACTION_BUTTONS[row.status]?.label
  try {
    const suggestResult = await api.post(`/maintenance/${row.id}/suggest-status`, {})
    await ElMessageBox.confirm(
      `是否执行「${actionLabel}」操作？\n状态将从「${suggestResult.current_status_label}」变为「${suggestResult.suggested_status_label || getNextStatusLabel(nextAction)}」`,
      '状态流转确认',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
    )
    const result = await api.post(`/maintenance/${row.id}/auto-transition`, { status: nextAction, operator: 'Web' })
    ElMessage.success(result.message || `状态已更新为 ${result.status_label}`)
    await loadMaintenances()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || e.message)
  }
}

const getNextStatusLabel = (status) => {
  const labels = { 'diagnosing': '诊断', 'repairing': '维修', 'verifying': '验证', 'completed': '完成', 'cancelled': '取消' }
  return labels[status] || status
}

const sparePartOptions = ref([])
const spareLoading = ref(false)
const selectedSparePart = ref(null)
const currentFoundPart = ref(null)
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)
const returnScanInput = ref('')
const returnScanLoading = ref(false)
const returnFoundInfo = ref(null)
const selectedReturnPart = ref(null)
const returnPartSerial = ref('')
const returnPartNumber = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

const openAddDialog = async () => {
  editMode.value = false
  resetForm()
  await loadInitialSpareParts()
  showAddDialog.value = true
}

const loadInitialSpareParts = async () => {
  spareLoading.value = true
  try {
    const result = await getPartList({ limit: 50 })
    sparePartOptions.value = result.items || []
  } catch (e) { console.error(t('spareLoadFailed'), e) }
  finally { spareLoading.value = false }
}

const maintForm = ref({
  device_id: null, maint_type: 'corrective', spare_parts: [], return_parts: [],
  parts_cost: 0, labor_hours: 0, labor_cost: 0, vendor: '', description: ''
})

const getMaintTypeText = (type) => {
  const texts = { preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }
  return texts[type] || type || '--'
}

const searchSpareParts = async (query) => {
  if (!query || query.length < 1) { sparePartOptions.value = []; return }
  spareLoading.value = true
  try {
    const result = await getPartList({ search: query, limit: 20 })
    sparePartOptions.value = result.items || []
  } catch (e) { ElMessage.error(t('maintSearchFailed')) }
  finally { spareLoading.value = false }
}

const searchReturnParts = async (query) => { await searchSpareParts(query) }

const onScanPartAdded = (item) => {
  const existing = maintForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
  if (existing) { existing.quantity += 1; ElMessage.info(`${item.name} ${t('maintPartQtyAdded')}`) }
  else {
    maintForm.value.spare_parts.push({ part_id: item.id, part_number: item.part_number, name: item.name, serial_number: item.serial_number, unit_price: item.unit_price || 0, quantity: 1 })
    ElMessage.success(item.action === 'out' ? `${t('maintAlreadyOut')}: ${item.name}` : `${t('maintPartAdded')}: ${item.name}`)
  }
  updatePartsCost(); currentFoundPart.value = null
}

const openScanDialog = () => { scanDialogVisible.value = true }

const onScanSessionComplete = async (result) => {
  for (const item of result.items) {
    const existing = maintForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) { existing.quantity += 1; ElMessage.info(`${item.name} ${t('maintPartQtyAdded')}`) }
    else { maintForm.value.spare_parts.push({ part_id: item.part_id, part_number: item.part_number, name: item.name, serial_number: item.serial_number, unit_price: item.unit_price || 0, quantity: 1, is_from_scan: true }); ElMessage.success(`${t('maintPartAdded')}: ${item.name}`) }
  }
  updatePartsCost(); scanDialogVisible.value = false
  ElMessage.success(`${t('maintAddedCount')} ${result.items.length} ${t('maintPartAdded')}`)
}

const addSparePartToForm = () => {
  if (!selectedSparePart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return
  const existing = maintForm.value.spare_parts.find(p => p.part_id === part.id)
  if (existing) { existing.quantity += 1 }
  else { maintForm.value.spare_parts.push({ part_id: part.id, part_number: part.part_number, name: part.name, unit_price: part.unit_price || 0, quantity: 1 }) }
  updatePartsCost(); selectedSparePart.value = null
}

const removeSparePart = (index) => { maintForm.value.spare_parts.splice(index, 1); updatePartsCost() }

const scanReturnPart = async () => {
  const serial = returnScanInput.value.trim()
  if (!serial || serial.length < 4) { ElMessage.warning(t('maintSerialMinLength')); return }
  returnScanLoading.value = true
  try {
    const info = await getPartBySerialNumber(serial)
    returnFoundInfo.value = info
    ElMessage.success(`${t('maintIdentified')}: ${info.name || info.part_number}`)
    returnPartSerial.value = info.serial_number; returnPartNumber.value = info.part_number
    returnPartName.value = info.name; selectedReturnPart.value = info.id; returnPartScrap.value = true
  } catch (e) { returnFoundInfo.value = null; returnPartSerial.value = serial; ElMessage.info(t('maintSerialNotFound')) }
  finally { returnScanLoading.value = false }
}

const clearReturnFound = () => {
  returnFoundInfo.value = null; returnScanInput.value = ''; returnPartSerial.value = ''
  returnPartNumber.value = ''; returnPartName.value = ''; selectedReturnPart.value = null
  returnPartQty.value = 1
}

const addFoundReturnPart = () => {
  if (!returnFoundInfo.value) return
  maintForm.value.return_parts.push({ part_id: returnFoundInfo.value.id, part_number: returnFoundInfo.value.part_number, name: returnFoundInfo.value.name, serial_number: returnFoundInfo.value.serial_number, unit_price: returnFoundInfo.value.unit_price || 0, quantity: returnPartQty.value, scrap_in: returnPartScrap.value, is_from_scan: true, history: returnFoundInfo.value.history })
  ElMessage.success(`${t('maintReturnAdded')}: ${returnFoundInfo.value.serial_number}`)
  clearReturnFound()
}

const onReturnPartSelect = () => {
  if (!selectedReturnPart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
  if (part) { returnPartNumber.value = part.part_number; returnPartName.value = part.name || part.part_number; returnPartScrap.value = true }
}

const addReturnPart = () => {
  if (!returnPartSerial.value) { ElMessage.warning(t('maintSerialPrompt')); return }
  const existing = maintForm.value.return_parts.find(p => p.serial_number === returnPartSerial.value)
  if (existing) { ElMessage.warning(`${t('maintSerialDuplicate')} ${returnPartSerial.value}`); return }
  let partNumber = returnPartNumber.value, partName = returnPartName.value || returnPartNumber.value, partId = null
  if (selectedReturnPart.value) {
    const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) { partId = part.id; partNumber = part.part_number; partName = part.name || part.part_number }
  }
  maintForm.value.return_parts.push({ part_id: partId, part_number: partNumber, name: partName, serial_number: returnPartSerial.value, quantity: returnPartQty.value, scrap_in: selectedReturnPart.value ? returnPartScrap.value : false, is_from_scan: false })
  ElMessage.success(`${t('maintReturnAdded')}: ${returnPartSerial.value}`)
  returnScanInput.value = ''; returnFoundInfo.value = null; selectedReturnPart.value = null
  returnPartSerial.value = ''; returnPartNumber.value = ''; returnPartName.value = ''
  returnPartQty.value = 1; returnPartScrap.value = true
}

const removeReturnPart = (index) => { maintForm.value.return_parts.splice(index, 1) }
const updatePartsCost = () => { maintForm.value.parts_cost = maintForm.value.spare_parts.reduce((sum, p) => sum + p.quantity * p.unit_price, 0) }

const filterMaintenances = () => {
  let result = [...maintenances.value]
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(m => m.device_name?.toLowerCase().includes(search) || m.maint_no?.toLowerCase().includes(search) || m.description?.toLowerCase().includes(search))
  }
  if (filterStatus.value) {
    if (filterStatus.value === 'overdue') result = result.filter(m => isOverdue(m))
    else result = result.filter(m => m.status === filterStatus.value)
  }
  if (filterPriority.value) result = result.filter(m => (m.priority || 'P3') === filterPriority.value)
  if (filterMaintType.value) result = result.filter(m => m.maint_type === filterMaintType.value)
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0]), endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(m => { const mt = dayjs(m.maint_time || m.created_at); return mt.isAfter(startDate) && mt.isBefore(endDate) })
  }
  if (sortBy.value) {
    switch (sortBy.value) {
      case 'maint_time_desc': result.sort((a, b) => dayjs(b.maint_time || b.created_at) - dayjs(a.maint_time || a.created_at)); break
      case 'maint_time_asc': result.sort((a, b) => dayjs(a.maint_time || a.created_at) - dayjs(b.maint_time || b.created_at)); break
      case 'total_cost_desc': result.sort((a, b) => ((b.parts_cost || 0) + (b.labor_cost || 0)) - ((a.parts_cost || 0) + (a.labor_cost || 0))); break
      case 'total_cost_asc': result.sort((a, b) => ((a.parts_cost || 0) + (a.labor_cost || 0)) - ((b.parts_cost || 0) + (b.labor_cost || 0))); break
    }
  }
  filteredMaintenances.value = result
}

const loadMaintenances = async () => {
  loading.value = true
  try {
    const data = await getMaintenances({ limit: 500 })
    maintenances.value = data.items || []; total.value = data.total || maintenances.value.length
    filterMaintenances()
  } catch (error) { ElMessage.error(t('maintLoadFailed')) }
  finally { loading.value = false }
}

const loadDevices = async () => {
  try { const data = await getDevices(); devices.value = data.items || [] }
  catch (error) { ElMessage.error(t('maintDeviceLoadFailed')) }
}

const addMaintenance = async () => {
  if (!maintForm.value.device_id) { ElMessage.warning(t('maintSelectDevicePrompt')); return }
  if (!maintForm.value.description) { ElMessage.warning(t('maintDescPrompt')); return }
  try {
    const device = devices.value.find(d => d.id === maintForm.value.device_id)
    const combinedParts = [...maintForm.value.spare_parts.map(p => ({ ...p, is_return: false })), ...maintForm.value.return_parts.map(p => ({ ...p, is_return: true }))]
    await createMaintenance({ ...maintForm.value, device_name: device?.name, parts_replaced: JSON.stringify(combinedParts) })
    for (const part of maintForm.value.spare_parts) {
      if (part.part_id && !part.is_from_scan) {
        await createMovement({ part_id: part.part_id, movement_type: 'out', quantity: part.quantity, serial_number: part.serial_number, reason: `${t('spareReasonMaintenanceReplace')} - ${maintForm.value.maint_type}`, operator: 'Web', reference: device?.name })
      }
    }
    for (const part of maintForm.value.return_parts) {
      if (part.scrap_in && part.part_id) {
        await createMovement({ part_id: part.part_id, movement_type: 'scrap_in', quantity: part.quantity, serial_number: part.serial_number, reason: t('spareReasonReturnPartScrap'), operator: 'Web', reference: device?.name })
      }
    }
    ElMessage.success(t('maintAddSuccess')); showAddDialog.value = false; resetForm(); loadMaintenances()
  } catch (error) { ElMessage.error(`${t('maintAddFailed')}: ${error.response?.data?.detail || error.message}`) }
}

const editMaintenance = (row) => {
  editMode.value = true
  maintForm.value = { id: row.id, device_id: row.device_id, maint_type: row.maint_type, spare_parts: [], return_parts: [], parts_cost: row.parts_cost || 0, labor_hours: row.labor_hours || 0, labor_cost: row.labor_cost || 0, vendor: row.vendor || '', description: row.description }
  showAddDialog.value = true
}

const updateMaintenance = async () => {
  if (!maintForm.value.description) { ElMessage.warning(t('maintDescPrompt')); return }
  try {
    const device = devices.value.find(d => d.id === maintForm.value.device_id)
    await updateMaintenanceApi(maintForm.value.id, { ...maintForm.value, device_name: device?.name, parts_replaced: JSON.stringify(maintForm.value.spare_parts) })
    ElMessage.success(t('maintUpdateSuccess')); showAddDialog.value = false; editMode.value = false; resetForm(); loadMaintenances()
  } catch (error) { ElMessage.error(t('maintUpdateFailed')) }
}

const deleteMaintenance = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('maintConfirmDeletePrompt')} "${row.maint_no}"?`, t('msgConfirmDelete'), { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' })
    await deleteMaintenanceApi(row.id); ElMessage.success(t('maintDeleteSuccess')); loadMaintenances()
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('maintDeleteFailed')) }
}

const resetForm = () => {
  maintForm.value = { device_id: null, maint_type: 'corrective', spare_parts: [], return_parts: [], parts_cost: 0, labor_hours: 0, labor_cost: 0, vendor: '', description: '' }
  selectedSparePart.value = null; sparePartOptions.value = []; currentFoundPart.value = null
  returnScanInput.value = ''; returnFoundInfo.value = null; selectedReturnPart.value = null
  returnPartSerial.value = ''; returnPartNumber.value = ''; returnPartName.value = ''
  returnPartQty.value = 1; returnPartScrap.value = true
}

onMounted(() => { loadMaintenances(); loadDevices() })
</script>

<style scoped>
.maint-no-badge, .metric-value, .chip-count, .table-count, .progress-percent, .sla-text, .cost-value, .cost-currency, .time-text, .priority-text {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

.maintenance-page {
  padding: 0;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f8fafc 0%, #e8f4fc 50%, #f0f7ff 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.06);
  position: relative;
  overflow: hidden;
}

.page-nav-bar::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894);
}

.nav-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
.nav-right { display: flex; gap: 8px; }

.nav-action-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 8px;
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
  color: white; border: none; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(9, 132, 227, 0.25);
}
.nav-action-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(9, 132, 227, 0.35); }
.nav-action-btn.secondary {
  background: rgba(255, 255, 255, 0.9); color: var(--text-secondary);
  border: 1px solid var(--border-default); box-shadow: none; padding: 8px 12px;
}
.nav-action-btn.secondary:hover { background: var(--bg-hover); color: var(--accent-primary); border-color: var(--accent-primary); }

.stats-dashboard {
  padding: 16px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(16px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }

.stat-card {
  position: relative; display: flex; align-items: center; gap: 12px;
  padding: 18px; background: rgba(255, 255, 255, 0.95);
  border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.8);
  cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); overflow: hidden;
}
.stat-card::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(9, 132, 227, 0.05) 100%);
  opacity: 0; transition: opacity 0.3s;
}
.stat-card:hover::before { opacity: 1; }
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 8px 32px rgba(0, 48, 135, 0.12); }

.card-content { display: flex; align-items: center; gap: 14px; width: 100%; }
.card-icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; transition: transform 0.3s;
}
.stat-card:hover .card-icon { transform: scale(1.05); }

.stat-card.total .card-icon { background: linear-gradient(135deg, rgba(9, 132, 227, 0.15) 0%, rgba(9, 132, 227, 0.08) 100%); color: #0984e3; }
.stat-card.repairing .card-icon { background: linear-gradient(135deg, rgba(225, 112, 85, 0.2) 0%, rgba(225, 112, 85, 0.1) 100%); color: #e17055; }
.stat-card.verifying .card-icon { background: linear-gradient(135deg, rgba(116, 185, 255, 0.2) 0%, rgba(116, 185, 255, 0.1) 100%); color: #74b9ff; }
.stat-card.completed .card-icon { background: linear-gradient(135deg, rgba(0, 184, 148, 0.2) 0%, rgba(0, 184, 148, 0.1) 100%); color: #00b894; }
.stat-card.overdue .card-icon { background: linear-gradient(135deg, rgba(214, 48, 49, 0.2) 0%, rgba(214, 48, 49, 0.1) 100%); color: #d63031; }

.card-body { flex: 1; }
.metric-value {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 28px; font-weight: 700; color: var(--text-primary);
  line-height: 1; letter-spacing: -0.02em;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
}
.metric-label { font-size: 12px; color: var(--text-tertiary); margin-top: 6px; font-weight: 500; }

.card-trend { width: 24px; height: 24px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 12px; }
.card-trend.stable { background: rgba(9, 132, 227, 0.1); color: #0984e3; }
.card-trend.warning { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.card-trend.success { background: rgba(0, 184, 148, 0.1); color: #00b894; }
.card-trend.info { background: rgba(116, 185, 255, 0.1); color: #74b9ff; }

.card-progress { width: 24px; height: 24px; position: relative; }
.progress-ring {
  width: 24px; height: 24px; border-radius: 50%;
  background: conic-gradient(#e17055 calc(var(--percent) * 1%), rgba(225, 112, 85, 0.2) 0);
}
.progress-ring::after { content: ''; width: 16px; height: 16px; border-radius: 50%; background: white; }

.filter-section {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 12px rgba(0, 48, 135, 0.06);
}

.filter-toolbar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.search-box { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 12px; color: var(--text-tertiary); font-size: 14px; z-index: 1; }
.search-input { width: 240px; }
.search-input :deep(.el-input__wrapper) {
  padding-left: 36px; background: rgba(255, 255, 255, 0.95);
  border-radius: 8px; border: 1px solid var(--border-default); box-shadow: none; transition: all 0.25s;
}
.search-input :deep(.el-input__wrapper:hover) { border-color: var(--accent-primary); }
.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary); box-shadow: 0 0 0 3px rgba(9, 132, 227, 0.15);
}

.status-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.status-chip {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  background: rgba(255, 255, 255, 0.9); border-radius: 8px;
  border: 1px solid var(--border-default); cursor: pointer;
  transition: all 0.25s ease; position: relative; overflow: hidden;
}
.status-chip::before {
  content: ''; position: absolute; bottom: 0; left: 50%; right: 50%;
  height: 2px; background: currentColor; transition: all 0.25s ease;
}
.status-chip:hover::before, .status-chip.active::before { left: 0; right: 0; }
.status-chip:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0, 48, 135, 0.1); }
.status-chip.active { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }

.chip-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.chip-label { font-size: 12px; font-weight: 500; color: var(--text-secondary); }
.status-chip.active .chip-label { color: #0984e3; }
.chip-count {
  font-size: 11px; font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--text-tertiary); padding: 2px 6px; background: rgba(0, 48, 135, 0.05); border-radius: 4px;
}

.status-chip.chip-created .chip-dot { background: #0984e3; }
.status-chip.chip-diagnosing .chip-dot { background: #0984e3; }
.status-chip.chip-repairing .chip-dot { background: #e17055; }
.status-chip.chip-verifying .chip-dot { background: #74b9ff; }
.status-chip.chip-completed .chip-dot { background: #00b894; }
.status-chip.chip-overdue .chip-dot { background: #d63031; }
.status-chip.chip-created:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); }
.status-chip.chip-diagnosing:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); }
.status-chip.chip-repairing:hover { background: rgba(225, 112, 85, 0.08); border-color: rgba(225, 112, 85, 0.3); }
.status-chip.chip-verifying:hover { background: rgba(116, 185, 255, 0.08); border-color: rgba(116, 185, 255, 0.3); }
.status-chip.chip-completed:hover { background: rgba(0, 184, 148, 0.12); border-color: rgba(0, 184, 148, 0.4); }
.status-chip.chip-overdue:hover { background: rgba(214, 48, 49, 0.08); border-color: rgba(214, 48, 49, 0.3); }

.more-filters { display: flex; gap: 8px; margin-left: auto; }
.more-filters :deep(.el-select .el-input__wrapper) { background: rgba(255, 255, 255, 0.95); border-radius: 8px; border: 1px solid var(--border-default); box-shadow: none; }
.more-filters :deep(.el-date-editor) { background: rgba(255, 255, 255, 0.95); border-radius: 8px; border: 1px solid var(--border-default); box-shadow: none; }

.data-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid rgba(0, 48, 135, 0.08); }
.table-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); letter-spacing: 0.03em; }
.table-count { font-size: 12px; color: var(--text-tertiary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

.enterprise-table { width: 100%; }
.enterprise-table :deep(.el-table__inner-wrapper::before) { display: none; }
.enterprise-table :deep(.el-table__header-wrapper) { border-bottom: 2px solid rgba(0, 48, 135, 0.1); }
.enterprise-table :deep(th.el-table__cell) {
  background: transparent; font-size: 11px; font-weight: 600; color: var(--text-tertiary);
  letter-spacing: 0.03em; padding: 12px 0; border-bottom: none;
}
.enterprise-table :deep(td.el-table__cell) { border-bottom: 1px solid rgba(0, 48, 135, 0.06); padding: 10px 0; background: transparent; }
.enterprise-table :deep(.el-table__row) { transition: all 0.25s ease; background: transparent; }
.enterprise-table :deep(.el-table__row:hover > td) { background: rgba(9, 132, 227, 0.04) !important; }
.enterprise-table :deep(.overdue-row > td) { background: rgba(239, 68, 68, 0.04) !important; }
.enterprise-table :deep(.cancelled-row) { opacity: 0.6; }

.maint-no-link { display: flex; align-items: center; gap: 8px; color: var(--accent-primary); text-decoration: none; transition: all 0.25s; }
.maint-no-link:hover { color: var(--accent-secondary); }
.maint-no-badge {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600; font-size: 13px; padding: 4px 8px; background: rgba(9, 132, 227, 0.08);
  border-radius: 6px; transition: all 0.25s;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; letter-spacing: 0.02em;
}
.maint-no-link:hover .maint-no-badge { background: rgba(9, 132, 227, 0.15); }
.link-arrow { opacity: 0; font-size: 12px; transition: all 0.25s; color: var(--accent-primary); }
.maint-no-link:hover .link-arrow { opacity: 1; transform: translateX(4px); }

.status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500; background: rgba(255, 255, 255, 0.95); border: 1px solid; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.status-text { letter-spacing: 0.02em; }
.status-badge.created { border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }
.status-badge.created .status-dot { background: #0984e3; }
.status-badge.diagnosing { border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }
.status-badge.diagnosing .status-dot { background: #0984e3; }
.status-badge.repairing { border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.status-badge.repairing .status-dot { background: #e17055; }
.status-badge.verifying { border-color: rgba(116, 185, 255, 0.3); color: #74b9ff; }
.status-badge.verifying .status-dot { background: #74b9ff; }
.status-badge.completed { border-color: rgba(0, 184, 148, 0.4); color: #00b894; }
.status-badge.completed .status-dot { background: #00b894; }
.status-badge.cancelled { border-color: rgba(45, 52, 54, 0.3); color: #636e72; }
.status-badge.cancelled .status-dot { background: #636e72; }

.priority-badge { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.priority-icon { font-size: 12px; }
.priority-badge.P1 { background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.08) 100%); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; }
.priority-badge.P2 { background: linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(251, 191, 36, 0.08) 100%); border: 1px solid rgba(251, 191, 36, 0.3); color: #f59e0b; }
.priority-badge.P3 { background: linear-gradient(135deg, rgba(9, 132, 227, 0.12) 0%, rgba(9, 132, 227, 0.06) 100%); border: 1px solid rgba(9, 132, 227, 0.25); color: #0984e3; }
.priority-badge.P4 { background: linear-gradient(135deg, rgba(0, 184, 148, 0.12) 0%, rgba(0, 184, 148, 0.06) 100%); border: 1px solid rgba(0, 184, 148, 0.25); color: #00b894; }

.device-cell { display: flex; align-items: center; gap: 8px; }
.device-icon { font-size: 14px; color: var(--text-tertiary); }
.device-name { font-size: 13px; color: var(--text-secondary); }

.owner-cell { display: flex; align-items: center; gap: 8px; }
.owner-avatar {
  width: 24px; height: 24px; border-radius: 6px;
  background: linear-gradient(135deg, #0984e3, #74b9ff); color: white;
  font-size: 11px; font-weight: 600; display: flex; align-items: center; justify-content: center;
}
.owner-name { font-size: 13px; color: var(--text-secondary); }

.type-badge { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500; }
.type-badge.preventive { background: rgba(0, 184, 148, 0.08); color: #00b894; }
.type-badge.corrective { background: rgba(225, 112, 85, 0.08); color: #e17055; }
.type-badge.upgrade { background: rgba(9, 132, 227, 0.08); color: #0984e3; }
.type-badge.emergency { background: rgba(239, 68, 68, 0.08); color: #ef4444; }
.type-badge.other { background: rgba(45, 52, 54, 0.08); color: #636e72; }

.progress-cell { display: flex; align-items: center; gap: 10px; }
.progress-bar-bg { width: 70px; height: 6px; background: rgba(0, 48, 135, 0.08); border-radius: 3px; overflow: hidden; }
.progress-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.progress-bar-fill.created { background: linear-gradient(90deg, #74b9ff, #a8d8ff); }
.progress-bar-fill.diagnosing { background: linear-gradient(90deg, #0984e3, #74b9ff); }
.progress-bar-fill.repairing { background: linear-gradient(90deg, #e17055, #fab1a0); }
.progress-bar-fill.verifying { background: linear-gradient(90deg, #74b9ff, #a8d8ff); }
.progress-bar-fill.completed { background: linear-gradient(90deg, #00b894, #55efc4); }
.progress-bar-fill.cancelled { background: linear-gradient(90deg, #636e72, #b2bec3); }
.progress-percent { font-size: 11px; color: var(--text-tertiary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-weight: 500; }

.sla-cell { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.sla-cell.overdue { color: #ef4444; background: rgba(239, 68, 68, 0.08); padding: 2px 8px; border-radius: 6px; }
.sla-cell.critical { color: #f59e0b; }
.sla-icon { font-size: 12px; }

.cost-cell { display: flex; align-items: center; gap: 2px; }
.cost-currency { font-size: 11px; color: var(--text-tertiary); }
.cost-value { font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 13px; color: var(--text-secondary); font-weight: 500; }

.time-cell { display: flex; align-items: center; gap: 8px; }
.time-icon { font-size: 13px; color: var(--text-tertiary); }
.time-text { font-size: 12px; color: var(--text-secondary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

.action-group { display: flex; gap: 4px; }
.action-btn {
  width: 28px; height: 28px; border-radius: 6px; border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.9); color: var(--text-tertiary);
  cursor: pointer; transition: all 0.25s ease; display: flex; align-items: center; justify-content: center;
}
.action-btn:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0, 48, 135, 0.15); }
.action-btn.view:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.2); color: #0984e3; }
.action-btn.advance:hover { background: rgba(225, 112, 85, 0.08); border-color: rgba(225, 112, 85, 0.2); color: #e17055; }
.action-btn.delete:hover { background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.2); color: #ef4444; }

.pagination-bar { margin-top: 16px; padding-top: 12px; border-top: 1px solid rgba(0, 48, 135, 0.06); display: flex; justify-content: flex-end; }
.pagination-bar :deep(.el-pagination) { gap: 8px; }
.pagination-bar :deep(.el-pagination button), .pagination-bar :deep(.el-pager li) {
  background: rgba(255, 255, 255, 0.95); border-radius: 6px; border: 1px solid var(--border-default);
  font-size: 12px; font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.pagination-bar :deep(.el-pager li.is-active) { background: linear-gradient(135deg, #0984e3, #74b9ff); border-color: transparent; color: white; }

.edit-dialog-content { display: flex; flex-direction: column; gap: 16px; }
.form-section { background: rgba(0, 48, 135, 0.04); border-radius: 10px; padding: 16px; border: 1px solid rgba(0, 48, 135, 0.08); }
.form-section-title { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; }

.spare-parts-section { width: 100%; }
.spare-search { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.spare-tip { font-size: 12px; color: var(--el-text-color-secondary); padding: 4px 8px; background: var(--el-fill-color-light); border-radius: 4px; }
.selected-parts { margin-top: 12px; }
.no-parts-tip { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: #f5f7fa; border-radius: 4px; color: #909399; font-size: 13px; margin-top: 12px; }
.parts-summary { margin-top: 10px; padding: 8px 12px; background: #f5f7fa; border-radius: 4px; text-align: right; }
.total-cost { font-weight: 600; color: #409EFF; font-size: 16px; }
.spare-option { display: flex; align-items: center; gap: 12px; }
.spare-number { font-weight: 500; color: #409EFF; }
.spare-name { color: #606266; }
.spare-stock { font-size: 12px; color: #909399; }
.spare-stock.low { color: #F56C6C; font-weight: 500; }

.return-parts-section { width: 100%; }
.return-found-info { margin-bottom: 16px; }
.found-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.found-actions { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
.return-manual-area { margin-bottom: 12px; }
.return-manual-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.return-manual-tip { font-size: 12px; color: var(--el-text-color-secondary); padding: 4px 8px; background: var(--el-fill-color-light); border-radius: 4px; }
.return-parts-table { margin-top: 8px; }
.scrap-label { margin-left: 8px; font-size: 12px; color: #909399; }
.scrap-label.no-id { color: #E6A23C; }
.return-tip { margin-top: 10px; padding: 8px 12px; background: #fdf6ec; border-radius: 4px; color: #909399; font-size: 12px; }
.no-return-tip { margin-top: 8px; }

.scan-action-bar {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  background: linear-gradient(135deg, var(--color-gb) 0%, var(--color-gb-mid) 100%);
  border-radius: var(--radius-md); margin-bottom: 16px;
}
.scan-action-bar.return { background: linear-gradient(135deg, #636e72 0%, #4a5455 100%); }
.scan-action-bar .scan-btn {
  background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.3);
  color: #fff; font-weight: 600; height: 36px; border-radius: 8px; transition: all 0.2s;
}
.scan-action-bar .scan-btn:hover { background: rgba(255,255,255,0.25); transform: translateY(-1px); }
.scan-tip-badge { display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: rgba(255,255,255,0.1); border-radius: 4px; color: rgba(255,255,255,0.9); font-size: 12px; }

@media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .filter-toolbar { flex-direction: column; align-items: stretch; }
  .status-chips { justify-content: center; }
  .more-filters { justify-content: center; margin-left: 0; }
  .page-nav-bar { flex-direction: column; gap: 12px; }
  .nav-right { width: 100%; justify-content: center; }
}

.dark .maintenance-page { background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #161b22 100%); }
.dark .page-nav-bar { background: rgba(22, 27, 34, 0.9); border-color: rgba(48, 54, 61, 0.8); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); }
.dark .page-nav-bar::before { background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894); }
.dark .page-title { color: #f0f6fc; }
.dark .nav-action-btn { background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%); }
.dark .nav-action-btn.secondary { background: rgba(48, 54, 61, 0.8); color: #8b949e; border-color: #30363d; }
.dark .nav-action-btn.secondary:hover { background: rgba(9, 132, 227, 0.15); border-color: #0984e3; color: #58a6ff; }
.dark .stats-dashboard { background: rgba(22, 27, 34, 0.85); border-color: rgba(48, 54, 61, 0.6); box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4); }
.dark .stat-card { background: rgba(13, 17, 23, 0.95); border-color: rgba(48, 54, 61, 0.6); }
.dark .stat-card:hover { background: rgba(22, 27, 34, 0.95); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5); }
.dark .metric-value { color: #f0f6fc; }
.dark .metric-label { color: #8b949e; }
.dark .card-trend.stable { background: rgba(9, 132, 227, 0.2); color: #58a6ff; }
.dark .card-trend.warning { background: rgba(239, 68, 68, 0.2); color: #f85149; }
.dark .card-trend.success { background: rgba(0, 184, 148, 0.2); color: #3fb950; }
.dark .card-trend.info { background: rgba(116, 185, 255, 0.2); color: #74b9ff; }
.dark .progress-ring { background: conic-gradient(#e17055 calc(var(--percent) * 1%), rgba(225, 112, 85, 0.3) 0); }
.dark .progress-ring::after { background: #0d1117; }
.dark .filter-section { background: rgba(22, 27, 34, 0.85); border-color: rgba(48, 54, 61, 0.6); box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3); }
.dark .search-input :deep(.el-input__wrapper) { background: rgba(13, 17, 23, 0.95); border-color: #30363d; }
.dark .search-input :deep(.el-input__wrapper:hover), .dark .search-input :deep(.el-input__wrapper.is-focus) { border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15); }
.dark .search-icon { color: #8b949e; }
.dark .status-chip { background: rgba(13, 17, 23, 0.9); border-color: #30363d; }
.dark .status-chip:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); }
.dark .chip-label { color: #8b949e; }
.dark .status-chip.active { background: rgba(88, 166, 255, 0.15); border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .status-chip.active .chip-label { color: #58a6ff; }
.dark .chip-count { background: rgba(48, 54, 61, 0.3); color: #8b949e; }
.dark .more-filters :deep(.el-select .el-input__wrapper), .dark .more-filters :deep(.el-date-editor) { background: rgba(13, 17, 23, 0.95); border-color: #30363d; }
.dark .status-badge { background: rgba(13, 17, 23, 0.9); }
.dark .status-badge.created { border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .status-badge.created .status-dot { background: #58a6ff; }
.dark .status-badge.diagnosing { border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .status-badge.diagnosing .status-dot { background: #58a6ff; }
.dark .status-badge.repairing { border-color: rgba(225, 112, 85, 0.4); color: #e17055; }
.dark .status-badge.repairing .status-dot { background: #e17055; }
.dark .status-badge.verifying { border-color: rgba(116, 185, 255, 0.4); color: #74b9ff; }
.dark .status-badge.verifying .status-dot { background: #74b9ff; }
.dark .status-badge.completed { border-color: rgba(63, 185, 80, 0.4); color: #3fb950; }
.dark .status-badge.completed .status-dot { background: #3fb950; }
.dark .status-badge.cancelled { border-color: rgba(139, 148, 158, 0.4); color: #8b949e; }
.dark .status-badge.cancelled .status-dot { background: #8b949e; }
.dark .priority-badge.P1 { background: rgba(248, 81, 73, 0.15); border-color: rgba(248, 81, 73, 0.4); color: #f85149; }
.dark .priority-badge.P2 { background: rgba(210, 153, 34, 0.15); border-color: rgba(210, 153, 34, 0.4); color: #d29922; }
.dark .priority-badge.P3 { background: rgba(88, 166, 255, 0.15); border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .priority-badge.P4 { background: rgba(63, 185, 80, 0.15); border-color: rgba(63, 185, 80, 0.4); color: #3fb950; }
.dark .type-badge.preventive { background: rgba(63, 185, 80, 0.15); color: #3fb950; }
.dark .type-badge.corrective { background: rgba(225, 112, 85, 0.15); color: #e17055; }
.dark .type-badge.upgrade { background: rgba(88, 166, 255, 0.15); color: #58a6ff; }
.dark .type-badge.emergency { background: rgba(248, 81, 73, 0.15); color: #f85149; }
.dark .type-badge.other { background: rgba(139, 148, 158, 0.15); color: #8b949e; }
.dark .data-section { background: rgba(22, 27, 34, 0.85); border-color: rgba(48, 54, 61, 0.6); box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4); }
.dark .table-header { border-bottom-color: rgba(48, 54, 61, 0.6); }
.dark .table-title { color: #8b949e; }
.dark .table-count { color: #6e7681; }
.dark .enterprise-table :deep(.el-table__header-wrapper) { border-bottom-color: rgba(48, 54, 61, 0.6); }
.dark .enterprise-table :deep(th.el-table__cell) { color: #8b949e; }
.dark .enterprise-table :deep(td.el-table__cell) { border-bottom-color: rgba(48, 54, 61, 0.3); }
.dark .enterprise-table :deep(.el-table__row:hover > td) { background: rgba(88, 166, 255, 0.08) !important; }
.dark .enterprise-table :deep(.overdue-row > td) { background: rgba(248, 81, 73, 0.08) !important; }
.dark .maint-no-link { color: #58a6ff; }
.dark .maint-no-badge { background: rgba(88, 166, 255, 0.15); }
.dark .maint-no-link:hover .maint-no-badge { background: rgba(88, 166, 255, 0.25); }
.dark .device-name { color: #c9d1d9; }
.dark .owner-name { color: #8b949e; }
.dark .owner-avatar { background: linear-gradient(135deg, #0984e3, #74b9ff); }
.dark .progress-bar-bg { background: rgba(48, 54, 61, 0.5); }
.dark .progress-percent { color: #8b949e; }
.dark .sla-cell { color: #8b949e; }
.dark .sla-cell.overdue { background: rgba(248, 81, 73, 0.15); color: #f85149; }
.dark .sla-cell.critical { color: #d29922; }
.dark .cost-value { color: #8b949e; }
.dark .cost-currency { color: #6e7681; }
.dark .time-text { color: #8b949e; }
.dark .pagination-bar { border-top-color: rgba(48, 54, 61, 0.3); }
.dark .pagination-bar :deep(.el-pagination button), .dark .pagination-bar :deep(.el-pager li) { background: rgba(13, 17, 23, 0.95); border-color: #30363d; color: #8b949e; }
.dark .pagination-bar :deep(.el-pager li.is-active) { background: linear-gradient(135deg, #0984e3, #74b9ff); color: white; }
.dark .action-btn { background: rgba(13, 17, 23, 0.9); color: #8b949e; border-color: transparent; }
.dark .action-btn:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4); }
.dark .action-btn.view:hover { background: rgba(88, 166, 255, 0.15); border-color: rgba(88, 166, 255, 0.3); color: #58a6ff; }
.dark .action-btn.advance:hover { background: rgba(225, 112, 85, 0.15); border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.dark .action-btn.delete:hover { background: rgba(248, 81, 73, 0.15); border-color: rgba(248, 81, 73, 0.3); color: #f85149; }
.dark .form-section { background: rgba(13, 17, 23, 0.6); border-color: rgba(48, 54, 61, 0.4); }
.dark .form-section-title { color: #8b949e; }
.dark .no-parts-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }
.dark .parts-summary { background: rgba(13, 17, 23, 0.6); }
.dark .spare-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }
.dark .return-manual-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }
.dark .return-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }
</style>

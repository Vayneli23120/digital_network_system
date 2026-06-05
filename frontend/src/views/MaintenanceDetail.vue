<template>
  <div class="maintenance-report-page">
    <!-- 顶部精简进度条 -->
    <section class="progress-bar-header">
      <div class="progress-steps">
        <div class="step-node completed">
          <span class="node-dot">●</span>
          <span class="node-label">{{ t('workflowStepCreate') }}</span>
        </div>
        <div class="step-line completed"></div>
        <div class="step-node" :class="{ completed: isStepCompleted('repairing'), active: statusInfo.status === 'repairing' }">
          <span class="node-dot">{{ isStepCompleted('repairing') ? '●' : (statusInfo.status === 'repairing' ? '●' : '○') }}</span>
          <span class="node-label">{{ t('workflowStepRepair') }}</span>
        </div>
        <div class="step-line" :class="{ completed: isStepCompleted('verifying') }"></div>
        <div class="step-node" :class="{ completed: isStepCompleted('verifying'), active: statusInfo.status === 'verifying' }">
          <span class="node-dot">{{ isStepCompleted('verifying') ? '●' : '○' }}</span>
          <span class="node-label">{{ t('workflowStepVerify') }}</span>
        </div>
        <div class="step-line" :class="{ completed: statusInfo.status === 'completed' }"></div>
        <div class="step-node" :class="{ completed: statusInfo.status === 'completed', active: statusInfo.status === 'completed' }">
          <span class="node-dot">{{ statusInfo.status === 'completed' ? '●' : '○' }}</span>
          <span class="node-label">{{ t('workflowStepComplete') }}</span>
        </div>
      </div>
      <div class="progress-info">
        <span class="report-no">{{ maintenance.maint_no }}</span>
        <el-tag :type="getStatusTagClass(statusInfo.status)" size="small">{{ statusInfo.status_label }}</el-tag>
        <span class="progress-percent">{{ calculateProgress() }}%</span>
        <span class="progress-estimate" v-if="statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'">
          {{ t('maintEstimateComplete') }}: {{ estimateCompletionTime() }}
        </span>
      </div>
    </section>

    <!-- 维修工单报告头部 -->
    <section class="report-header-card">
      <div class="header-title-row">
        <div class="title-area">
          <el-icon class="report-icon"><Setting /></el-icon>
          <h1 class="report-title">{{ t('maintReportTitle') }}</h1>
        </div>
        <div class="header-tags">
          <span class="maint-no-text">{{ maintenance.maint_no }}</span>
          <el-tag :type="getMaintTypeTagClass(maintenance.maint_type)" size="default">{{ getMaintTypeText(maintenance.maint_type) }}</el-tag>
          <el-tag :type="getPriorityTagClass(statusInfo.priority)" size="default">{{ statusInfo.priority }}</el-tag>
        </div>
      </div>

      <!-- 设备信息 -->
      <div class="info-block">
        <div class="info-row">
          <div class="info-item">
            <span class="info-label">{{ t('deviceName') }}:</span>
            <router-link :to="`/devices/${maintenance.device_id}`" class="info-value link">{{ maintenance.device_name }}</router-link>
          </div>
          <div class="info-item">
            <span class="info-label">IP:</span>
            <span class="info-value">{{ device?.ip || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('maintDetailDeviceInfo') }}:</span>
            <el-tag :type="device?.status === 'online' ? 'success' : 'info'" size="small">
              <span class="status-dot">●</span> {{ device?.status === 'online' ? t('statusOnline') : t('statusOffline') }}
            </el-tag>
          </div>
        </div>
        <div class="info-row">
          <div class="info-item">
            <span class="info-label">{{ t('deviceType') }}:</span>
            <span class="info-value">{{ device?.device_type || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('deviceLocation') }}:</span>
            <span class="info-value">{{ device?.location || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="separator-line"></div>

      <!-- 关联故障 -->
      <div class="info-block fault-block" v-if="maintenance.fault_id">
        <div class="info-row">
          <div class="info-item">
            <span class="info-label">{{ t('maintRelatedFault') }}:</span>
            <router-link :to="`/faults/${maintenance.fault_id}`" class="info-value link fault-link">
              {{ maintenance.fault?.fault_no || maintenance.fault_no || `FLT-${maintenance.fault_id}` }}
            </router-link>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('faultDescription') }}:</span>
            <span class="info-value">{{ maintenance.fault?.description || maintenance.fault_reason || '-' }}</span>
          </div>
        </div>
      </div>
      <div class="info-block fault-block" v-else>
        <div class="info-row">
          <div class="info-item">
            <span class="info-label">{{ t('maintRelatedFault') }}:</span>
            <span class="info-value muted">{{ t('maintNoRelatedFault') }}</span>
          </div>
        </div>
      </div>

      <div class="separator-line"></div>

      <!-- 维修说明 -->
      <div class="info-block description-block">
        <div class="description-label">{{ t('maintDescription') }}:</div>
        <div class="description-content">
          {{ maintenance.description || t('maintDetailNoDesc') }}
        </div>
      </div>

      <div class="separator-line"></div>

      <!-- 关键指标表格 -->
      <div class="metrics-table">
        <div class="metrics-row">
          <div class="metric-cell">
            <span class="metric-label">{{ t('maintCurrentOwner') }}</span>
            <span class="metric-value">{{ statusInfo.current_owner || '-' }}</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">{{ t('maintDetailHours') }}</span>
            <span class="metric-value">{{ maintenance.labor_hours || 0 }} {{ t('maintDetailHoursUnit') }}</span>
          </div>
          <div class="metric-cell highlight">
            <span class="metric-label">{{ t('maintTotalCost') }}</span>
            <span class="metric-value cost">{{ formatCurrency(totalCost) }}</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">{{ t('maintDetailVendor') }}</span>
            <span class="metric-value">{{ maintenance.vendor || '-' }}</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">{{ t('maintCreatedAt') }}</span>
            <span class="metric-value">{{ formatDateTimeShort(maintenance.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="header-actions">
        <button class="action-btn secondary" @click="handleExport">
          <el-icon><Download /></el-icon>
          {{ t('maintExportPDF') }}
        </button>
        <button class="action-btn secondary" @click="handlePrint">
          <el-icon><Printer /></el-icon>
          {{ t('maintPrint') }}
        </button>
        <button class="action-btn primary" @click="openEditDialog" v-if="canEdit">
          <el-icon><Edit /></el-icon>
          {{ t('actionEdit') }}
        </button>
      </div>
    </section>

    <!-- 一、备件与成本（Tab切换） -->
    <section class="report-section">
      <div class="section-header">
        <span class="section-number">{{ t('maintSectionOne') }}</span>
        <span class="section-title">{{ t('maintPartsAndCost') }}</span>
      </div>
      <div class="section-content">
        <div class="tab-switcher">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'parts' }"
            @click="activeTab = 'parts'"
          >
            {{ t('maintSparePartsSection') }}
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'cost' }"
            @click="activeTab = 'cost'"
          >
            {{ t('maintCostAnalysis') }}
          </button>
        </div>

        <!-- Tab: 备件清单 -->
        <div class="tab-content" v-show="activeTab === 'parts'">
          <div class="parts-table-wrapper" v-if="allPartsList.length > 0">
            <table class="parts-table">
              <thead>
                <tr>
                  <th width="60">{{ t('maintColSerialNumberShort') }}</th>
                  <th width="80">{{ t('maintColType') }}</th>
                  <th width="120">{{ t('maintColSerialNumber') }}</th>
                  <th>{{ t('maintColName') }}</th>
                  <th width="120">{{ t('maintColModel') }}</th>
                  <th width="80">{{ t('maintColQuantity') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(part, idx) in sparePartsList" :key="'spare-' + idx">
                  <td class="cell-index">{{ idx + 1 }}</td>
                  <td class="cell-type">
                    <span class="type-tag replace">{{ t('maintTypeReplace') }}</span>
                  </td>
                  <td class="cell-sn">{{ part.serial_number || '-' }}</td>
                  <td class="cell-name">{{ part.name }}</td>
                  <td class="cell-model">{{ part.part_number || '-' }}</td>
                  <td class="cell-qty">{{ part.quantity || 1 }}</td>
                </tr>
                <tr v-for="(part, idx) in returnPartsList" :key="'return-' + idx" class="return-row">
                  <td class="cell-index">{{ sparePartsList.length + idx + 1 }}</td>
                  <td class="cell-type">
                    <span class="type-tag return">{{ t('maintTypeReturn') }}</span>
                  </td>
                  <td class="cell-sn">{{ part.serial_number || '-' }}</td>
                  <td class="cell-name">{{ part.name }}</td>
                  <td class="cell-model">{{ part.part_number || '-' }}</td>
                  <td class="cell-qty">{{ part.quantity || 1 }}</td>
                </tr>
              </tbody>
            </table>
            <div class="parts-summary">
              <span class="summary-item">
                <span class="summary-label">{{ t('maintReplaceParts') }}:</span>
                <span class="summary-value">{{ sparePartsList.length }}{{ t('maintColRecords') }}</span>
                <span class="summary-cost">{{ formatCurrency(maintenance.parts_cost || 0) }}</span>
              </span>
              <span class="summary-divider">│</span>
              <span class="summary-item">
                <span class="summary-label">{{ t('maintReturnParts') }}:</span>
                <span class="summary-value">{{ returnPartsList.length }}{{ t('maintColRecords') }}</span>
                <span class="summary-status">{{ t('maintScrapedIn') }}</span>
              </span>
            </div>
          </div>
          <div class="empty-state" v-else>
            <el-icon><Box /></el-icon>
            <span>{{ t('maintDetailNoSpare') }}</span>
          </div>
        </div>

        <!-- Tab: 成本分析 -->
        <div class="tab-content" v-show="activeTab === 'cost'">
          <div class="cost-analysis">
            <div class="cost-total">
              <span class="cost-total-label">{{ t('maintTotalCost') }}</span>
              <span class="cost-total-value">{{ formatCurrency(totalCost) }}</span>
            </div>
            <div class="cost-breakdown">
              <div class="cost-item">
                <div class="cost-row">
                  <span class="cost-label">{{ t('maintDetailPartsCost') }}</span>
                  <span class="cost-amount">{{ formatCurrency(maintenance.parts_cost || 0) }}</span>
                  <span class="cost-percent">{{ partsCostPercent }}%</span>
                </div>
                <div class="cost-bar">
                  <div class="bar-fill parts" :style="{ width: partsCostPercent + '%' }"></div>
                </div>
              </div>
              <div class="cost-item">
                <div class="cost-row">
                  <span class="cost-label">{{ t('maintDetailLaborCost') }}</span>
                  <span class="cost-amount">{{ formatCurrency(maintenance.labor_cost || 0) }}</span>
                  <span class="cost-percent">{{ laborCostPercent }}%</span>
                </div>
                <div class="cost-bar">
                  <div class="bar-fill labor" :style="{ width: laborCostPercent + '%' }"></div>
                </div>
              </div>
            </div>
            <div class="cost-detail">
              <div class="detail-row">
                <span class="detail-label">{{ t('maintLaborHours') }}:</span>
                <span class="detail-value">{{ maintenance.labor_hours || 0 }} {{ t('maintDetailHoursUnit') }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('maintLaborRate') }}:</span>
                <span class="detail-value">{{ formatCurrency(laborRate) }}/{{ t('maintDetailHoursUnit') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 二、验证确认 -->
    <section class="report-section">
      <div class="section-header">
        <span class="section-number">{{ t('maintSectionTwo') }}</span>
        <span class="section-title">{{ t('maintVerificationSection') }}</span>
      </div>
      <div class="section-content">
        <div class="verification-card">
          <div class="verification-status">
            <span class="status-label">{{ t('maintVerificationStatus') }}:</span>
            <span class="status-value" :class="verificationStatusClass">
              <span class="status-icon">{{ verificationStatusIcon }}</span>
              {{ verificationStatusLabel }}
            </span>
          </div>

          <div class="separator-line light"></div>

          <div class="verification-result" v-if="statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'">
            <span class="result-label">{{ t('maintVerificationResult') }}:</span>
            <div class="result-buttons">
              <button
                class="result-btn"
                :class="{ selected: editForm.verification_result === 'passed' }"
                @click="editForm.verification_result = 'passed'"
              >
                {{ t('maintVerificationPassed') }}
              </button>
              <button
                class="result-btn partial"
                :class="{ selected: editForm.verification_result === 'partial' }"
                @click="editForm.verification_result = 'partial'"
              >
                {{ t('maintVerificationPartial') }}
              </button>
              <button
                class="result-btn fail"
                :class="{ selected: editForm.verification_result === 'failed' }"
                @click="editForm.verification_result = 'failed'"
              >
                {{ t('maintVerificationFailed') }}
              </button>
            </div>
          </div>

          <div class="verification-result-display" v-else>
            <span class="result-label">{{ t('maintVerificationResult') }}:</span>
            <el-tag :type="getVerificationTagType(maintenance.verification_result)" size="default">
              {{ getVerificationResultText(maintenance.verification_result) }}
            </el-tag>
          </div>

          <div class="verification-notes">
            <span class="notes-label">{{ t('maintVerificationNotes') }}:</span>
            <div class="notes-content" v-if="maintenance.verification_notes">
              {{ maintenance.verification_notes }}
            </div>
            <div class="notes-input" v-else-if="statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'">
              <el-input
                v-model="editForm.verification_notes"
                type="textarea"
                :rows="3"
                :placeholder="t('maintVerificationNotesPlaceholder')"
              />
            </div>
            <div class="notes-placeholder" v-else>
              {{ t('maintNoVerificationNotes') }}
            </div>
          </div>

          <div class="verification-signature">
            <div class="signature-item">
              <span class="signature-label">{{ t('maintVerifier') }}:</span>
              <span class="signature-value">{{ maintenance.verifier || statusInfo.current_owner || '-' }}</span>
            </div>
            <div class="signature-item">
              <span class="signature-label">{{ t('maintVerificationTime') }}:</span>
              <span class="signature-value">{{ maintenance.verified_at ? formatDateTime(maintenance.verified_at) : '-' }}</span>
            </div>
          </div>

          <!-- 验证操作按钮 -->
          <div class="verification-actions" v-if="statusInfo.status === 'verifying'">
            <button class="verify-btn primary" @click="handleVerifyPass">
              <el-icon><CircleCheck /></el-icon>
              {{ t('maintVerifyPass') }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 报告底部信息 -->
    <section class="report-footer">
      <span class="footer-item">{{ t('maintReportNo') }}: {{ maintenance.maint_no }}</span>
      <span class="footer-item">{{ t('maintGeneratedAt') }}: {{ formatDateTime(reportGeneratedTime) }}</span>
      <span class="footer-item">{{ t('maintReportSystem') }}: {{ t('maintSystemVersion') }}</span>
    </section>

    <!-- 编辑维修对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="t('maintDetailEdit')"
      width="720px"
      append-to-body
      draggable
      align-center
      class="edit-maint-dialog"
    >
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Setting /></el-icon>
            {{ t('maintBasicInfo') }}
          </div>
          <el-form :model="editForm" label-width="70px">
            <el-form-item :label="t('maintType')" required>
              <el-select v-model="editForm.maint_type" style="width: 200px">
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
          <el-form :model="editForm" label-width="70px">
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
                    :placeholder="t('maintDetailSpareSearchPlaceholder')"
                    filterable
                    remote
                    :remote-method="searchSpareParts"
                    :loading="spareLoading"
                    style="width: 200px"
                    @change="addSparePartToEditForm"
                  >
                    <el-option
                      v-for="part in sparePartOptions"
                      :key="part.id"
                      :label="part.is_serial_match ? `${part.serial_number} - ${part.name}` : `${part.part_number} - ${part.name} (${t('maintSpareStock')}: ${part.quantity_in_stock})`"
                      :value="part.id"
                      :disabled="!part.is_serial_match && part.quantity_in_stock <= 0"
                    >
                      <div class="spare-option">
                        <span class="spare-number">{{ part.part_number }}</span>
                        <span class="spare-name">{{ part.name }}</span>
                        <span v-if="part.is_serial_match" class="spare-sn">
                          {{ t('maintDetailSpareSerial') }}: {{ part.serial_number }}
                        </span>
                        <span v-else class="spare-stock" :class="{ low: part.quantity_in_stock <= part.min_quantity }">
                          {{ t('maintSpareStock') }}: {{ part.quantity_in_stock }}
                        </span>
                      </div>
                    </el-option>
                  </el-select>
                </div>

                <div class="selected-parts" v-if="editForm.spare_parts.length > 0">
                  <el-table :data="editForm.spare_parts" size="small" border>
                    <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                      <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                    </el-table-column>
                    <el-table-column prop="part_number" :label="t('maintColModel')" width="100" />
                    <el-table-column prop="name" :label="t('maintColName')" min-width="100" />
                    <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60">
                      <template #default="{ row }">
                        <el-input-number v-model="row.quantity" :min="1" size="small" @change="updateEditPartsCost" />
                      </template>
                    </el-table-column>
                    <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="70">
                      <template #default="{ row }">{{ formatCurrency(row.unit_price) }}</template>
                    </el-table-column>
                    <el-table-column :label="t('colOperation')" width="40">
                      <template #default="{ row, $index }">
                        <el-button type="danger" size="small" link class="delete-btn-icon" @click="removeEditSparePart($index)">
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  <div class="parts-summary">
                    {{ t('maintSpareTotalCost') }}: <span class="total-cost">{{ formatCurrency(editForm.parts_cost) }}</span>
                  </div>
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
          <el-form :model="editForm" label-width="70px">
            <el-form-item :label="t('maintReturnPartsLabel')">
              <div class="return-parts-section">
                <!-- 扫码功能条 -->
                <div class="scan-action-bar return">
                  <el-button type="default" class="scan-btn" @click="openReturnScanDialog">
                    <el-icon><Aim /></el-icon>
                    {{ t('maintDetailScanAddReturn') }}
                  </el-button>
                  <div class="scan-tip-badge">
                    <el-icon><InfoFilled /></el-icon>
                    {{ t('maintDetailReturnScanTip') }}
                  </div>
                </div>

                <!-- 手动输入查询 -->
                <div class="return-manual-query" style="margin-top: 8px">
                  <el-input
                    v-model="returnScanInput"
                    :placeholder="t('maintDetailReturnManualPlaceholder')"
                    style="width: 150px"
                    @keyup.enter="scanReturnPart"
                    clearable
                  >
                    <template #prefix><el-icon><Aim /></el-icon></template>
                  </el-input>
                  <el-button type="default" size="small" @click="scanReturnPart" :loading="returnScanLoading">
                    {{ t('spareQuery') }}
                  </el-button>
                </div>

                <!-- 扫码识别结果 -->
                <div class="return-found-info" v-if="returnFoundInfo">
                  <el-card size="small" shadow="never">
                    <div class="found-header">
                      <el-tag type="success" size="small">{{ t('maintReturnFoundTag') }}</el-tag>
                      <span>{{ returnFoundInfo.serial_number }}</span>
                    </div>
                    <el-descriptions :column="3" size="small" border>
                      <el-descriptions-item :label="t('maintColModel')">{{ returnFoundInfo.part_number }}</el-descriptions-item>
                      <el-descriptions-item :label="t('maintColName')">{{ returnFoundInfo.name }}</el-descriptions-item>
                      <el-descriptions-item :label="t('maintColUnitPrice')">{{ formatCurrency(returnFoundInfo.unit_price) }}</el-descriptions-item>
                    </el-descriptions>
                    <div class="found-actions">
                      <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                      <el-checkbox v-model="returnPartScrap">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                      <el-button type="primary" size="small" @click="addFoundReturnPart">{{ t('maintReturnAddToList') }}</el-button>
                      <el-button size="small" @click="clearReturnFound">{{ t('actionReset') }}</el-button>
                    </div>
                  </el-card>
                </div>

                <!-- 手动添加返回件 -->
                <div class="return-manual-area" v-if="!returnFoundInfo">
                  <div class="return-manual-row">
                    <el-select
                      v-model="selectedReturnPart"
                      :placeholder="t('maintReturnSelectFromSpare')"
                      filterable
                      remote
                      :remote-method="searchReturnParts"
                      :loading="spareLoading"
                      style="width: 140px"
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
                    <el-input v-model="returnPartSerial" :placeholder="t('maintReturnSerialPlaceholder')" style="width: 100px" />
                    <el-input v-model="returnPartNumber" :placeholder="t('maintReturnModelManual')" style="width: 100px" />
                    <el-input v-model="returnPartName" :placeholder="t('maintReturnNameDefault')" style="width: 100px" />
                  </div>
                  <div class="return-manual-row">
                    <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 70px" />
                    <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                    <el-button type="primary" size="small" :disabled="!returnPartSerial" @click="addReturnPart">{{ t('actionAdd') }}</el-button>
                  </div>
                </div>

                <div class="return-parts-table" v-if="editForm.return_parts.length > 0">
                  <el-table :data="editForm.return_parts" size="small" border>
                    <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                      <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                    </el-table-column>
                    <el-table-column prop="part_number" :label="t('maintColModel')" width="100" />
                    <el-table-column prop="name" :label="t('maintColName')" min-width="100" />
                    <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60">
                      <template #default="{ row, $index }">
                        <el-input-number v-model="row.quantity" :min="1" size="small" />
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('maintReturnScrapLabel')" width="90">
                      <template #default="{ row }">
                        <el-checkbox v-model="row.scrap_in" :disabled="!row.part_id" />
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('colOperation')" width="40">
                      <template #default="{ row, $index }">
                        <el-button type="danger" size="small" link class="delete-btn-icon" @click="removeReturnPart($index)">
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  <div class="return-tip-form">{{ t('maintDetailReturnTipForm') }}</div>
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
            {{ t('maintCostDescSection') }}
          </div>
          <el-form :model="editForm" label-width="70px">
            <el-form-item :label="t('maintLaborHours')">
              <el-input-number v-model="editForm.labor_hours" :min="0" :precision="1" />
            </el-form-item>
            <el-form-item :label="t('maintLaborCost')">
              <el-input-number v-model="editForm.labor_cost" :min="0" :precision="2" />
            </el-form-item>
            <el-form-item :label="t('maintVendor')">
              <el-input v-model="editForm.vendor" />
            </el-form-item>
            <el-form-item :label="t('maintDesc')" required>
              <el-input v-model="editForm.description" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateMaintenanceRecord">{{ t('maintConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="t('maintScanSpareDialog')" width="900px">
      <ScanSession
        ref="scanSessionRef"
        default-type="out"
        :device-id="maintenance?.device_id"
        :auto-start="scanDialogVisible"
        :reference="maintenance?.maint_no"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>

    <!-- 扫码添加返回件对话框 -->
    <el-dialog v-model="returnScanDialogVisible" :title="t('maintDetailScanReturnDialog')" width="900px">
      <ScanSession
        ref="returnScanSessionRef"
        default-type="return"
        :device-id="maintenance?.device_id"
        :auto-start="returnScanDialogVisible"
        :reference="maintenance?.maint_no"
        @complete="onReturnScanSessionComplete"
        @cancel="returnScanDialogVisible = false"
      />
      <template #footer>
        <el-button @click="returnScanDialogVisible = false">{{ t('actionClose') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Aim, Edit, Delete, Setting, Box, RefreshRight, Document, InfoFilled,
  CircleCheck, Download, Printer
} from '@element-plus/icons-vue'
import {
  getMaintenanceDetail, updateMaintenance,
  getDevices, getPartList, createMovement, getPartBySerialNumber, searchInStockParts
} from '@/api'
import ScanSession from '@/components/ScanSession.vue'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import api from '@/api/request'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

// 基础数据
const maintenance = ref({})
const device = ref(null)
const loading = ref(false)
const showEditDialog = ref(false)
const activeTab = ref('parts')
const reportGeneratedTime = ref(new Date())

// 状态信息
const statusInfo = ref({
  status: 'created',
  status_label: '创建',
  priority: 'P3',
  current_owner: null,
  repairing_at: null,
  verifying_at: null,
  completed_at: null
})

// 备件相关
const sparePartOptions = ref([])
const spareLoading = ref(false)
const selectedSparePart = ref(null)
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)
const originalSpareParts = ref([])

// 返回件相关
const returnScanDialogVisible = ref(false)
const returnScanSessionRef = ref(null)
const returnScanInput = ref('')
const returnScanLoading = ref(false)
const returnFoundInfo = ref(null)
const selectedReturnPart = ref(null)
const returnPartNumber = ref('')
const returnPartSerial = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

// 编辑表单
const editForm = ref({
  maint_type: 'corrective',
  spare_parts: [],
  return_parts: [],
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  vendor: '',
  description: '',
  verification_result: '',
  verification_notes: ''
})

// ===== 状态常量 =====
const STATUS_COLORS = {
  'created': 'info', 'pending': 'info', 'repairing': 'warning',
  'verifying': 'primary', 'completed': 'success', 'cancelled': 'danger'
}
const PRIORITY_COLORS = {
  'P1': 'danger', 'P2': 'warning', 'P3': 'info', 'P4': 'success'
}

// ===== 计算属性 =====
const totalCost = computed(() => (maintenance.value.parts_cost || 0) + (maintenance.value.labor_cost || 0))

const sparePartsList = computed(() => {
  if (!maintenance.value.parts_replaced) return []
  try {
    const parsed = JSON.parse(maintenance.value.parts_replaced)
    return parsed.filter(p => !p.is_return)
  } catch { return [] }
})

const returnPartsList = computed(() => {
  if (!maintenance.value.parts_replaced) return []
  try {
    const parsed = JSON.parse(maintenance.value.parts_replaced)
    return parsed.filter(p => p.is_return)
  } catch { return [] }
})

const allPartsList = computed(() => [...sparePartsList.value, ...returnPartsList.value])

const partsCostPercent = computed(() => {
  if (totalCost.value === 0) return 0
  return Math.round(((maintenance.value.parts_cost || 0) / totalCost.value) * 100)
})

const laborCostPercent = computed(() => {
  if (totalCost.value === 0) return 0
  return Math.round(((maintenance.value.labor_cost || 0) / totalCost.value) * 100)
})

const laborRate = computed(() => {
  const hours = maintenance.value.labor_hours || 0
  if (hours === 0) return 0
  return Math.round((maintenance.value.labor_cost || 0) / hours)
})

const canEdit = computed(() => ['created', 'pending', 'repairing', 'verifying'].includes(statusInfo.value.status))

const verificationStatusClass = computed(() => {
  if (statusInfo.value.status === 'completed') return 'completed'
  if (statusInfo.value.status === 'cancelled') return 'cancelled'
  if (statusInfo.value.status === 'verifying') return 'verifying'
  return 'pending'
})

const verificationStatusIcon = computed(() => {
  if (statusInfo.value.status === 'completed') return '✓'
  if (statusInfo.value.status === 'cancelled') return '✗'
  if (statusInfo.value.status === 'verifying') return '⏳'
  return '○'
})

const verificationStatusLabel = computed(() => {
  if (statusInfo.value.status === 'completed') return t('maintVerificationCompleted')
  if (statusInfo.value.status === 'cancelled') return t('maintStatusCancelled')
  if (statusInfo.value.status === 'verifying') return t('maintVerificationPending')
  return t('maintVerificationNotStarted')
})

// ===== 方法 =====
const isStepCompleted = (stepKey) => {
  const statusOrder = ['created', 'pending', 'repairing', 'verifying', 'completed']
  if (statusInfo.value.status === 'cancelled') return false
  const currentIdx = statusOrder.indexOf(statusInfo.value.status)
  const stepIdx = statusOrder.indexOf(stepKey)
  return stepIdx < currentIdx || statusInfo.value.status === stepKey
}

const calculateProgress = () => {
  const progressMap = { 'created': 25, 'pending': 25, 'repairing': 50, 'verifying': 75, 'completed': 100, 'cancelled': 0 }
  return progressMap[statusInfo.value.status] || 25
}

const estimateCompletionTime = () => {
  const hours = maintenance.value.labor_hours || 2
  const startDate = new Date(statusInfo.value.repairing_at || maintenance.value.created_at)
  const estimatedEnd = new Date(startDate.getTime() + hours * 60 * 60 * 1000)
  return dayjs(estimatedEnd).format('HH:mm')
}

const getStatusTagClass = (status) => STATUS_COLORS[status] || 'info'
const getPriorityTagClass = (priority) => PRIORITY_COLORS[priority] || 'info'
const getMaintTypeTagClass = (type) => ({ preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }[type] || 'info')
const getMaintTypeText = (type) => ({ preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }[type] || type)

const getVerificationTagType = (result) => ({ passed: 'success', partial: 'warning', failed: 'danger' }[result] || 'info')
const getVerificationResultText = (result) => ({ passed: t('maintVerificationPassed'), partial: t('maintVerificationPartial'), failed: t('maintVerificationFailed') }[result] || t('maintVerificationNotVerified'))

const formatDateTime = (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'
const formatDateTimeShort = (date) => date ? dayjs(date).format('MM-DD HH:mm') : '-'
const formatCurrency = (value) => `¥${(value || 0).toFixed(2)}`

// ===== 数据加载 =====
const loadMaintenance = debounce(async (force = false) => {
  loading.value = true
  try {
    const maintId = route.params.id
    const data = await cachedRequest(() => getMaintenanceDetail(maintId), 'maintenance_detail', { id: maintId }, { forceRefresh: force })
    maintenance.value = data
    statusInfo.value = {
      status: data.status || 'created',
      status_label: data.status_label || t('maintStatusLabelCreated'),
      priority: data.priority || 'P3',
      current_owner: data.current_owner,
      repairing_at: data.repairing_at,
      verifying_at: data.verifying_at,
      completed_at: data.completed_at
    }
    if (data.device_id) {
      const devices = await getDevices()
      device.value = (devices.items || []).find(d => d.id === data.device_id)
    }
  } catch { ElMessage.error(t('maintLoadDetailFailed')) }
  finally { loading.value = false }
}, 300)

// ===== 编辑相关 =====
const openEditDialog = () => {
  editForm.value = {
    maint_type: maintenance.value.maint_type,
    spare_parts: [...sparePartsList.value],
    return_parts: [...returnPartsList.value],
    parts_cost: maintenance.value.parts_cost || 0,
    labor_hours: maintenance.value.labor_hours || 0,
    labor_cost: maintenance.value.labor_cost || 0,
    vendor: maintenance.value.vendor || '',
    description: maintenance.value.description || '',
    verification_result: maintenance.value.verification_result || '',
    verification_notes: maintenance.value.verification_notes || ''
  }
  showEditDialog.value = true
}

const updateMaintenanceRecord = async () => {
  if (!editForm.value.description) { ElMessage.warning(t('maintEnterDescription')); return }
  try {
    const combinedParts = [...editForm.value.spare_parts.map(p => ({ ...p, is_return: false })), ...editForm.value.return_parts.map(p => ({ ...p, is_return: true }))]
    await updateMaintenance(maintenance.value.id, { ...editForm.value, parts_replaced: JSON.stringify(combinedParts) })
    for (const part of editForm.value.spare_parts) {
      if (!part.is_from_scan && part.part_id) {
        await createMovement({ part_id: part.part_id, movement_type: 'out', quantity: part.quantity || 1, serial_number: part.serial_number, reason: `${t('spareReasonMaintenancePartReplace')} - ${maintenance.value.maint_no}`, operator: 'Web', reference: maintenance.value.maint_no, target_device_id: maintenance.value.device_id })
      }
    }
    for (const part of editForm.value.return_parts) {
      if (!part.is_from_scan && part.scrap_in && part.part_id) {
        await createMovement({ part_id: part.part_id, movement_type: 'scrap_in', quantity: part.quantity, serial_number: part.serial_number, reason: t('spareReasonReturnPartScrap'), operator: 'Web', reference: maintenance.value.maint_no, source_device_id: maintenance.value.device_id })
      }
    }
    ElMessage.success(t('maintRecordUpdated'))
    showEditDialog.value = false
    loadMaintenance()
  } catch (e) { ElMessage.error(t('maintUpdateFailed') + ': ' + (e.response?.data?.detail || e.message)) }
}

// ===== 备件搜索 =====
const searchSpareParts = async (query) => {
  if (!query || query.length < 1) { sparePartOptions.value = []; return }
  spareLoading.value = true
  try {
    const result = await searchInStockParts(query)
    sparePartOptions.value = (result.items || []).map(item => ({ id: item.id, part_number: item.part_number, name: item.name, serial_number: item.serial_number, quantity_in_stock: item.quantity_in_stock, unit_price: item.unit_price, is_serial_match: true }))
  } catch { sparePartOptions.value = [] }
  finally { spareLoading.value = false }
}

const addSparePartToEditForm = () => {
  if (!selectedSparePart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return
  editForm.value.spare_parts.push({ part_id: part.id, part_number: part.part_number, name: part.name, serial_number: part.serial_number || null, unit_price: part.unit_price || 0, quantity: 1, is_serial_match: part.is_serial_match || false })
  updateEditPartsCost()
  selectedSparePart.value = null
}

const removeEditSparePart = (index) => { editForm.value.spare_parts.splice(index, 1); updateEditPartsCost() }
const updateEditPartsCost = () => { editForm.value.parts_cost = editForm.value.spare_parts.reduce((sum, p) => sum + p.quantity * p.unit_price, 0) }

// ===== 扫码 =====
const openScanDialog = () => { scanDialogVisible.value = true }
const openReturnScanDialog = () => { returnScanDialogVisible.value = true }

const onScanSessionComplete = async (result) => {
  for (const item of result.items) {
    const existing = editForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) existing.quantity += 1
    else editForm.value.spare_parts.push({ part_id: item.part_id, part_number: item.part_number, name: item.name, serial_number: item.serial_number, unit_price: item.unit_price || 0, quantity: 1, is_from_scan: true })
  }
  updateEditPartsCost()
  scanDialogVisible.value = false
  ElMessage.success(t('maintPartsAdded', { count: result.items.length }))
}

const onReturnScanSessionComplete = async (result) => {
  for (const item of result.items) {
    editForm.value.return_parts.push({ part_id: item.part_id, part_number: item.part_number, name: item.name, serial_number: item.serial_number, unit_price: item.unit_price || 0, quantity: 1, scrap_in: item.part_id ? true : false, is_from_scan: true })
  }
  returnScanDialogVisible.value = false
}

// ===== 返回件 =====
const searchReturnParts = async (query) => {
  if (!query) { sparePartOptions.value = []; return }
  spareLoading.value = true
  try { const result = await getPartList({ search: query, limit: 20 }); sparePartOptions.value = result.items || [] }
  catch { sparePartOptions.value = [] }
  finally { spareLoading.value = false }
}

const scanReturnPart = async () => {
  const serial = returnScanInput.value.trim()
  if (!serial || serial.length < 4) { ElMessage.warning(t('maintSerialMinLength')); return }
  returnScanLoading.value = true
  try {
    const info = await getPartBySerialNumber(serial)
    returnFoundInfo.value = info
    returnPartSerial.value = info.serial_number
    returnPartNumber.value = info.part_number
    returnPartName.value = info.name
    selectedReturnPart.value = info.id
    returnPartScrap.value = true
  } catch { returnFoundInfo.value = null; returnPartSerial.value = serial; ElMessage.info(t('maintSerialNotFound')) }
  finally { returnScanLoading.value = false }
}

const clearReturnFound = () => { returnFoundInfo.value = null; returnScanInput.value = ''; returnPartSerial.value = ''; returnPartNumber.value = ''; returnPartName.value = ''; selectedReturnPart.value = null; returnPartQty.value = 1 }

const addFoundReturnPart = () => {
  if (!returnFoundInfo.value) return
  editForm.value.return_parts.push({ part_id: returnFoundInfo.value.id, part_number: returnFoundInfo.value.part_number, name: returnFoundInfo.value.name, serial_number: returnFoundInfo.value.serial_number, unit_price: returnFoundInfo.value.unit_price || 0, quantity: returnPartQty.value, scrap_in: returnPartScrap.value, is_from_scan: true })
  ElMessage.success(t('maintReturnPartAdded', { sn: returnFoundInfo.value.serial_number }))
  clearReturnFound()
}

const onReturnPartSelect = () => {
  if (!selectedReturnPart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
  if (part) { returnPartNumber.value = part.part_number; returnPartName.value = part.name || part.part_number; returnPartScrap.value = true }
}

const addReturnPart = async () => {
  if (!returnPartSerial.value) { ElMessage.warning(t('maintEnterSerial')); return }
  let partId = null, partNumber = returnPartNumber.value, partName = returnPartName.value || returnPartNumber.value, unitPrice = 0
  if (selectedReturnPart.value) {
    const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) { partId = part.id; partNumber = part.part_number; partName = part.name || part.part_number; unitPrice = part.unit_price || 0 }
  } else {
    try { const info = await getPartBySerialNumber(returnPartSerial.value); partId = info.id; partNumber = info.part_number; partName = info.name; unitPrice = info.unit_price || 0 } catch { partId = null }
  }
  editForm.value.return_parts.push({ part_id: partId, part_number: partNumber, name: partName, serial_number: returnPartSerial.value, unit_price: unitPrice, quantity: returnPartQty.value, scrap_in: partId ? returnPartScrap.value : false, is_from_scan: false })
  ElMessage.success(t('maintReturnPartAddedNoMatch'))
  returnScanInput.value = ''; returnFoundInfo.value = null; selectedReturnPart.value = null; returnPartSerial.value = ''; returnPartNumber.value = ''; returnPartName.value = ''; returnPartQty.value = 1; returnPartScrap.value = true
}

const removeReturnPart = (index) => { editForm.value.return_parts.splice(index, 1) }

// ===== 验证 =====
const handleVerifyPass = async () => {
  try {
    await ElMessageBox.confirm(t('maintVerifyConfirm'), t('msgConfirm'), { type: 'success' })
    await api.post(`/maintenance/${maintenance.value.id}/verify-pass`, { operator: 'Web' })
    ElMessage.success(t('maintVerified'))
    loadMaintenance()
  } catch (e) { if (e !== 'cancel') ElMessage.error(t('maintVerifyFailed') + ': ' + (e.response?.data?.detail || e.message)) }
}

// ===== 导出打印 =====
const handleExport = () => { ElMessage.info(t('maintExportInProgress')) }
const handlePrint = () => { window.print() }

onMounted(async () => {
  await loadMaintenance()
  if (route.query.edit === 'true') openEditDialog()
})
</script>

<style scoped>
/* ===== 页面容器 ===== */
.maintenance-report-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

/* ===== 进度条顶部 ===== */
.progress-bar-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  margin-bottom: 24px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

.progress-steps {
  display: flex;
  align-items: center;
  gap: 0;
}

.step-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.node-dot {
  font-size: 16px;
  color: #dcdfe6;
  transition: color 0.3s;
}

.step-node.completed .node-dot {
  color: #67c23a;
}

.step-node.active .node-dot {
  color: #409eff;
  animation: pulse 1.5s infinite;
}

.node-label {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

.step-node.completed .node-label {
  color: #67c23a;
}

.step-node.active .node-label {
  color: #409eff;
  font-weight: 600;
}

.step-line {
  width: 60px;
  height: 2px;
  background: #e4e7ed;
  margin: 0 8px;
  margin-top: -20px;
  transition: background 0.3s;
}

.step-line.completed {
  background: #67c23a;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.report-no {
  color: #606266;
  font-weight: 500;
}

.progress-percent {
  color: #409eff;
  font-weight: 600;
}

.progress-estimate {
  color: #909399;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ===== 报告头部卡片 ===== */
.report-header-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  margin-bottom: 24px;
}

.header-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.title-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.report-icon {
  font-size: 24px;
  color: #409eff;
}

.report-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.maint-no-text {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

/* ===== 信息区块 ===== */
.info-block {
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
}

.info-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.info-label {
  font-size: 13px;
  color: #909399;
  min-width: 60px;
}

.info-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.info-value.link {
  color: #409eff;
  text-decoration: none;
}

.info-value.link:hover {
  text-decoration: underline;
}

.info-value.muted {
  color: #c0c4cc;
}

.fault-link {
  color: #e6a23c;
}

.separator-line {
  height: 1px;
  background: linear-gradient(to right, transparent, #ebeef5 20%, #ebeef5 80%, transparent);
  margin: 16px 0;
}

/* ===== 维修说明 ===== */
.description-block {
  padding: 12px 0;
}

.description-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.description-content {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

/* ===== 关键指标表格 ===== */
.metrics-table {
  margin-top: 16px;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  padding: 16px 0;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
}

.metric-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: center;
}

.metric-cell.highlight {
  background: #fff;
  border-radius: 6px;
  padding: 8px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
}

.metric-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.metric-value.cost {
  color: #409eff;
  font-size: 16px;
  font-weight: 600;
}

/* ===== 操作按钮 ===== */
.header-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.action-btn.secondary {
  background: #f5f7fa;
  color: #606266;
  border-color: #dcdfe6;
}

.action-btn.secondary:hover {
  background: #e4e7ed;
}

.action-btn.primary {
  background: #409eff;
  color: #fff;
}

.action-btn.primary:hover {
  background: #66b1ff;
}

/* ===== 报告区块 ===== */
.report-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.section-number {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  background: #ecf5ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

/* ===== Tab切换 ===== */
.tab-switcher {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 14px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  background: transparent;
}

.tab-btn:hover {
  color: #409eff;
}

.tab-btn.active {
  background: #fff;
  color: #409eff;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.tab-content {
  padding: 8px 0;
}

/* ===== 备件表格 ===== */
.parts-table-wrapper {
  overflow-x: auto;
}

.parts-table {
  width: 100%;
  border-collapse: collapse;
}

.parts-table th {
  background: #f5f7fa;
  padding: 10px 12px;
  font-size: 13px;
  color: #909399;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

.parts-table td {
  padding: 12px;
  font-size: 14px;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
}

.parts-table tr:hover {
  background: #f5f7fa;
}

.type-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.type-tag.spare {
  background: #ecf5ff;
  color: #409eff;
}

.type-tag.return {
  background: #f0f9eb;
  color: #67c23a;
}

/* ===== 成本分析 ===== */
.cost-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.cost-card {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  text-align: center;
}

.cost-card .cost-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 10px;
}

.cost-card .cost-amount {
  font-size: 26px;
  font-weight: 600;
  color: #303133;
}

.cost-card .cost-amount.highlight {
  color: #409eff;
}

.cost-bar-chart {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cost-bar-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bar-label {
  min-width: 80px;
  font-size: 13px;
  color: #606266;
}

.bar-track {
  flex: 1;
  height: 28px;
  background: #f5f7fa;
  border-radius: 6px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
}

.bar-fill.parts { background: linear-gradient(90deg, #409eff, #79bbff); }
.bar-fill.return { background: linear-gradient(90deg, #67c23a, #95d475); }
.bar-fill.total { background: linear-gradient(90deg, #e6a23c, #eebe77); }

.bar-value {
  min-width: 80px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  text-align: right;
}

/* ===== 验收确认 ===== */
.verification-card {
  padding: 0;
}

.verification-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.status-value {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
}

.status-value.completed {
  color: #67c23a;
}

.status-value.verifying {
  color: #e6a23c;
}

.status-value.pending {
  color: #909399;
}

.status-value.cancelled {
  color: #f56c6c;
}

.status-icon {
  font-size: 16px;
}

.separator-line.light {
  background: linear-gradient(to right, transparent, #ebeef5 30%, #ebeef5 70%, transparent);
  margin: 12px 0;
}

.verification-result {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.result-label {
  font-size: 13px;
  color: #909399;
  min-width: 80px;
}

.result-buttons {
  display: flex;
  gap: 8px;
}

.result-btn {
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  transition: all 0.2s;
}

.result-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

.result-btn.selected {
  background: #ecf5ff;
  border-color: #409eff;
  color: #409eff;
}

.result-btn.partial.selected {
  background: #fdf6ec;
  border-color: #e6a23c;
  color: #e6a23c;
}

.result-btn.fail.selected {
  background: #fef0f0;
  border-color: #f56c6c;
  color: #f56c6c;
}

.verification-result-display {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.verification-notes {
  margin-bottom: 16px;
}

.notes-input {
  margin-top: 8px;
}

.notes-placeholder {
  color: #c0c4cc;
  font-size: 13px;
}

.verification-signature {
  display: flex;
  gap: 24px;
  padding: 12px 0;
  border-top: 1px solid #ebeef5;
}

.signature-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.signature-label {
  font-size: 13px;
  color: #909399;
}

.signature-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.verification-actions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.verify-btn.primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  background: #67c23a;
  color: #fff;
  transition: all 0.2s;
}

.verify-btn.primary:hover {
  background: #85ce61;
}

/* ===== 成本分析详情 ===== */
.cost-breakdown {
  padding: 16px 0;
}

.cost-item {
  margin-bottom: 16px;
}

.cost-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.cost-label {
  font-size: 13px;
  color: #606266;
}

.cost-amount {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.cost-percent {
  font-size: 12px;
  color: #909399;
}

.cost-bar {
  height: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill.labor {
  background: linear-gradient(90deg, #e6a23c, #eebe77);
}

.cost-detail {
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-top: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-size: 13px;
  color: #909399;
}

.detail-value {
  font-size: 13px;
  color: #303133;
}

/* ===== 报告底部 ===== */
.report-footer {
  display: flex;
  justify-content: center;
  gap: 24px;
  padding: 16px;
  font-size: 12px;
  color: #909399;
  background: #fff;
  border-radius: 8px;
}

.footer-item {
  color: #909399;
}

/* ===== 深色模式 ===== */
.dark .maintenance-report-page {
  background: #1a1a2e;
}

.dark .progress-bar-header,
.dark .report-header-card,
.dark .report-section,
.dark .report-footer {
  background: #16213e;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.dark .report-title,
.dark .section-title,
.dark .info-value,
.dark .metric-value,
.dark .bar-value {
  color: #e4e7ed;
}

.dark .info-label,
.dark .node-label,
.dark .metric-label,
.dark .cost-label {
  color: #6b7280;
}

.dark .separator-line,
.dark .header-title-row,
.dark .section-header,
.dark .header-actions {
  border-color: #374151;
}

.dark .description-content,
.dark .metrics-row,
.dark .cost-card,
.dark .verify-status-block,
.dark .notes-content,
.dark .signature-block,
.dark .tab-switcher,
.dark .parts-table th,
.dark .parts-table tr:hover {
  background: #1f2937;
}

.dark .parts-table th,
.dark .parts-table td {
  border-color: #374151;
  color: #e4e7ed;
}

.dark .action-btn.secondary {
  background: #374151;
  color: #e4e7ed;
  border-color: #4b5563;
}

.dark .tab-btn.active {
  background: #16213e;
  color: #409eff;
}

/* ===== 打印样式 ===== */
@media print {
  .maintenance-report-page {
    background: #fff;
    padding: 0;
    max-width: 100%;
  }

  .progress-bar-header,
  .report-header-card,
  .report-section {
    box-shadow: none;
    border: 1px solid #e4e7ed;
  }

  .header-actions,
  .tab-switcher,
  .verify-actions {
    display: none;
  }

  .report-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #fff;
  }
}
</style>
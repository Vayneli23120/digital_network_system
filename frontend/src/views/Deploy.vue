<template>
  <div class="deploy-page" :class="{ dark: isDark }">
    <!-- 页面标题栏 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('deployTitle') }}</h1>
        <el-tag v-if="executionStatus === 'running'" type="warning" effect="dark" class="status-tag">
          <span class="status-content">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>{{ t('deployExecuting') }}</span>
          </span>
        </el-tag>
        <el-tag v-else-if="executionStatus === 'completed'" type="success" class="status-tag">
          <span class="status-content">
            <el-icon><CircleCheckFilled /></el-icon>
            <span>{{ t('deployCompleted') }}</span>
          </span>
        </el-tag>
        <el-tag v-else-if="executionStatus === 'failed'" type="danger" class="status-tag">
          <span class="status-content">
            <el-icon><CircleCloseFilled /></el-icon>
            <span>{{ t('deployFailed') }}</span>
          </span>
        </el-tag>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn secondary" @click="showVariableHelp = true">
          <el-icon><QuestionFilled /></el-icon>
          {{ t('deployVariableHelp') }}
        </button>
        <button
          v-if="executionStatus === 'running'"
          class="nav-action-btn danger"
          @click="confirmAbort"
          :loading="aborting"
        >
          <el-icon><CircleClose /></el-icon>
          {{ t('deployAbort') }}
        </button>
      </div>
    </section>

    <!-- 主内容区 -->
    <section class="main-content-area">
      <el-row :gutter="20" class="full-height">
        <!-- 左侧：配置面板 -->
        <el-col :span="8" class="config-column">
          <div class="config-panel" v-loading="loading">
            <div class="panel-header">
              <span class="panel-title">{{ t('deployConfigPanel') }}</span>
            </div>

            <el-form :model="deployForm" label-position="top" class="config-form">
              <!-- 部署模式 -->
              <div class="form-section">
                <div class="section-label">{{ t('deployMode') }}</div>
                <el-radio-group v-model="deployForm.mode" class="mode-radio-group">
                  <el-radio-button label="backup">
                    <el-icon><Document /></el-icon>
                    {{ t('deployFromBackup') }}
                  </el-radio-button>
                  <el-radio-button label="template">
                    <el-icon><Files /></el-icon>
                    {{ t('deployUseTemplate') }}
                  </el-radio-button>
                  <el-radio-button label="snippet">
                    <el-icon><Edit /></el-icon>
                    {{ t('deploySnippet') }}
                  </el-radio-button>
                </el-radio-group>
              </div>

              <!-- 部署引擎选择 -->
              <div class="form-section">
                <div class="section-label">{{ t('deployEngine') }}</div>
                <el-radio-group v-model="deployForm.engine" size="small">
                  <el-radio-button label="napalm" :disabled="deployForm.mode === 'template' || deployForm.mode === 'backup'">
                    <el-icon><Shield /></el-icon>
                    {{ t('deployEngineNapalm') }}
                    <el-tag type="success" size="small" effect="plain" class="engine-tag">{{ t('deployEngineNapalmTag') }}</el-tag>
                  </el-radio-button>
                  <el-radio-button label="netmiko">
                    <el-icon><Connection /></el-icon>
                    {{ t('deployEngineNetmiko') }}
                    <el-tag type="info" size="small" effect="plain" class="engine-tag">{{ t('deployEngineNetmikoTag') }}</el-tag>
                  </el-radio-button>
                </el-radio-group>
                <div v-if="deployForm.mode === 'template' || deployForm.mode === 'backup'" class="engine-tip warning">
                  <el-icon><WarningFilled /></el-icon>
                  {{ t('deployBackupTemplateNetmikoOnly') }}
                </div>
                <div v-else-if="deployForm.engine === 'napalm'" class="engine-tip safe">
                  <el-icon><InfoFilled /></el-icon>
                  {{ t('deployEngineNapalmTip') }}
                </div>
              </div>

              <!-- NAPALM 传输方式选择 -->
              <div v-if="deployForm.engine === 'napalm'" class="form-section">
                <div class="section-label">{{ t('deployNapalmTransfer') }}</div>
                <el-radio-group v-model="deployForm.transfer_mode" size="small">
                  <el-radio-button label="scp">
                    {{ t('deployTransferScp') }}
                    <el-tag type="success" size="small" effect="plain" class="engine-tag">{{ t('deployTransferScpTag') }}</el-tag>
                  </el-radio-button>
                  <el-radio-button label="inline">
                    {{ t('deployTransferInline') }}
                    <el-tag type="warning" size="small" effect="plain" class="engine-tag">{{ t('deployTransferInlineTag') }}</el-tag>
                  </el-radio-button>
                </el-radio-group>
                <div class="napalm-mode-tip">
                  {{ deployForm.transfer_mode === 'scp' ? t('deployTransferScpTip') : t('deployTransferInlineTip') }}
                </div>
              </div>

              <!-- 备份文件选择 -->
              <div v-if="deployForm.mode === 'backup'" class="form-section">
                <div class="section-label required">{{ t('deployBackupFile') }}</div>
                <el-select
                  v-model="deployForm.backup_file"
                  :placeholder="t('deploySelectBackupFile')"
                  style="width: 100%"
                  filterable
                >
                  <el-option
                    v-for="backup in backups"
                    :key="backup.id"
                    :label="`${backup.device_name} - ${backup.backup_file}`"
                    :value="backup.backup_file"
                  >
                    <div class="backup-option">
                      <span class="backup-name">{{ backup.device_name }}</span>
                      <span class="backup-file">{{ backup.backup_file }}</span>
                      <span class="backup-time">{{ formatDateTime(backup.backup_time) }}</span>
                    </div>
                  </el-option>
                </el-select>
              </div>

              <!-- 模板选择 -->
              <div v-if="deployForm.mode === 'template'" class="form-section">
                <div class="section-label required">{{ t('deployConfigTemplate') }}</div>
                <el-select
                  v-model="deployForm.template_id"
                  :placeholder="t('deploySelectTemplate')"
                  style="width: 100%"
                  @change="loadTemplateVariables"
                >
                  <el-option
                    v-for="template in templates"
                    :key="template.id"
                    :label="template.name"
                    :value="template.id"
                  >
                    <div class="template-option">
                      <span class="template-name">{{ template.name }}</span>
                      <span v-if="template.description" class="template-desc">
                        {{ template.description }}
                      </span>
                    </div>
                  </el-option>
                </el-select>
              </div>

              <!-- 配置片段模式 -->
              <div v-if="deployForm.mode === 'snippet'" class="form-section">
                <div class="section-label required">{{ t('deploySnippetContent') }}</div>
                <el-input
                  v-model="deployForm.snippet"
                  type="textarea"
                  :rows="8"
                  :placeholder="t('deploySnippetPlaceholder')"
                  style="width: 100%"
                  class="snippet-input"
                />
                <div class="section-desc">{{ t('deploySnippetTip') }}</div>

                <!-- 片段位置 -->
                <div class="section-label" style="margin-top: 12px;">{{ t('deploySnippetPosition') }}</div>
                <el-radio-group v-model="deployForm.snippet_position" size="small">
                  <el-radio-button label="smart">{{ t('deploySnippetSmart') }}</el-radio-button>
                  <el-radio-button label="append">{{ t('deploySnippetAppend') }}</el-radio-button>
                  <el-radio-button label="prepend">{{ t('deploySnippetPrepend') }}</el-radio-button>
                  <el-radio-button label="replace">{{ t('deploySnippetReplace') }}</el-radio-button>
                </el-radio-group>
                <div v-if="deployForm.snippet_position === 'smart'" class="smart-mode-tip">
                  <el-icon class="tip-icon"><InfoFilled /></el-icon>
                  <span class="tip-text">{{ t('deploySmartModeTip') }}</span>
                </div>

                <!-- 基础配置选择（可选） -->
                <div class="section-label" style="margin-top: 12px;">{{ t('deploySnippetBaseConfig') }}</div>
                <el-select
                  v-model="deployForm.base_backup_file"
                  :placeholder="t('deploySelectBackupOptional')"
                  style="width: 100%"
                  clearable
                >
                  <el-option
                    v-for="backup in backups"
                    :key="backup.id"
                    :label="`${backup.device_name} - ${backup.backup_file}`"
                    :value="backup.backup_file"
                  >
                    <div class="backup-option">
                      <span class="backup-name">{{ backup.device_name }}</span>
                      <span class="backup-file">{{ backup.backup_file }}</span>
                      <span class="backup-time">{{ formatDateTime(backup.backup_time) }}</span>
                    </div>
                  </el-option>
                </el-select>
                <div class="section-desc">{{ t('deploySnippetBaseTip') }}</div>
              </div>

              <!-- 目标设备 -->
              <div class="form-section">
                <div class="section-label required">{{ t('deployTargetDevice') }}</div>
                <el-select
                  v-model="deployForm.target_devices"
                  multiple
                  :placeholder="t('deploySelectDeviceMultiple')"
                  style="width: 100%"
                  filterable
                  @change="handleDeviceChange"
                >
                  <el-option
                    v-for="device in devices"
                    :key="device.id"
                    :label="`${device.name} (${device.ip})`"
                    :value="device.id"
                    :disabled="device.status === 'offline'"
                  >
                    <div class="device-option">
                      <span class="device-name">{{ device.name }}</span>
                      <span class="device-ip">{{ device.ip }}</span>
                      <el-tag
                        v-if="device.status !== 'online'"
                        size="small"
                        type="danger"
                      >
                        {{ device.status }}
                      </el-tag>
                    </div>
                  </el-option>
                </el-select>
                <div class="section-desc">{{ t('deployDeviceTip') }}</div>

                <!-- 执行模式选择 -->
                <div v-if="deployForm.target_devices.length > 1" class="execution-mode-section">
                  <div class="mode-options">
                    <el-radio-group v-model="executionMode" size="small">
                      <el-radio-button value="serial">
                        <span class="mode-option-content">
                          <el-icon><Loading /></el-icon>
                          <span>{{ t('deploySerialModeLabel') }}</span>
                        </span>
                      </el-radio-button>
                      <el-radio-button value="parallel">
                        <span class="mode-option-content">
                          <el-icon><CircleCheckFilled /></el-icon>
                          <span>{{ t('deployParallelModeLabel') }}</span>
                        </span>
                      </el-radio-button>
                    </el-radio-group>
                  </div>
                  <div v-if="executionMode === 'parallel'" class="parallel-limit-input">
                    <span class="limit-label">{{ t('deployParallelLimitLabel') }}</span>
                    <el-input-number
                      v-model="parallelLimit"
                      :min="1"
                      :max="5"
                      size="small"
                      controls-position="right"
                    />
                    <span class="limit-tip">{{ t('deployParallelLimitTip') }}</span>
                  </div>
                </div>
              </div>

              <!-- 变量替换 -->
              <div v-if="deployForm.mode === 'template' && availableVariables.length > 0" class="form-section">
                <div class="section-label">{{ t('deployVariableReplace') }}</div>
                <div class="variables-list">
                  <div
                    v-for="(variable, index) in deployForm.variables"
                    :key="index"
                    class="variable-item"
                  >
                    <el-select
                      v-model="variable.key"
                      :placeholder="t('deploySelectVariable')"
                      style="width: 140px"
                      size="small"
                    >
                      <el-option
                        v-for="v in availableVariables"
                        :key="v.key"
                        :label="v.key"
                        :value="v.key"
                      />
                    </el-select>
                    <el-input
                      v-model="variable.value"
                      :placeholder="getVariablePlaceholder(variable.key)"
                      style="flex: 1"
                      size="small"
                    />
                    <el-button
                      size="small"
                      type="danger"
                      link
                      @click="removeVariable(index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button size="small" @click="addVariable" class="add-var-btn">
                    <el-icon><Plus /></el-icon>
                    {{ t('deployAddVariable') }}
                  </el-button>
                </div>
              </div>

              <!-- 干运行选项 -->
              <div class="form-section">
                <el-checkbox v-model="deployForm.dry_run">
                  {{ t('deployDryRun') }}
                </el-checkbox>
                <div class="section-desc">{{ t('deployPreviewTip') }}</div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section actions-section">
                <button
                  type="button"
                  class="nav-action-btn secondary preview-btn"
                  @click="previewDeploy"
                  :disabled="!canDeploy || !deployForm.dry_run"
                  :class="{ disabled: !canDeploy || !deployForm.dry_run }"
                >
                  <el-icon><View /></el-icon>
                  {{ t('deployPreviewChange') }}
                </button>
                <button
                  type="button"
                  class="nav-action-btn deploy-btn"
                  @click="confirmDeploy"
                  :disabled="!canDeploy"
                  :class="{ disabled: !canDeploy }"
                >
                  <el-icon><Upload /></el-icon>
                  {{ t('deployStart') }}
                </button>
              </div>
            </el-form>
          </div>
        </el-col>

        <!-- 右侧：执行面板 -->
        <el-col :span="16" class="execution-column">
          <div class="execution-panel" :class="{ active: executionStatus !== 'idle' }">
            <!-- 执行进度概览 -->
            <div class="execution-overview">
              <div class="overview-header">
                <div class="overview-title">
                  <el-icon v-if="executionStatus === 'running'" class="is-loading"><Loading /></el-icon>
                  <span>{{ t('deployExecutionTitle') }}</span>
                </div>
                <div class="overview-actions">
                  <div v-if="elapsedTime > 0" class="elapsed-time">
                    {{ t('deployElapsedTime') }}: {{ formatDuration(elapsedTime) }}
                  </div>
                  <el-button
                    v-if="executionStatus === 'completed' && hasRollbackAvailable"
                    type="warning"
                    size="small"
                    @click="handleRollback"
                  >
                    <el-icon><RefreshLeft /></el-icon>
                    {{ t('deployRollback') }}
                  </el-button>
                </div>
              </div>

              <div class="progress-overview">
                <div class="progress-item">
                  <div class="progress-label">{{ t('deployTotalDevices') }}</div>
                  <div class="progress-value">{{ totalDevices }}</div>
                </div>
                <div class="progress-item success">
                  <div class="progress-label">{{ t('deployCompleted') }}</div>
                  <div class="progress-value">{{ completedDevices }}</div>
                </div>
                <div class="progress-item warning">
                  <div class="progress-label">{{ t('deployInProgress') }}</div>
                  <div class="progress-value">{{ inProgressDevices }}</div>
                </div>
                <div class="progress-item error">
                  <div class="progress-label">{{ t('deployFailed') }}</div>
                  <div class="progress-value">{{ failedDevices }}</div>
                </div>
              </div>

              <el-progress
                :percentage="progressPercentage"
                :status="progressStatus"
                :stroke-width="12"
                class="overall-progress"
              />
            </div>

            <!-- 设备执行状态 -->
            <div class="devices-section">
              <div class="section-header">
                <span class="section-title">{{ t('deployDeviceExecution') }}</span>
              </div>
              <div class="device-cards">
                <div
                  v-for="device in deviceExecutions"
                  :key="device.device_id"
                  class="device-card"
                  :class="{
                    active: selectedDevice?.device_id === device.device_id,
                    success: device.status === 'completed',
                    error: device.status === 'failed',
                    skipped: device.status === 'skipped',
                    running: device.status === 'running'
                  }"
                  @click="selectDevice(device)"
                >
                  <div class="device-card-header">
                    <div class="device-info">
                      <el-icon
                        v-if="device.status === 'completed'"
                        class="status-icon success"
                      >
                        <CircleCheckFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'failed'"
                        class="status-icon error"
                      >
                        <CircleCloseFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'skipped'"
                        class="status-icon skipped"
                      >
                        <Minus />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'running'"
                        class="status-icon running is-loading"
                      >
                        <Loading />
                      </el-icon>
                      <el-icon v-else class="status-icon pending">
                        <Timer />
                      </el-icon>
                      <div class="device-text">
                        <div class="device-name">{{ device.device_name }}</div>
                        <div class="device-ip">{{ device.device_ip }}</div>
                      </div>
                    </div>
                    <el-tag
                      :type="getDeviceStatusType(device.status)"
                      size="small"
                      effect="dark"
                    >
                      {{ getDeviceStatusText(device.status) }}
                    </el-tag>
                  </div>
                  <el-progress
                    :percentage="device.progress"
                    :status="getDeviceProgressStatus(device.status)"
                    :stroke-width="4"
                    class="device-progress"
                  />
                  <div v-if="device.message" class="device-message">
                    {{ device.message }}
                  </div>
                </div>
              </div>
            </div>

            <!-- CLI 区域：并排显示命令输出和部署历史 -->
            <div class="cli-section-parallel">
              <!-- 左侧：CLI 命令输出（部署结果） -->
              <div class="cli-panel">
                <div class="cli-panel-header">
                  <span class="cli-panel-title">
                    {{ t('deployCliOutput') }}
                    <span v-if="selectedDevice" class="device-badge">{{ selectedDevice.device_name }}</span>
                  </span>
                  <el-tag v-if="executionStatus === 'running'" type="warning" size="small">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    {{ t('deployExecuting') }}
                  </el-tag>
                  <el-tag v-else-if="executionStatus === 'completed'" type="success" size="small">
                    {{ t('deployCompleted') }}
                  </el-tag>
                  <button class="nav-action-btn secondary small" @click="clearCliOutput">
                    <el-icon><Delete /></el-icon>
                    {{ t('actionClear') }}
                  </button>
                </div>
                <div ref="cliOutputRef" class="cli-panel-output">
                  <div
                    v-for="(line, index) in selectedDevice?.cliLogs || []"
                    :key="index"
                    class="cli-line"
                    :class="line.type"
                  >
                    <span class="cli-timestamp">{{ formatTime(line.timestamp) }}</span>
                    <span class="cli-content">{{ line.content }}</span>
                  </div>
                  <div v-if="!selectedDevice || selectedDevice.cliLogs.length === 0" class="cli-empty">
                    {{ t('deployCliEmpty') }}
                  </div>
                </div>
              </div>

              <!-- 右侧：部署历史记录 -->
              <div class="cli-panel history-panel">
                <div class="cli-panel-header">
                  <span class="cli-panel-title">{{ t('deployHistory') }}</span>
                </div>
                <div class="history-list" v-loading="historyLoading">
                  <!-- 任务链分组显示 (DNAC风格) -->
                  <div v-for="(group, gIdx) in groupedHistory" :key="group.parent.id || gIdx" class="history-group">
                    <!-- 主记录 (DevOps现代化风格) -->
                    <div
                      class="deploy-card"
                      :class="{
                        selected: selectedHistoryId === group.parent.id,
                        success: group.parent.success,
                        failed: !group.parent.success
                      }"
                      @click="loadHistoryRecord(group.parent)"
                    >
                      <!-- 左侧状态指示条 -->
                      <div class="card-status-bar" :class="group.parent.success ? 'success' : 'failed'"></div>

                      <!-- 卡片主体 -->
                      <div class="card-body">
                        <!-- 第一行：状态点 + 时间 + 状态标签 -->
                        <div class="card-header">
                          <div class="status-dot" :class="group.parent.success ? 'success' : 'failed'"></div>
                          <span class="card-time">{{ formatDateTime(group.parent.timestamp) }}</span>
                          <div class="header-badges">
                            <span class="mini-badge" :class="group.parent.success ? 'success' : 'failed'">
                              {{ group.parent.success ? t('statusSuccess') : t('statusFailed') }}
                            </span>
                            <span v-if="hasBeenRolledBack(group.parent)" class="status-label rollback">
                              {{ t('deployRolledBack') }}
                            </span>
                            <span v-else-if="canRollback(group.parent)" class="status-label can-rollback">
                              {{ t('deployCanRollback') }}
                            </span>
                          </div>
                        </div>

                        <!-- 第二行：metadata（用户 | 驱动 | 模式 | 设备数） -->
                        <div class="card-meta">
                          <span class="meta-item" v-if="group.parent.username">
                            <el-icon :size="12"><User /></el-icon>
                            {{ group.parent.username }}
                          </span>
                          <span class="meta-divider">·</span>
                          <span class="meta-item">{{ group.parent.engine }}</span>
                          <span class="meta-divider" v-if="group.parent.mode">·</span>
                          <span class="meta-item" v-if="group.parent.mode">{{ group.parent.mode }}</span>
                          <span class="meta-divider">·</span>
                          <span class="meta-item">
                            <el-icon :size="12"><Monitor /></el-icon>
                            {{ group.parent.total_devices || 0 }} {{ t('deployDevices') }}
                          </span>
                          <span class="meta-divider" v-if="group.children.length > 0">·</span>
                          <span class="meta-item children-count" v-if="group.children.length > 0" @click.stop="toggleGroupExpand(group.parentId)">
                            <el-icon :size="12">
                              <ArrowRight v-if="!isGroupExpanded(group.parentId)" />
                              <ArrowDown v-else />
                            </el-icon>
                            {{ group.children.length }} {{ t('deployRelatedRecords') }}
                          </span>
                        </div>

                        <!-- 第三行：统计 + 操作 -->
                        <div class="card-footer">
                          <div class="result-summary">
                            <span class="summary-badge success" v-if="group.parent.success_count > 0">
                              ✓ {{ group.parent.success_count }}
                            </span>
                            <span class="summary-badge failed" v-if="group.parent.failed_count > 0">
                              ✗ {{ group.parent.failed_count }}
                            </span>
                          </div>
                          <div class="card-actions" v-if="selectedHistoryId === group.parent.id">
                            <el-button
                              v-if="canRollback(group.parent)"
                              type="warning"
                              size="small"
                              plain
                              round
                              @click.stop="handleHistoryRollback(group.parent)"
                            >
                              {{ t('deployRollback') }}
                            </el-button>
                            <el-button
                              v-else
                              type="primary"
                              size="small"
                              plain
                              round
                              @click.stop="handleRedeploy(group.parent)"
                            >
                              {{ t('deployRedeploy') }}
                            </el-button>
                            <el-button
                              type="info"
                              size="small"
                              plain
                              round
                              @click.stop="handleDeleteHistory(group.parent)"
                            >
                              {{ t('actionDelete') }}
                            </el-button>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 子记录 -->
                    <Transition name="expand">
                      <div v-if="isGroupExpanded(group.parentId) && group.children.length > 0" class="children-list">
                        <div
                          v-for="child in group.children"
                          :key="child.id"
                          class="history-item child-record"
                          :class="{ active: selectedHistoryId === child.id }"
                          @click="loadHistoryRecord(child)"
                        >
                        <div class="chain-line"></div>
                        <div class="operation-icon small">
                          <el-icon :size="12" :class="child.operation_type">
                            <RefreshLeft v-if="child.operation_type === 'rollback'" />
                            <Refresh v-if="child.operation_type === 'redeploy'" />
                          </el-icon>
                        </div>
                        <div class="history-main-info compact">
                          <div class="history-row">
                            <span class="history-time small">{{ formatDateTime(child.timestamp) }}</span>
                            <el-tag :type="child.success ? 'success' : 'danger'" size="small">
                              {{ child.success ? t('statusSuccess') : t('statusFailed') }}
                            </el-tag>
                            <el-tag v-if="child.operation_type === 'rollback'" type="info" size="small" effect="plain">
                              {{ t('deployRollbackRecord') }}
                            </el-tag>
                            <el-tag v-else type="warning" size="small" effect="plain">
                              {{ t('deployRedeployRecord') }}
                            </el-tag>
                          </div>
                        </div>
                        <div class="child-actions" v-if="selectedHistoryId === child.id">
                          <el-button type="danger" size="small" link @click.stop="handleDeleteHistory(child)">
                            <el-icon><Delete /></el-icon>
                          </el-button>
                        </div>
                          </div>
                      </div>
                    </Transition>

                    <!-- 操作按钮 -->
                    <div class="group-actions" v-if="selectedHistoryId === group.parent.id && group.parent.operation_type === 'deploy'">
                      <el-button
                        v-if="canRollback(group.parent)"
                        type="warning"
                        size="small"
                        @click.stop="handleHistoryRollback(group.parent)"
                      >
                        <el-icon><RefreshLeft /></el-icon>
                        {{ t('deployRollback') }}
                      </el-button>
                      <el-button
                        v-else
                        type="primary"
                        size="small"
                        @click.stop="handleRedeploy(group.parent)"
                      >
                        <el-icon><Refresh /></el-icon>
                        {{ t('deployRedeploy') }}
                      </el-button>
                      <el-button
                        type="danger"
                        size="small"
                        @click.stop="handleDeleteHistory(group.parent)"
                      >
                        <el-icon><Delete /></el-icon>
                        {{ t('deployDeleteHistory') }}
                      </el-button>
                    </div>
                  </div>

                  <div v-if="groupedHistory.length === 0" class="cli-empty">
                    {{ t('deployNoHistory') }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </section>

    <!-- 配置差异预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="t('deployPreviewDialog')"
      width="90%"
      top="5vh"
      destroy-on-close
      align-center
    >
      <el-skeleton v-if="previewLoading" :rows="10" animated />

      <div v-else class="preview-content">
        <!-- 影响分析摘要 -->
        <div class="impact-summary">
          <div class="impact-header">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ t('deployImpactAnalysis') }}</span>
          </div>
          <div class="impact-stats">
            <div class="impact-item">
              <span class="impact-label">{{ t('diffTotalChanges') }}</span>
              <span class="impact-value">{{ impactAnalysis.totalChanges }}</span>
            </div>
            <div class="impact-item">
              <span class="impact-label">{{ t('diffAffectedServices') }}</span>
              <span class="impact-value">
                {{ impactAnalysis.affectedServices.length > 0
                  ? impactAnalysis.affectedServices.join(', ')
                  : t('diffNoServices') }}
              </span>
            </div>
            <div class="impact-item">
              <span class="impact-label">{{ t('diffEstimatedDowntime') }}</span>
              <span class="impact-value">{{ impactAnalysis.estimatedDowntime }}s</span>
            </div>
            <div class="impact-item">
              <span class="impact-label">{{ t('diffRiskLevel') }}</span>
              <el-tag :type="getRiskLevelType(impactAnalysis.riskLevel)" size="large">
                {{ getRiskLevelText(impactAnalysis.riskLevel) }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 设备选择 -->
        <div class="device-selector">
          <span class="selector-label">{{ t('diffSelectDevice') }}:</span>
          <el-select v-model="selectedPreviewDevice" style="width: 300px">
            <el-option
              v-for="result in previewResults"
              :key="result.device_id"
              :label="`${result.device_name} (${result.device_ip})`"
              :value="result"
            />
          </el-select>
        </div>

        <!-- 设备差异 -->
        <div v-if="selectedPreviewDevice" class="device-diff">
          <div class="diff-device-header">
            <div class="device-info">
              <h4>{{ selectedPreviewDevice.device_name }}</h4>
              <span class="device-ip">{{ selectedPreviewDevice.device_ip }}</span>
            </div>
            <el-tag
              :type="getRiskLevelType(selectedPreviewDevice.impact?.risk_level)"
              size="small"
            >
              {{ getRiskLevelText(selectedPreviewDevice.impact?.risk_level) }}
            </el-tag>
          </div>

          <DiffViewer
            v-if="selectedPreviewDevice.diff"
            :old-config="selectedPreviewDevice.old_config || ''"
            :new-config="selectedPreviewDevice.new_config || ''"
            :diff-data="selectedPreviewDevice.diff"
            :is-dark="isDark"
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showPreviewDialog = false">
            {{ t('actionClose') }}
          </el-button>
          <el-button type="primary" @click="openScheduleDialog">
            <el-icon><Calendar /></el-icon>
            {{ t('deploySchedule') }}
          </el-button>
          <el-button type="success" @click="confirmDeployFromPreview">
            <el-icon><Upload /></el-icon>
            {{ t('deployStart') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 维护窗口预约对话框 -->
    <el-dialog
      v-model="showScheduleDialog"
      :title="t('deployScheduleDialog')"
      width="600px"
      align-center
    >
      <div class="schedule-content">
        <p class="schedule-desc">{{ t('deployScheduleDesc') }}</p>

        <el-form label-position="top">
          <el-form-item :label="t('deploySelectWindow')">
            <el-radio-group v-model="selectedWindow" class="window-options">
              <el-radio-button
                v-for="window in maintenanceWindows"
                :key="window.id"
                :label="window.id"
                :disabled="!window.available"
                class="window-option"
              >
                <div class="window-label">{{ getWindowLabel(window) }}</div>
                <div class="window-time">{{ window.start_time }} - {{ window.end_time }}</div>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <div v-if="isScheduled" class="schedule-confirmation">
          <el-alert
            :title="t('deployScheduledConfirm', { time: scheduledTime })"
            type="success"
            :closable="false"
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showScheduleDialog = false">
            {{ t('actionCancel') }}
          </el-button>
          <el-button type="primary" @click="scheduleDeployTask">
            {{ t('deployConfirmSchedule') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 变量说明对话框 -->
    <el-dialog
      v-model="showVariableHelp"
      :title="t('deployVariableDialog')"
      width="800px"
      align-center
      draggable
    >
      <el-table :data="allVariables" style="width: 100%" stripe>
        <el-table-column prop="key" :label="t('deployVariableName')" width="200" />
        <el-table-column prop="description" :label="t('deployDescription')" />
        <el-table-column prop="example" :label="t('deployExampleValue')" width="200" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  QuestionFilled,
  Plus,
  View,
  Upload,
  CircleClose,
  WarningFilled,
  CircleCheckFilled,
  CircleCloseFilled,
  Loading,
  Timer,
  Document,
  Files,
  Calendar,
  Edit,
  Delete,
  User,
  Monitor,
  RefreshLeft,
  Refresh,
  Promotion,
  ArrowRight,
  ArrowDown,
  Minus
} from '@element-plus/icons-vue'
import {
  getDevices,
  getBackups,
  getTemplates,
  getTemplate,
  previewDeploy as previewDeployApi,
  executeDeploy as executeDeployApi,
  rollbackDeploy as rollbackDeployApi,
  getCompatibleVariables,
  getMaintenanceWindows,
  scheduleDeploy,
  getDeployHistory,
  getDeployHistoryDetail,
  deleteDeployHistory
} from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import DiffViewer from '@/components/DiffViewer.vue'

const { t } = useI18n()

// 暗黑模式检测
const isDark = computed(() => document.documentElement.classList.contains('dark'))

// 执行模式控制
const executionMode = ref('serial')  // serial | parallel
const parallelLimit = ref(1)  // 并行数量，建议不超过3

// 数据
const devices = ref([])
const backups = ref([])
const templates = ref([])
const allVariables = ref([])
const availableVariables = ref([])
const loading = ref(false)

// 表单
const deployForm = ref({
  mode: 'backup',
  engine: 'netmiko',  // napalm | netmiko，默认 netmiko（无需 SCP）
  napalm_mode: 'merge',  // merge | replace，默认 merge
  transfer_mode: 'inline',  // scp | inline，默认 inline（短配置适用，无需 SCP）
  backup_file: '',
  template_id: '',
  snippet: '',
  snippet_position: 'smart',
  base_backup_file: '',
  target_devices: [],
  variables: [],
  dry_run: false
})

// 执行状态
const executionStatus = ref('idle') // idle, running, completed, failed, aborted
const taskId = ref(null)
const startTime = ref(null)
const elapsedTime = ref(0)
const deviceExecutions = ref([])
const selectedDevice = ref(null)
const aborting = ref(false)
const showVariableHelp = ref(false)
const cliOutputRef = ref(null)

// 部署历史记录（从后端 API 加载）
const deployHistory = ref([])
const selectedHistoryId = ref(null)
const currentHistoryId = ref(null)  // 当前正在操作的部署记录ID（用于回滚关联）
const historyLoading = ref(false)

// 加载历史记录
const loadHistory = async () => {
  try {
    historyLoading.value = true
    const res = await getDeployHistory({ limit: 50 })
    deployHistory.value = res.history || []
  } catch (e) {
    console.error('Failed to load deploy history:', e)
    ElMessage.error(t('deployLoadHistoryFailed'))
  } finally {
    historyLoading.value = false
  }
}

// 审批相关状态
const approvalStatus = ref('none') // none, pending, approved, rejected
const approvalId = ref(null)
const approvalLevel = ref(null)
const approvalInfo = ref(null)
const showApprovalDialog = ref(false)
const approvalComment = ref('')
const rejectionReason = ref('')

// Phase 3: 配置差异预览
const previewResults = ref([])
const showPreviewDialog = ref(false)
const previewLoading = ref(false)
const selectedPreviewDevice = ref(null)

// Phase 3: 维护窗口
const maintenanceWindows = ref([])
const selectedWindow = ref(null)
const showScheduleDialog = ref(false)
const isScheduled = ref(false)
const scheduledTime = ref(null)

// Phase 3: 影响分析
const impactAnalysis = ref({
  totalChanges: 0,
  affectedServices: [],
  estimatedDowntime: 0,
  riskLevel: 'low',
  highRiskDevices: 0
})

// 计算属性
const canDeploy = computed(() => {
  if (deployForm.value.target_devices.length === 0) return false
  if (deployForm.value.mode === 'backup') {
    return !!deployForm.value.backup_file
  }
  if (deployForm.value.mode === 'snippet') {
    return !!deployForm.value.snippet.trim()
  }
  return !!deployForm.value.template_id
})

const totalDevices = computed(() => deviceExecutions.value.length)
const completedDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'completed').length
)
const inProgressDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'running').length
)
const failedDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'failed').length
)

const progressPercentage = computed(() => {
  if (totalDevices.value === 0) return 0
  const totalProgress = deviceExecutions.value.reduce((sum, d) => sum + d.progress, 0)
  return Math.round(totalProgress / totalDevices.value)
})

const progressStatus = computed(() => {
  if (executionStatus.value === 'failed') return 'exception'
  if (executionStatus.value === 'completed') return 'success'
  return ''
})

const hasRollbackAvailable = computed(() => {
  return deviceExecutions.value.some(d => d.rollback_available)
})

// 加载数据
const loadDevices = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getDevices(),
      'devices',
      {},
      { forceRefresh: force }
    )
    devices.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadDeviceFailed'))
    }
  }
}, 300)

const loadBackups = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getBackups({ limit: 50 }),
      'backups',
      { limit: 50 },
      { forceRefresh: force }
    )
    backups.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadBackupFailed'))
    }
  }
}, 300)

const loadTemplates = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getTemplates(),
      'templates',
      {},
      { forceRefresh: force }
    )
    templates.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadTemplateFailed'))
    }
  }
}, 300)

const loadCompatibleVariables = async () => {
  try {
    const data = await cachedRequest(
      () => getCompatibleVariables(),
      'compatibleVariables',
      {},
      { ttl: 300000 }  // 缓存 5 分钟
    )
    allVariables.value = data.variables || []
  } catch (error) {
    // Silent fail
  }
}

const loadTemplateVariables = async (templateId) => {
  if (!templateId) {
    availableVariables.value = []
    deployForm.value.variables = []
    return
  }

  try {
    const data = await cachedRequest(
      () => getTemplate(templateId),
      'template',
      { id: templateId },
      { ttl: 60000 }  // 缓存 1 分钟
    )
    if (data.variables) {
      try {
        let vars = typeof data.variables === 'string'
          ? JSON.parse(data.variables)
          : data.variables

        // 处理两种格式：
        // 1. 对象格式: {"hostname": "SW-Office", "domain": "local"}
        // 2. 数组格式: [{key: "hostname", default: "SW-Office"}]
        if (vars && typeof vars === 'object' && !Array.isArray(vars)) {
          // 对象格式转为数组
          vars = Object.entries(vars).map(([key, value]) => ({
            key: key,
            default: typeof value === 'object' ? value.default || '' : value,
            description: typeof value === 'object' ? value.description || '' : ''
          }))
        }

        availableVariables.value = vars || []
        deployForm.value.variables = (vars || []).map(v => ({
          key: v.key,
          value: v.default || ''
        }))
      } catch (e) {
        console.error('Parse template variables failed:', e)
        deployForm.value.variables = []
      }
    } else {
      deployForm.value.variables = []
    }
  } catch (error) {
    ElMessage.error(t('deployLoadTemplateVarFailed'))
  }
}

const handleDeviceChange = () => {
  // 重置设备执行列表
  deviceExecutions.value = deployForm.value.target_devices.map(id => {
    const device = devices.value.find(d => d.id === id)
    return {
      device_id: id,
      device_name: device?.name || '',
      device_ip: device?.ip || '',
      status: 'pending',
      progress: 0,
      message: '',
      cliLogs: [],
      rollback_available: false
    }
  })
}

// 变量操作
const getVariablePlaceholder = (key) => {
  const v = allVariables.value.find(v => v.key === key)
  return v ? t('deployExample') + v.example : ''
}

const addVariable = () => {
  deployForm.value.variables.push({ key: '', value: '' })
}

const removeVariable = (index) => {
  deployForm.value.variables.splice(index, 1)
}

// 设备状态
const getDeviceStatusType = (status) => {
  const types = { pending: 'info', running: 'primary', completed: 'success', failed: 'danger', skipped: 'warning' }
  return types[status] || 'info'
}

const getDeviceStatusText = (status) => {
  const texts = {
    pending: t('deployDevicePending'),
    running: t('deployDeviceRunning'),
    completed: t('deployDeviceCompleted'),
    failed: t('deployDeviceFailed'),
    skipped: t('deployDeviceSkipped')
  }
  return texts[status] || status
}

const getDeviceProgressStatus = (status) => {
  if (status === 'failed') return 'exception'
  if (status === 'completed') return 'success'
  return ''
}

const selectDevice = (device) => {
  selectedDevice.value = device
}

const clearCliOutput = () => {
  if (selectedDevice.value) {
    selectedDevice.value.cliLogs = []
  }
}

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (cliOutputRef.value) {
      cliOutputRef.value.scrollTop = cliOutputRef.value.scrollHeight
    }
  })
}

// 加载历史记录详情到左侧面板
const loadHistoryRecord = async (record) => {
  selectedHistoryId.value = record.id

  // 如果 record 只有摘要信息，从 API 加载完整详情
  let fullRecord = record
  if (!record.deviceResults || record.deviceResults.length === 0 || !record.deviceResults[0]?.logs) {
    try {
      fullRecord = await getDeployHistoryDetail(record.id)
    } catch (e) {
      console.error('Failed to load history detail:', e)
      return
    }
  }

  // 清空当前设备执行状态，使用保存的状态
  deviceExecutions.value = (fullRecord.deviceResults || []).map(d => ({
    device_id: d.device_id,
    device_name: d.device_name,
    status: d.status || 'completed',  // 使用保存的状态，默认 completed
    message: d.message || '',
    progress: 100,
    cliLogs: d.logs || [],
    rollback_available: d.rollback_available || false
  }))
  // 选中第一个设备
  if (deviceExecutions.value.length > 0) {
    selectedDevice.value = deviceExecutions.value[0]
  }
}

// 检查历史记录是否已被回滚
const hasBeenRolledBack = (record) => {
  if (record.mode === 'rollback') return false  // 回滚记录本身不算"已被回滚"
  // 检查是否所有成功设备都已被回滚（rollback_available = false 且有 rollback_status）
  const successDevices = record.deviceResults?.filter(d => d.status === 'completed') || []
  if (successDevices.length === 0) return false
  return successDevices.every(d => d.rollback_status === 'rolled_back')
}

// 检查历史记录是否可以回滚
const canRollback = (record) => {
  if (record.mode === 'rollback') return false  // 回滚记录不能再回滚
  if (record.engine !== 'napalm') return false  // 只有 NAPALM 支持回滚
  // 检查是否有 rollback_available = true 的设备
  return record.deviceResults?.some(d => d.rollback_available) || false
}

// 任务链分组：将部署历史按父子关系分组
const groupedHistory = computed(() => {
  const groups = []
  const processedIds = new Set()

  // 先找出所有父记录（原始部署）
  const parentRecords = deployHistory.value.filter(r => !r.parent_id && r.operation_type === 'deploy')

  for (const parent of parentRecords) {
    if (processedIds.has(parent.id)) continue

    // 找出所有子记录（回滚、重新部署）
    const children = deployHistory.value
      .filter(r => r.parent_id === parent.id)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)) // 按时间倒序

    groups.push({
      parent,
      children,
      parentId: parent.id  // 用于跟踪展开状态
    })

    processedIds.add(parent.id)
    children.forEach(c => processedIds.add(c.id))
  }

  // 再处理独立的记录（没有父记录的回滚等）
  const orphanRecords = deployHistory.value.filter(r => !processedIds.has(r.id))
  for (const orphan of orphanRecords) {
    groups.push({
      parent: orphan,
      children: [],
      parentId: orphan.id
    })
  }

  return groups
})

// 展开状态存储（响应式）
const expandedGroups = ref({})

// 判断组是否展开
const isGroupExpanded = (parentId) => {
  // 默认展开，除非明确设置为 false
  return expandedGroups.value[parentId] !== false
}

// 展开/折叠任务链
const toggleGroupExpand = (parentId) => {
  const current = expandedGroups.value[parentId]
  expandedGroups.value[parentId] = current === false ? true : false
}

// 从历史记录执行回滚
const handleHistoryRollback = async (record) => {
  // 先加载历史记录到设备执行列表
  await loadHistoryRecord(record)
  // 然后执行回滚
  await handleRollback()
}

// 从历史记录重新部署
const handleRedeploy = async (record) => {
  try {
    // 如果需要完整配置，从 API 加载详情
    let fullRecord = record
    if (!record.deployConfig && !record.deploy_config) {
      try {
        fullRecord = await getDeployHistoryDetail(record.id)
      } catch (e) {
        ElMessage.warning(t('deployRedeployNoConfig'))
        return
      }
    }

    // 检查是否有部署配置
    const config = fullRecord.deployConfig || fullRecord.deploy_config
    if (!config) {
      ElMessage.warning(t('deployRedeployNoConfig'))
      return
    }

    const deviceIds = fullRecord.deviceResults?.map(d => d.device_id) || fullRecord.target_devices?.map(d => d.id) || []
    if (deviceIds.length === 0) {
      ElMessage.warning(t('deployNoDevicesInHistory'))
      return
    }

    await ElMessageBox.confirm(
      t('deployRedeployConfirmDetail', {
        count: deviceIds.length,
        engine: config.engine,
        mode: config.mode
      }),
      t('deployRedeployTitle'),
      { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'info' }
    )

    // 恢复部署配置
    deployForm.value.mode = config.mode || 'backup'
    deployForm.value.engine = config.engine || 'napalm'
    deployForm.value.napalm_mode = config.napalm_mode || 'merge'
    deployForm.value.backup_file = config.backup_file || ''
    deployForm.value.template_id = config.template_id || ''
    deployForm.value.snippet = config.snippet || ''
    deployForm.value.snippet_position = config.snippet_position || 'append'
    deployForm.value.base_backup_file = config.base_backup_file || ''
    deployForm.value.target_devices = deviceIds
    // variables 可能是对象格式，需要转换为数组
    if (config.variables && typeof config.variables === 'object' && !Array.isArray(config.variables)) {
      deployForm.value.variables = Object.entries(config.variables).map(([key, value]) => ({ key, value }))
    } else {
      deployForm.value.variables = config.variables || []
    }
    deployForm.value.dry_run = false

    // 检查必要配置是否存在
    let missingConfig = ''
    if (deployForm.value.mode === 'backup' && !deployForm.value.backup_file) {
      missingConfig = t('deploySelectBackupFile')
    } else if (deployForm.value.mode === 'template' && !deployForm.value.template_id) {
      missingConfig = t('deploySelectTemplate')
    } else if (deployForm.value.mode === 'snippet' && !deployForm.value.snippet) {
      missingConfig = t('deployInputSnippet')
    }

    if (missingConfig) {
      ElMessage.warning(t('deployRedeployConfigMissing') + ': ' + missingConfig)
      return
    }

    // 记录父记录 ID，用于建立任务链
    redeployParentId.value = record.id

    // 直接执行部署
    await executeDeploy()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新部署失败:', error)
      ElMessage.error(t('deployRedeployFailed'))
    }
  }
}

// 删除历史记录
const handleDeleteHistory = async (record) => {
  try {
    await ElMessageBox.confirm(
      t('deployDeleteConfirm'),
      t('deployDeleteHistory'),
      { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
    )

    await deleteDeployHistory(record.id)
    ElMessage.success(t('deployDeleteSuccess'))
    // 重新加载历史记录
    await loadHistory()

    // 如果删除的是当前选中的记录，清空选中状态
    if (selectedHistoryId.value === record.id) {
      selectedHistoryId.value = null
      deviceExecutions.value = []
      selectedDevice.value = null
    }
  } catch (error) {
    if (error !== 'cancel') {
      if (error.response?.status === 403) {
        ElMessage.error(t('deployDeletePermissionDenied'))
      } else {
        ElMessage.error(t('deployDeleteFailed'))
      }
      console.error('删除历史记录失败:', error)
    }
  }
}

// 重新部署的父记录 ID
const redeployParentId = ref(null)

// 预览部署
const previewDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  const deployData = {
    mode: deployForm.value.mode,
    engine: deployForm.value.engine,
    napalm_mode: deployForm.value.napalm_mode,
    backup_file: deployForm.value.backup_file,
    template_id: deployForm.value.template_id,
    snippet: deployForm.value.snippet,
    snippet_position: deployForm.value.snippet_position,
    base_backup_file: deployForm.value.base_backup_file,
    target_devices: deployForm.value.target_devices,
    variables: {}
  }

  deployForm.value.variables.forEach(v => {
    if (v.key) deployData.variables[v.key] = v.value
  })

  previewLoading.value = true
  showPreviewDialog.value = true

  try {
    const result = await previewDeployApi(deployData)
    previewResults.value = result.preview || []
    selectedPreviewDevice.value = previewResults.value[0] || null

    // 更新影响分析
    impactAnalysis.value = {
      totalChanges: result.summary?.total_changes || 0,
      highRiskDevices: result.summary?.high_risk_devices || 0,
      affectedServices: [...new Set(previewResults.value.flatMap(p => p.impact?.affected_services || []))],
      estimatedDowntime: Math.max(...previewResults.value.map(p => p.impact?.estimated_downtime_seconds || 0)),
      riskLevel: result.summary?.high_risk_devices > 0 ? 'high' :
                 result.summary?.total_changes > 20 ? 'medium' : 'low'
    }

    ElMessage.success(t('deployPreviewSuccess'))
  } catch (error) {
    ElMessage.error(t('deployPreviewFailed'))
    showPreviewDialog.value = false
  } finally {
    previewLoading.value = false
  }
}

// 加载维护窗口
const loadMaintenanceWindows = async () => {
  try {
    const data = await cachedRequest(
      () => getMaintenanceWindows(),
      'maintenanceWindows',
      {},
      { ttl: 300000 }  // 缓存 5 分钟
    )
    maintenanceWindows.value = data.windows || []
  } catch (error) {
    console.error('Load maintenance windows failed:', error)
  }
}

// 预约部署
const scheduleDeployTask = async () => {
  if (!selectedWindow.value) {
    ElMessage.warning(t('deploySelectWindow'))
    return
  }

  const deployData = {
    mode: deployForm.value.mode,
    engine: deployForm.value.engine,
    napalm_mode: deployForm.value.napalm_mode,
    backup_file: deployForm.value.backup_file,
    template_id: deployForm.value.template_id,
    snippet: deployForm.value.snippet,
    snippet_position: deployForm.value.snippet_position,
    base_backup_file: deployForm.value.base_backup_file,
    target_devices: deployForm.value.target_devices,
    variables: {}
  }

  deployForm.value.variables.forEach(v => {
    if (v.key) deployData.variables[v.key] = v.value
  })

  try {
    const result = await scheduleDeploy({
      window_id: selectedWindow.value,
      deploy_data: deployData
    })

    isScheduled.value = true
    scheduledTime.value = result.scheduled_at
    showScheduleDialog.value = false
    ElMessage.success(t('deployScheduled'))
  } catch (error) {
    ElMessage.error(t('deployScheduleFailed'))
  }
}

// 获取风险等级标签
const getRiskLevelType = (level) => {
  const types = { low: 'success', medium: 'warning', high: 'danger' }
  return types[level] || 'info'
}

const getRiskLevelText = (level) => {
  const texts = {
    low: t('diffRiskLow'),
    medium: t('diffRiskMedium'),
    high: t('diffRiskHigh')
  }
  return texts[level] || level
}

// 维护窗口标签生成
const getWindowLabel = (window) => {
  const dateStr = window.date ? window.date.slice(5) : ''  // 取 MM-DD
  const periodLabels = {
    morning: t('deployWindowMorning'),
    afternoon: t('deployWindowAfternoon'),
    evening: t('deployWindowEvening')
  }
  const periodText = periodLabels[window.period] || window.period
  return `${dateStr} ${periodText} (${window.start_time}-${window.end_time})`
}

// 变量描述生成
const getVariableDescription = (key) => {
  const descriptions = {
    HOSTNAME: t('varDescHostname'),
    ENABLE_SECRET: t('varDescEnableSecret'),
    ADMIN_USERNAME: t('varDescAdminUsername'),
    ADMIN_PASSWORD: t('varDescAdminPassword'),
    DOMAIN_NAME: t('varDescDomainName'),
    MGMT_VLAN_ID: t('varDescMgmtVlanId'),
    MGMT_IP: t('varDescMgmtIp'),
    MGMT_NETMASK: t('varDescMgmtNetmask'),
    DEFAULT_GATEWAY: t('varDescDefaultGateway'),
    SNMP_COMMUNITY: t('varDescSnmpCommunity'),
    LOCATION: t('varDescLocation'),
    CONTACT: t('varDescContact'),
    NTP_SERVER: t('varDescNtpServer'),
    SYSLOG_SERVER: t('varDescSyslogServer'),
    DEFAULT_ROUTE: t('varDescDefaultRoute'),
    OSPF_ROUTER_ID: t('varDescOspfRouterId'),
    ACCESS_PORT_RANGE: t('varDescAccessPortRange'),
    UPLINK_PORT: t('varDescUplinkPort'),
    BUSINESS_VLAN_LIST: t('varDescBusinessVlanList'),
    TRUNK_VLANS: t('varDescTrunkVlans')
  }
  return descriptions[key] || key
}

// 执行部署
const confirmDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  // 计算实际并行数量：串行模式为1，并行模式使用用户设置的值
  const actualParallelLimit = executionMode.value === 'serial' ? 1 : parallelLimit.value

  // 多设备部署确认
  if (deployForm.value.target_devices.length > 1) {
    const modeText = executionMode.value === 'serial'
      ? t('deploySerialModeLabel')
      : t('deployParallelModeLabel') + ` (${actualParallelLimit})`

    try {
      await ElMessageBox.confirm(
        t('deployMultiDeviceConfirm', {
          count: deployForm.value.target_devices.length,
          mode: modeText
        }),
        t('deployConfirmTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )
    } catch {
      return
    }
  } else {
    try {
      await ElMessageBox.confirm(
        t('deployConfirmMessage'),
        t('deployConfirmTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )
    } catch {
      return
    }
  }

  await executeDeploy()
}

// WebSocket 连接
let deployWebSocket = null
let timer = null

const executeDeploy = async () => {
  try {
    // 初始化设备执行列表
    deviceExecutions.value = deployForm.value.target_devices.map(id => {
      const device = devices.value.find(d => d.id === id)
      return {
        device_id: id,
        device_name: device?.name || '',
        device_ip: device?.ip || '',
        status: 'pending',
        progress: 0,
        message: '',
        cliLogs: [],
        rollback_available: false
      }
    })

    // 准备部署数据
    const deployData = {
      action: 'start_deploy',
      mode: deployForm.value.mode,
      engine: deployForm.value.engine,
      napalm_mode: deployForm.value.napalm_mode,
      transfer_mode: deployForm.value.transfer_mode,  // scp | inline
      backup_file: deployForm.value.backup_file,
      template_id: deployForm.value.template_id,
      snippet: deployForm.value.snippet,
      snippet_position: deployForm.value.snippet_position,
      base_backup_file: deployForm.value.base_backup_file,
      target_devices: deployForm.value.target_devices,
      variables: {},
      dry_run: deployForm.value.dry_run,
      parallel_limit: executionMode.value === 'serial' ? 1 : parallelLimit.value
    }

    deployForm.value.variables.forEach(v => {
      if (v.key) deployData.variables[v.key] = v.value
    })

    // 开始执行部署
    executionStatus.value = 'running'
    startTime.value = Date.now()
    timer = setInterval(() => {
      elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
    }, 1000)

    // 使用 WebSocket 执行部署
    const sessionId = `deploy_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.host
    const wsUrl = `${wsProtocol}//${wsHost}/ws/deploy/${sessionId}`

    deployWebSocket = new WebSocket(wsUrl)

    deployWebSocket.onopen = () => {
      console.log('WebSocket 连接已建立:', sessionId)
      // 发送部署请求
      deployWebSocket.send(JSON.stringify(deployData))
    }

    deployWebSocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleDeployMessage(data)
    }

    deployWebSocket.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      stopTimer()
      executionStatus.value = 'failed'
      ElMessage.error('WebSocket 连接失败，请检查网络')
    }

    deployWebSocket.onclose = () => {
      console.log('WebSocket 连接已关闭')
      stopTimer()
    }

  } catch (error) {
    stopTimer()
    executionStatus.value = 'failed'
    redeployParentId.value = null
    ElMessage.error(t('deployFailed'))
  }
}

// 处理 WebSocket 消息
const handleDeployMessage = (data) => {
  console.log('收到 WebSocket 消息:', data.type)

  if (data.type === 'deploy_started') {
    // 部署开始
    ElMessage.info(`开始部署 ${data.total_count} 台设备`)
  }
  else if (data.type === 'device_started') {
    // 设备开始部署
    const device = deviceExecutions.value.find(d => d.device_id === data.device_id)
    if (device) {
      device.status = 'running'
      device.message = '正在部署...'
      device.cliLogs.push({
        timestamp: data.timestamp,
        content: `开始部署设备 ${data.device_name}`,
        type: 'info'
      })
    }
  }
  else if (data.type === 'device_progress') {
    // 设备进度更新
    const device = deviceExecutions.value.find(d => d.device_id === data.device_id)
    if (device) {
      device.status = data.status
      device.message = data.message
      device.progress = 100
      device.rollback_available = data.rollback_available || false

      // 显示 CLI 输出或配置差异
      if (data.cli_output) {
        device.cliLogs.push({
          timestamp: data.timestamp,
          content: data.cli_output,
          type: 'info'
        })
      }
      if (data.diff) {
        device.cliLogs.push({
          timestamp: data.timestamp,
          content: `配置差异:\n${data.diff}`,
          type: 'diff'
        })
      }
      if (data.rollback_available) {
        device.cliLogs.push({
          timestamp: data.timestamp,
          content: '支持回滚，可通过 rollback 操作恢复',
          type: 'info'
        })
      }
      if (!data.success) {
        device.cliLogs.push({
          timestamp: data.timestamp,
          content: `错误: ${data.message}`,
          type: 'error'
        })
      }
      scrollToBottom()
    }

    // 更新整体进度
    const totalDevices = deviceExecutions.value.length
    const completedDevices = deviceExecutions.value.filter(d => d.status === 'completed' || d.status === 'failed').length
    if (totalDevices > 0) {
      const progress = Math.round((completedDevices / totalDevices) * 100)
      // 可以在这里更新整体进度条
    }
  }
  else if (data.type === 'deploy_complete') {
    // 部署完成
    stopTimer()

    const successCount = data.success_count || 0
    const failedCount = data.failed_count || 0

    // 更新执行状态
    executionStatus.value = failedCount === 0 ? 'completed' : (successCount > 0 ? 'completed' : 'failed')

    if (data.history_id) {
      currentHistoryId.value = data.history_id
    }

    // 重新加载历史记录
    loadHistory()

    // 清除重新部署的父记录 ID
    redeployParentId.value = null

    // 关闭 WebSocket
    if (deployWebSocket) {
      deployWebSocket.close()
      deployWebSocket = null
    }

    // 清除设备缓存
    clearCache('devices')

    if (failedCount === 0) {
      ElMessage.success(`部署完成，全部 ${successCount} 台设备成功`)
    } else if (successCount > 0) {
      ElMessage.warning(`部署完成，${successCount} 台成功，${failedCount} 台失败`)
    } else {
      ElMessage.error(`部署失败，全部 ${failedCount} 台设备失败`)
    }
  }
  else if (data.type === 'deploy_error') {
    // 部署错误
    ElMessage.error(data.message)
  }
}

const stopTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const handleRollback = async () => {
  // 只回滚成功部署的设备（有 rollback_available 标记）
  const rollbackDevices = deviceExecutions.value
    .filter(d => d.rollback_available)
    .map(d => d.device_id)

  if (rollbackDevices.length === 0) {
    ElMessage.warning('没有可回滚的设备')
    return
  }

  try {
    await ElMessageBox.confirm(
      t('deployRollbackConfirm'),
      t('deployRollbackTitle'),
      { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
    )

    const rollbackData = {
      target_devices: rollbackDevices,
      parent_id: selectedHistoryId.value || currentHistoryId.value || null
    }

    executionStatus.value = 'running'
    const result = await rollbackDeployApi(rollbackData)

    stopTimer()

    // 处理回滚结果
    deviceExecutions.value.forEach(d => {
      if (!d.rollback_available) {
        d.status = 'skipped'
        d.message = '原部署失败，未执行回滚'
      }
    })

    if (result.results && result.results.length > 0) {
      result.results.forEach(r => {
        const device = deviceExecutions.value.find(d => Number(d.device_id) === Number(r.device_id))
        if (device) {
          device.status = r.success ? 'completed' : 'failed'
          device.message = r.message || (r.success ? '回滚成功' : '回滚失败')
          device.progress = 100
          device.rollback_available = false
          device.cliLogs = []

          if (r.cli_output) {
            device.cliLogs.push({
              timestamp: new Date().toISOString(),
              content: r.cli_output,
              type: 'info'
            })
          }
          if (r.diff) {
            device.cliLogs.push({
              timestamp: new Date().toISOString(),
              content: `配置变更:\n${r.diff}`,
              type: 'diff'
            })
          }
          if (r.errors && r.errors.length > 0) {
            r.errors.forEach(err => {
              device.cliLogs.push({
                timestamp: new Date().toISOString(),
                content: `错误: ${err}`,
                type: 'error'
              })
            })
          }
        }
      })
    }

    executionStatus.value = result.success ? 'completed' : 'failed'
    clearCache('devices')

    // 重新加载历史记录
    await loadHistory()

    if (result.success) {
      ElMessage.success(t('deployRollbackSuccess'))
    } else {
      ElMessage.error(t('deployRollbackFailed'))
    }

  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('deployRollbackFailed'))
    }
  }
}

const confirmAbort = async () => {
  try {
    await ElMessageBox.confirm(
      t('deployAbortConfirm'),
      t('deployAbortTitle'),
      { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
    )
    await abortExecution()
  } catch {
    // Cancelled
  }
}

const abortExecution = async () => {
  aborting.value = true
  try {
    // 关闭 WebSocket 连接
    if (deployWebSocket) {
      deployWebSocket.close()
      deployWebSocket = null
    }
    executionStatus.value = 'aborted'
    stopTimer()
    ElMessage.warning(t('deployAborted'))
  } catch (error) {
    ElMessage.error(t('deployAbortFailed'))
  } finally {
    aborting.value = false
  }
}

// 审批处理函数
const handleApprovalSubmit = async () => {
  if (!approvalComment.value.trim()) {
    ElMessage.warning(t('deployApprovalCommentRequired'))
    return
  }

  try {
    const response = await fetch(`/api/deploy-approval/${approvalId.value}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: approvalComment.value })
    })

    if (response.ok) {
      approvalStatus.value = 'approved'
      ElMessage.success(t('deployApproved'))
      // 刷新并开始执行
      await startApprovedDeployment()
    } else {
      ElMessage.error(t('deployApproveFailed'))
    }
  } catch (error) {
    ElMessage.error(t('deployApproveFailed'))
  }
}

const handleRejectionSubmit = async () => {
  if (!rejectionReason.value.trim()) {
    ElMessage.warning(t('deployRejectionReasonRequired'))
    return
  }

  try {
    const response = await fetch(`/api/deploy-approval/${approvalId.value}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: rejectionReason.value })
    })

    if (response.ok) {
      approvalStatus.value = 'rejected'
      ElMessage.warning(t('deployRejected'))
    } else {
      ElMessage.error(t('deployRejectFailed'))
    }
  } catch (error) {
    ElMessage.error(t('deployRejectFailed'))
  }
}

const startApprovedDeployment = async () => {
  // 审批通过后开始执行
  executionStatus.value = 'running'
  startTime.value = Date.now()
  timer = setInterval(() => {
    elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
  }, 1000)

  // 重新调用部署API
  // 注意：实际实现需要一个新的API端点或在原API中处理
  // 这里简化处理，直接显示执行状态
}

// 打开预约对话框
const openScheduleDialog = () => {
  showPreviewDialog.value = false
  showScheduleDialog.value = true
}

// 从预览确认部署
const confirmDeployFromPreview = async () => {
  showPreviewDialog.value = false
  await confirmDeploy()
}

// 监听部署模式变化，模板和备份模式只支持 Netmiko
watch(() => deployForm.value.mode, (newMode) => {
  if ((newMode === 'template' || newMode === 'backup') && deployForm.value.engine === 'napalm') {
    deployForm.value.engine = 'netmiko'
  }
})

onMounted(async () => {
  // 加载部署历史
  await loadHistory()

  // 依次加载，避免同时触发太多请求
  await loadDevices()
  await new Promise(r => setTimeout(r, 100))
  await loadBackups()
  await new Promise(r => setTimeout(r, 100))
  await loadTemplates()
  await new Promise(r => setTimeout(r, 100))
  loadCompatibleVariables()  // 这个请求失败不影响，可以并行
  loadMaintenanceWindows()   // 这个也不影响，可以并行
})
</script>

<style scoped>
/* ========================================
   使用全局 Theme Token（来自 tokens.css）
   不要重新定义变量，直接使用全局变量
   ======================================== */

.deploy-page {
  padding: 0;
  background: var(--bg-primary);
}

/* ========================================
   页面导航栏
   ======================================== */

.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--gap-md);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-tag {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 6px !important;
  white-space: nowrap !important;
}

/* 穿透 Element Plus el-tag 内部结构 */
.status-tag :deep(.el-tag__content) {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 6px !important;
}

/* 直接作用于 el-tag 的所有子元素 */
.status-tag.el-tag {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
}

.status-tag.el-tag--large {
  height: 32px;
  padding: 0 12px;
}

.status-tag :deep(.el-icon) {
  display: inline-flex !important;
  align-items: center !important;
  width: 14px !important;
  height: 14px !important;
  flex-shrink: 0 !important;
  margin-right: 0 !important;
  margin-bottom: 0 !important;
  vertical-align: middle !important;
}

.status-tag.el-tag--large :deep(.el-icon) {
  width: 16px !important;
  height: 16px !important;
}

.status-tag :deep(.is-loading) {
  display: inline-flex !important;
  align-items: center !important;
}

/* 确保 el-tag 内的文字也是 inline */
.status-tag,
.status-tag :deep(*) {
  vertical-align: middle !important;
}

.status-content {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.status-content .el-icon {
  display: inline-flex;
  align-items: center;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.nav-right {
  display: flex;
  gap: 10px;
}

/* ========================================
   按钮系统 - 现代、轻量、主次分明
   ======================================== */

.nav-action-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: none;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.nav-action-btn .el-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

/* 小按钮 */
.nav-action-btn.small {
  height: 22px;
  padding: 0 8px;
  font-size: 11px;
}

/* 主按钮 - deploy */
.nav-action-btn.deploy-btn {
  background: var(--accent-primary);
  color: white;
  border: none;
}

.nav-action-btn.deploy-btn:hover:not(.disabled) {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

.nav-action-btn.deploy-btn.disabled {
  background: rgba(0, 184, 148, 0.4);
  cursor: not-allowed;
}

/* 次按钮 */
.nav-action-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

/* 危险按钮 */
.nav-action-btn.danger {
  background: var(--accent-danger);
  color: white;
  border: none;
}

.nav-action-btn.danger:hover {
  background: #c42a2a;
  box-shadow: 0 2px 6px rgba(214, 48, 49, 0.2);
  transform: translateY(-1px);
}

/* 预览按钮 */
.nav-action-btn.preview-btn {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.preview-btn:hover:not(.disabled) {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
}

.nav-action-btn.preview-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ========================================
   警告区域
   ======================================== */

.warning-section {
  margin-bottom: var(--gap-lg);
}

.warning-card {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  padding: var(--gap-md) var(--gap-lg);
  background: var(--warn-bg);
  border: 1px solid rgba(225, 112, 85, 0.3);
  border-radius: var(--radius-lg);
}

.warning-icon {
  font-size: 24px;
  color: var(--accent-warning);
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-weight: 600;
  color: var(--accent-warning);
  margin-bottom: var(--gap-xs);
}

.warning-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ========================================
   主内容区域
   ======================================== */

.main-content-area {
  height: calc(100vh - 200px);
}

.full-height {
  height: 100%;
}

.config-column,
.execution-column {
  height: 100%;
}

/* ========================================
   配置面板 - 更紧凑
   ======================================== */

.config-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
  height: 100%;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.config-panel::-webkit-scrollbar {
  width: var(--gap-xs);
}

.config-panel::-webkit-scrollbar-track {
  background: transparent;
}

.config-panel::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 3px;
}

.config-panel::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}

.panel-header {
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ========================================
   表单区域 - 现代 DevOps 风格
   ======================================== */

.form-section {
  margin-bottom: 16px;
}

.section-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.section-label.required::after {
  content: '';
  /* 不显示红色星号，更现代的方式 */
}

.section-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
  line-height: 1.4;
}

/* ========================================
   Input 输入框 - 更现代更细
   ======================================== */

.config-form :deep(.el-input__wrapper) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: none;
  padding: 0 12px;
  height: 32px;
  transition: all 0.15s ease;
}

.config-form :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
  background: var(--bg-card);
}

.config-form :deep(.el-input__inner) {
  font-size: 14px;
  color: var(--text-primary);
  height: 32px;
}

/* Placeholder 提高可见度 */
.config-form :deep(.el-input__inner::placeholder) {
  color: var(--text-tertiary);
  font-size: 13px;
  opacity: 1;
}

/* Textarea */
.config-form :deep(.el-textarea__inner) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-primary);
  padding: 12px;
  transition: all 0.15s ease;
  box-shadow: none;
}

.config-form :deep(.el-textarea__inner:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-textarea__inner:focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

/* Snippet input 特殊样式 */
.snippet-input :deep(.el-textarea__inner) {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
}

/* ========================================
   Select 选择器 - 更轻更科技
   ======================================== */

.config-form :deep(.el-select) {
  width: 100%;
}

.config-form :deep(.el-select .el-input__wrapper) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  height: 32px;
  padding: 0 32px 0 12px;
  box-shadow: none;
  transition: all 0.15s ease;
}

.config-form :deep(.el-select .el-input__wrapper:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-select .el-input__wrapper.is-focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

/* ========================================
   Radio Group - 扁平现代（完整样式）
   ======================================== */

.mode-radio-group {
  display: flex;
  width: 100%;
  gap: 2px;
  flex-wrap: nowrap;
}

.mode-radio-group :deep(.el-radio-button) {
  flex: 1;
  min-width: 0;
}

.mode-radio-group :deep(.el-radio-button__inner) {
  width: 100%;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s ease;
  box-shadow: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 激活状态 */
.mode-radio-group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: rgba(9, 132, 227, 0.1);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
  box-shadow: 0 0 0 1px var(--accent-secondary);
}

/* Hover */
.mode-radio-group :deep(.el-radio-button__inner:hover) {
  border-color: var(--accent-secondary);
}

.execution-mode-section {
  margin-top: var(--gap-md);
  padding: var(--gap-md);
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.mode-options {
  display: flex;
  align-items: center;
}

.mode-options :deep(.el-radio-group) {
  display: inline-flex;
}

.mode-option-content {
  display: inline-flex;
  align-items: center;
  gap: var(--gap-xs);
}

.mode-option-content .el-icon {
  width: 14px;
  height: 14px;
}

.parallel-limit-input {
  display: inline-flex;
  align-items: center;
  gap: var(--gap-sm);
  margin-top: var(--gap-md);
  padding-left: var(--gap-md);
}

.limit-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.limit-tip {
  font-size: 12px;
  color: var(--text-muted);
}

.execution-mode-hint {
  margin-top: 8px;
}

.execution-mode-hint .el-tag,
.execution-mode-hint .status-tag {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 6px !important;
}

.execution-mode-hint .el-tag :deep(.el-tag__content) {
  display: inline-flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 6px !important;
}

.execution-mode-hint .el-tag :deep(.el-icon) {
  display: inline-flex !important;
  align-items: center !important;
  width: 14px !important;
  height: 14px !important;
  flex-shrink: 0 !important;
  margin-right: 0 !important;
  margin-bottom: 0 !important;
  vertical-align: middle !important;
}

/* ========================================
   引擎选择
   ======================================== */

.engine-tag {
  margin-left: var(--gap-xs);
  font-size: 11px;
}

/* Engine 提示 - 固定在 radio-group 下面 */
.engine-tip {
  margin-top: var(--gap-sm);
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  padding: var(--gap-xs) 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  width: 100%;
}

.engine-tip.safe {
  background: var(--success-bg);
  color: var(--accent-primary);
}

.engine-tip.warning {
  background: var(--warning-bg);
  color: var(--accent-warning);
}

/* NAPALM 模式提示 - 固定在 radio-group 下面 */
.napalm-mode-tip {
  margin-top: var(--gap-xs);
  font-size: 12px;
  color: var(--text-secondary);
  padding: var(--gap-xs) 10px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  width: 100%;
}

/* Smart 模式提示 - 固定在 radio-group 下面 */
.smart-mode-tip {
  margin-top: var(--gap-sm);
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--gap-xs);
  padding: var(--gap-xs) 10px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  width: 100%;
}

.smart-mode-tip .tip-icon,
.smart-mode-tip .tip-text {
  color: var(--text-secondary);
  font-size: 12px;
}

/* ========================================
   Checkbox - 更现代
   ======================================== */

.config-form :deep(.el-checkbox) {
  height: auto;
  display: flex;
  align-items: center;
}

.config-form :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: var(--accent-secondary);
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-checkbox__inner) {
  transition: all 0.15s ease;
}

.config-form :deep(.el-checkbox__label) {
  font-size: 13px;
  color: var(--text-primary);
}

/* 暗色模式 checkbox */
.dark .config-form :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

.dark .config-form :deep(.el-checkbox__label) {
  color: var(--text-secondary);
}

/* ========================================
   Engine radio 特殊样式
   ======================================== */

.config-form .el-radio-group :deep(.el-radio-button__inner) {
  padding: 6px 10px;
  font-size: 11px;
}

/* Engine tag 更小 */
.engine-tag {
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 3px;
}

/* ========================================
   选项样式
   ======================================== */

.backup-option,
.template-option,
.device-option {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.backup-name,
.template-name,
.device-name {
  font-weight: 500;
}

.backup-file,
.template-desc,
.device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

.backup-time {
  font-size: 11px;
  color: var(--text-secondary);
}

/* ========================================
   变量区域
   ======================================== */

.variables-list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.variable-item {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.add-var-btn {
  margin-top: var(--gap-xs);
}

/* ========================================
   操作按钮
   ======================================== */

.actions-section {
  display: flex;
  gap: var(--gap-md);
  padding-top: var(--gap-md);
  border-top: 1px solid var(--border-subtle);
}

.preview-btn,
.deploy-btn {
  flex: 1;
  justify-content: center;
}

/* ========================================
   执行面板 - 浅色企业风格
   ======================================== */

.execution-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--gap-lg);
  height: 100%;
  overflow-y: auto;
  box-shadow: var(--shadow-card);
}

.execution-panel.active {
  border-color: var(--accent-secondary);
}

/* 执行面板分隔线 - 浅色风格 */
.execution-panel :deep(.el-divider) {
  border-color: var(--border-subtle);
}

/* ========================================
   执行概览 - 浅色风格 Pipeline Summary
   ======================================== */

.execution-overview {
  margin-bottom: var(--gap-md);
  padding: 16px;
  background: transparent;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--gap-sm);
}

.overview-title {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.overview-title .is-loading {
  display: inline-flex;
  align-items: center;
}

.elapsed-time {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
}

.overview-actions {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
}

/* ========================================
   进度统计 - 浅色卡片风格
   ======================================== */

.progress-overview {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  padding: 12px 0;
}

.progress-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  background: var(--bg-hover);
  font-size: 13px;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

.progress-item.success {
  background: var(--success-bg);
  border-color: rgba(0, 184, 148, 0.3);
}

.progress-item.warning {
  background: var(--warn-bg);
  border-color: rgba(210, 153, 34, 0.3);
}

.progress-item.error {
  background: var(--error-bg);
  border-color: rgba(214, 48, 49, 0.3);
}

.progress-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.progress-value {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.progress-item.success .progress-value {
  color: var(--accent-primary);
}

.progress-item.warning .progress-value {
  color: var(--accent-warning);
}

.progress-item.error .progress-value {
  color: var(--accent-danger);
}

.overall-progress {
  margin-top: var(--gap-sm);
}

/* 进度条 - 浅色背景 */
.overall-progress :deep(.el-progress-bar__outer) {
  height: 4px !important;
  border-radius: 2px;
  background: var(--bg-hover) !important;
}

.overall-progress :deep(.el-progress-bar__inner) {
  border-radius: 2px;
  transition: width 0.3s ease;
  background: var(--accent-primary) !important;
}

/* Progress shimmer 动画 */
@keyframes progress-shimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}

.execution-panel.active .overall-progress :deep(.el-progress-bar__inner) {
  background: linear-gradient(
    90deg,
    var(--accent-primary) 0%,
    #2ecc71 25%,
    var(--accent-primary) 50%,
    #2ecc71 75%,
    var(--accent-primary) 100%
  ) !important;
  background-size: 200% 100%;
  animation: progress-shimmer 2s linear infinite;
}

/* ========================================
   设备区域 - 浅色企业风格
   ======================================== */

.devices-section {
  margin-bottom: var(--gap-lg);
  background: transparent;
}

.section-header {
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.device-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--gap-md);
}

/* 设备卡片 - 浅色卡片风格 */
.device-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.device-card:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  transform: translateY(-1px);
}

.device-card.active {
  border-color: var(--accent-primary);
  background: var(--bg-hover);
}

/* 状态边框 */
.device-card.success {
  border-color: rgba(0, 184, 148, 0.3);
}

.device-card.error {
  border-color: rgba(214, 48, 49, 0.3);
}

.device-card.skipped {
  border-color: rgba(139, 148, 158, 0.3);
}

.device-card.running {
  border-color: var(--accent-secondary);
}

.device-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--gap-sm);
}

.device-info {
  display: flex;
  align-items: flex-start;
  gap: var(--gap-sm);
}

.status-icon {
  font-size: 16px;
  margin-top: 2px;
}

.status-icon.success { color: var(--accent-primary); }
.status-icon.error { color: var(--accent-danger); }
.status-icon.running { color: var(--accent-secondary); }
.status-icon.pending { color: var(--text-muted); }
.status-icon.skipped { color: var(--text-secondary); }

.device-text {
  display: flex;
  flex-direction: column;
}

.device-name {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 13px;
}

.device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

.device-progress {
  margin-top: var(--gap-sm);
}

/* 设备进度条 - 浅色风格 */
.device-progress :deep(.el-progress-bar__outer) {
  height: 3px !important;
  background: var(--bg-hover) !important;
}

.device-progress :deep(.el-progress-bar__inner) {
  background: var(--accent-secondary) !important;
}

.device-message {
  margin-top: var(--gap-sm);
  font-size: 12px;
  color: var(--text-secondary);
}

/* ========================================
   CLI 并排布局 - 企业级 SSH Console
   ======================================== */

.cli-section-parallel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--gap-lg);
  margin-top: var(--gap-lg);
}

/* CLI Panel - 保持深色 Terminal 风格 */
.cli-panel {
  background: #1e1e1e;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 340px;
}

.cli-panel.active {
  border-color: var(--accent-secondary);
}

.cli-panel.realtime {
  border-color: var(--accent-secondary);
}

/* CLI Header - VSCode Terminal 风格 */
.cli-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
  height: 36px;
  flex-shrink: 0;
  font-size: 12px;
  color: #cccccc;
}

.cli-panel.realtime .cli-panel-header {
  background: rgba(9, 132, 227, 0.1);
  border-bottom-color: rgba(9, 132, 227, 0.3);
}

.cli-panel-title {
  font-size: 12px;
  font-weight: 500;
  color: #cccccc;
}

.cli-panel-header .el-tag {
  display: inline-flex !important;
  align-items: center;
  gap: var(--gap-xs);
  height: 22px;
  padding: 0 8px;
}

.cli-panel-header .el-tag :deep(.el-icon) {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

.cli-panel-header .el-tag .is-loading {
  display: inline-flex;
  align-items: center;
}

/* Device Badge - VSCode Terminal 风格 */
.device-badge {
  margin-left: var(--gap-sm);
  padding: 2px 6px;
  background: rgba(9, 132, 227, 0.15);
  border-radius: 4px;
  font-size: 11px;
  color: #569cd6;
}

/* ========================================
   CLI 输出区域 - VSCode Terminal 风格（始终深色）
   ======================================== */

.cli-panel-output {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'JetBrains Mono', 'Geist Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 16px;
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
  position: relative;
}

.cli-panel-output::-webkit-scrollbar {
  width: 4px;
}

.cli-panel-output::-webkit-scrollbar-track {
  background: transparent;
}

.cli-panel-output::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.cli-panel-output::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* CLI 滚动指示 */
.cli-panel-output.autoscroll::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(transparent, rgba(30, 30, 30, 0.8));
  pointer-events: none;
}

.cli-empty {
  color: #858585;
  text-align: center;
  padding: var(--gap-lg);
}

.cli-line {
  display: flex;
  gap: 8px;
  padding: 1px 0;
}

.cli-timestamp {
  color: #6a9955;
  font-size: 10px;
  opacity: 0.8;
  flex-shrink: 0;
}

.cli-command {
  color: #4ec9b0;
  font-weight: 500;
}

.cli-content {
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

/* ANSI 风格高亮 - VSCode Terminal */
.cli-line.command .cli-content {
  color: #4ec9b0;
  font-weight: 500;
}

.cli-line.error .cli-content,
.cli-error-text {
  color: #f14c4c;
}

.cli-line.warning .cli-content {
  color: #cca700;
}

.cli-line.success .cli-content {
  color: #89d185;
}

.cli-line.diff .cli-content {
  color: #ce9178;
}

.cli-line.info .cli-content {
  color: #569cd6;
}

.cli-step {
  color: #569cd6;
  display: inline-flex;
  align-items: center;
  gap: var(--gap-xs);
}

.cli-diff-inline {
  color: #ce9178;
  white-space: pre-wrap;
  font-size: 11px;
  margin: var(--gap-xs) 0;
  padding: var(--gap-xs) 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-sm);
  max-width: 100%;
  overflow-x: auto;
}

/* 光标闪烁动画 */
@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.cli-cursor {
  display: inline-block;
  width: 8px;
  height: 14px;
  background: #4ec9b0;
  animation: cursor-blink 1s step-end infinite;
}

/* ========================================
   历史记录面板 - 浅色企业风格
   ======================================== */

/* ========================================
   历史面板 - 浅色企业风格
   ======================================== */

.history-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
}

.history-panel .cli-panel-header {
  background: var(--bg-hover);
  border-bottom: 1px solid var(--border-subtle);
}

.history-panel .cli-panel-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}

.history-list {
  background: var(--bg-card);
  padding: var(--gap-sm);
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border-default) transparent;
}

.history-list::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

.history-list::-webkit-scrollbar-track {
  background: transparent;
}

.history-list::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 2px;
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.history-item {
  padding: var(--gap-sm) var(--gap-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
  margin-bottom: var(--gap-xs);
  background: var(--bg-hover);
  border: 1px solid transparent;
  position: relative;
}

.history-item:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
}

.history-item.active {
  background: rgba(9, 132, 227, 0.08);
  border-color: var(--accent-secondary);
}

.history-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--gap-xs);
}

.history-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.history-operator {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: var(--gap-sm);
  padding: var(--gap-xs) var(--gap-xs);
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
}

.history-devices {
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: var(--gap-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-status {
  margin-bottom: var(--gap-xs);
}

.status-summary {
  display: flex;
  gap: var(--gap-sm);
  font-size: 12px;
}

.status-success {
  color: var(--status-active);
}

.status-failed {
  color: var(--status-error);
}

.history-engine {
  display: flex;
  gap: var(--gap-sm);
}

.engine-tag, .mode-tag {
  font-size: 11px;
  padding: var(--gap-xs);
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.mode-tag.rollback {
  background: var(--warn-bg);
  color: var(--accent-warning);
}

.history-actions {
  display: flex;
  gap: var(--gap-sm);
  margin-top: var(--gap-md);
  padding-top: var(--gap-md);
  border-top: 1px dashed var(--border-default);
}

.history-actions .el-button {
  flex: 1;
}

/* 任务链连接线 */
.history-item.is-child {
  margin-left: var(--gap-md);
  border-left: 3px solid var(--accent-secondary);
  background: var(--bg-hover);
}

.history-item.is-rollback {
  border-left-color: var(--accent-warning);
}

/* ========================================
   动画
   ======================================== */

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ========================================
   对话框样式
   ======================================== */

.preview-content {
  max-height: 70vh;
  overflow-y: auto;
}

.impact-summary {
  background: var(--bg-hover);
  border-radius: var(--radius-lg);
  padding: var(--gap-lg);
  margin-bottom: var(--gap-lg);
  border: 1px solid var(--border-default);
}

.impact-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--gap-lg);
}

.impact-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--gap-lg);
}

.impact-item {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.impact-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.impact-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.device-selector {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
  padding: var(--gap-lg);
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.selector-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.device-diff {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.diff-device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--gap-md);
  background: var(--bg-hover);
  border-bottom: 1px solid var(--border-default);
}

.diff-device-header .device-info h4 {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
}

.diff-device-header .device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ========================================
   预约对话框
   ======================================== */

.schedule-content {
  padding: var(--gap-md) 0;
}

.schedule-desc {
  margin-bottom: var(--gap-lg);
  color: var(--text-secondary);
  font-size: 14px;
}

.window-options {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  width: 100%;
}

.window-option {
  width: 100%;
}

.window-option :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: var(--gap-md);
}

.window-label {
  font-weight: 500;
  font-size: 14px;
  color: var(--text-primary);
}

.window-time {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: var(--gap-xs);
}

.schedule-confirmation {
  margin-top: var(--gap-lg);
}

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}

/* ========================================
   部署历史卡片 - 浅色企业风格
   ======================================== */

.deploy-card {
  position: relative;
  display: flex;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  transition: all 0.15s ease;
  overflow: hidden;
  min-height: 90px;
  max-height: 110px;
  cursor: pointer;
  box-shadow: var(--shadow-card);
}

.deploy-card:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-elevated);
}

.deploy-card.selected {
  border-color: var(--accent-secondary);
  background: rgba(9, 132, 227, 0.05);
}

.card-status-bar {
  width: 3px;
  min-height: 100%;
  flex-shrink: 0;
}

.card-status-bar.success {
  background: var(--accent-primary);
}

.card-status-bar.failed {
  background: var(--accent-danger);
}

.card-body {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.success {
  background: var(--accent-primary);
}

.status-dot.failed {
  background: var(--accent-danger);
}

.card-time {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'Geist Mono', monospace;
}

/* badges 更轻 */
.header-badges {
  display: flex;
  gap: 6px;
  margin-left: auto;
}

.mini-badge {
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 500;
  border-radius: 4px;
}

.mini-badge.success {
  background: rgba(0, 184, 148, 0.1);
  color: var(--accent-primary);
}

.mini-badge.failed {
  background: rgba(214, 48, 49, 0.1);
  color: var(--accent-danger);
}

.status-label {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.status-label.rollback {
  background: rgba(225, 112, 85, 0.1);
  color: var(--accent-warning);
}

.status-label.can-rollback {
  background: rgba(0, 184, 148, 0.1);
  color: var(--accent-primary);
}

/* 第二行 metadata */
.card-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--text-secondary);
}

.meta-item .el-icon {
  width: 12px;
  height: 12px;
}

.meta-item.children-count {
  cursor: pointer;
  color: var(--accent-secondary);
  padding: 2px 4px;
  border-radius: 4px;
  background: transparent;
  transition: all 0.15s ease;
}

.meta-item.children-count:hover {
  background: rgba(9, 132, 227, 0.1);
}

.meta-divider {
  color: var(--text-tertiary);
  opacity: 1;
}

/* 第三行 footer */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.result-summary {
  display: flex;
  gap: 8px;
}

.summary-badge {
  font-size: 11px;
  font-weight: 500;
}

.summary-badge.success {
  color: var(--accent-primary);
}

.summary-badge.failed {
  color: var(--accent-danger);
}

/* 操作按钮 */
.card-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.deploy-card:hover .card-actions,
.deploy-card.selected .card-actions {
  opacity: 1;
}

.card-actions .el-button {
  height: 22px;
  padding: 0 8px;
  font-size: 10px;
  border-radius: 4px;
}

/* 子记录 */
.children-list {
  margin-left: 12px;
  margin-top: 4px;
  padding: 6px 8px;
  background: var(--bg-hover);
  border-radius: 6px;
  border: 1px solid var(--border-subtle);
}

.history-item.child-record {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  margin-bottom: 4px;
  gap: 8px;
  font-size: 11px;
  background: var(--bg-card);
  border-radius: 4px;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.history-item.child-record:last-child {
  margin-bottom: 0;
}

.history-item.child-record:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
}

.history-item.child-record.active {
  border-color: var(--accent-secondary);
}

.chain-line {
  width: 2px;
  height: 24px;
  background: var(--border-default);
  flex-shrink: 0;
}

.operation-icon {
  color: var(--text-tertiary);
}

.operation-icon .rollback {
  color: var(--accent-warning);
}

.operation-icon .redeploy {
  color: var(--accent-secondary);
}

.child-actions {
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.history-item.child-record:hover .child-actions,
.history-item.child-record.active .child-actions {
  opacity: 1;
}

.group-actions {
  display: flex;
  gap: 4px;
  margin-top: 6px;
  margin-left: 12px;
}

.group-actions .el-button {
  height: 22px;
  padding: 0 8px;
  font-size: 10px;
}

/* Empty state */
.cli-empty {
  color: #858585;
  font-size: 12px;
  padding: 20px;
  text-align: center;
}

/* ========================================
   全页面微交互增强
   ======================================== */

/* 1. Fade slide in animation */
@keyframes fade-slide-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.deploy-card,
.device-card {
  animation: fade-slide-in 0.2s ease;
}

/* 2. Terminal cursor blink */
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.cli-panel-output.running::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 30px;
  background: linear-gradient(transparent, rgba(30, 30, 30, 0.8));
  pointer-events: none;
  z-index: 1;
}

/* 3. Focus effect on inputs */
.config-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.12);
}

.dark .config-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.12);
}

/* 4. Smooth hover transitions for inputs */
.config-form :deep(.el-input__wrapper),
.config-form :deep(.el-select .el-input__wrapper),
.config-form :deep(.el-textarea__inner) {
  transition: all 0.15s ease;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 300px;
  opacity: 1;
}

/* ========================================
   暗色模式兼容
   ======================================== */

.dark .config-panel {
  background: var(--bg-card);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-input__wrapper.is-focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

.dark .config-form :deep(.el-textarea__inner) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-textarea__inner:focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

.dark .config-form :deep(.el-select .el-input__wrapper) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-select .el-input__wrapper.is-focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

.dark .mode-radio-group :deep(.el-radio-button__inner) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .mode-radio-group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: rgba(0, 184, 148, 0.1);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

/* 暗色模式 badge 清晰化 */
.dark .mini-badge {
  color: var(--text-secondary);
}

.dark .card-meta {
  color: var(--text-secondary);
}
</style>

<!-- 全局样式：Select 下拉框文字清晰化（下拉菜单挂载在 body 上，需要非 scoped） -->
<style>
/* Select 选项文字 */
.el-select-dropdown__item {
  color: var(--text-primary);
  font-size: 13px;
}

/* 选项 hover */
.el-select-dropdown__item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* 已选中 */
.el-select-dropdown__item.selected {
  color: var(--accent-secondary);
}

/* 暗色模式 Select 下拉框 */
.dark .el-select-dropdown__item {
  color: var(--text-primary);
}

.dark .el-select-dropdown__item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.dark .el-select-dropdown__item.selected {
  color: var(--accent-primary);
}
</style>
<template>
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
          @click="emit('select-record', group.parent)"
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
              <span class="meta-item children-count" v-if="group.children.length > 0" @click.stop="emit('toggle-group', group.parentId)">
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
                  @click.stop="emit('rollback-record', group.parent)"
                >
                  {{ t('deployRollback') }}
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  size="small"
                  plain
                  round
                  @click.stop="emit('redeploy-record', group.parent)"
                >
                  {{ t('deployRedeploy') }}
                </el-button>
                <el-button
                  type="info"
                  size="small"
                  plain
                  round
                  @click.stop="emit('delete-record', group.parent)"
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
              @click="emit('select-record', child)"
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
                <el-button type="danger" size="small" link @click.stop="emit('delete-record', child)">
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
            @click.stop="emit('rollback-record', group.parent)"
          >
            <el-icon><RefreshLeft /></el-icon>
            {{ t('deployRollback') }}
          </el-button>
          <el-button
            v-else
            type="primary"
            size="small"
            @click.stop="emit('redeploy-record', group.parent)"
          >
            <el-icon><Refresh /></el-icon>
            {{ t('deployRedeploy') }}
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click.stop="emit('delete-record', group.parent)"
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
</template>

<script setup>
import {
  Delete,
  User,
  Monitor,
  ArrowRight,
  ArrowDown,
  RefreshLeft,
  Refresh
} from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { formatDateTime } from '@/utils/time'
import { hasBeenRolledBack, canRollback } from '@/utils/deploy.js'

defineProps({
  groupedHistory: { type: Array, default: () => [] },
  selectedHistoryId: { type: [String, Number], default: null },
  historyLoading: { type: Boolean, default: false },
  isGroupExpanded: { type: Function, default: () => true }
})

const emit = defineEmits([
  'select-record',
  'toggle-group',
  'rollback-record',
  'redeploy-record',
  'delete-record'
])

const { t } = useI18n()
</script>

<style scoped>
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

.cli-panel-title {
  font-size: 12px;
  font-weight: 500;
  color: #cccccc;
}

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

.deploy-card {
  animation: fade-slide-in 0.2s ease;
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

/* 暗色模式 badge 清晰化 */
.dark .mini-badge {
  color: var(--text-secondary);
}

.dark .card-meta {
  color: var(--text-secondary);
}
</style>

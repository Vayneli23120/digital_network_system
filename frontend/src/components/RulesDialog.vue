<template>
  <el-dialog
    v-model="visible"
    :title="t('complianceRulesTitle')"
    width="800px"
    append-to-body
    draggable
    align-center
    class="compliance-dialog"
  >
    <div class="rules-panel" v-loading="loading">
      <el-empty v-if="rules.length === 0 && !loading" :description="t('complianceNoRules')" />

      <el-table v-else :data="rules" style="width: 100%" size="small">
        <el-table-column prop="rule_id" :label="t('complianceRuleId')" width="100">
          <template #default="{ row }">
            <span class="rule-id-link" @click="emit('view-rule', row)">{{ row.rule_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" :label="t('complianceRuleName')" min-width="150">
          <template #default="{ row }">
            <span class="rule-name-link" @click="emit('view-rule', row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="category" :label="t('complianceCategory')" width="100">
          <template #default="{ row }">
            <el-tag :type="categoryType(row.category)" size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" :label="t('complianceSeverity')" width="80">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_type" :label="t('complianceRuleSource')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.source_type === 'auto' ? 'success' : 'info'" size="small">
              {{ row.source_type === 'auto' ? t('complianceRuleSourceAuto') : t('complianceRuleSourceManual') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('colActions')" width="120" align="center">
          <template #default="{ row }">
            <button class="table-action-btn primary" @click="emit('view-rule', row)">
              <el-icon><View /></el-icon>
              {{ t('complianceStandardViewBtn') }}
            </button>
            <el-switch
              v-model="row.is_active"
              size="small"
              @change="emit('toggle-status', row.id, row.is_active)"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { View } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { categoryType, severityType } from '@/utils/compliance.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  rules: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'view-rule', 'toggle-status'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})
</script>

<style scoped>
.table-action-btn {
  height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
}

.table-action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.table-action-btn.danger:hover {
  color: var(--accent-danger);
}

/* 规则表格中的链接样式 */
.rule-id-link,
.rule-name-link {
  color: var(--accent-secondary);
  cursor: pointer;
  transition: color 0.15s ease;
}

.rule-id-link:hover,
.rule-name-link:hover {
  color: var(--accent-primary);
}
</style>

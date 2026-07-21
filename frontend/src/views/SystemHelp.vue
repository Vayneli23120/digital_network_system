<template>
  <div class="system-help-page">
    <el-card class="hero-card" shadow="never">
      <div class="hero-header">
        <div>
          <h1>{{ t('systemHelpTitle') || '系统架构中心' }}</h1>
          <p>{{ t('systemHelpSubtitle') || '统一展示系统拓扑、模块关系与数据流，便于运维交接和故障分析。' }}</p>
          <div class="meta-row">
            <span>{{ t('systemHelpVersionLabel') || '架构版本' }}: {{ selectedVersionMeta.label }}</span>
            <span>{{ t('systemHelpUpdatedAtLabel') || '最近更新' }}: {{ selectedVersionMeta.updatedAt }}</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button @click="refreshDiagram">{{ t('commonRefresh') || '刷新' }}</el-button>
          <el-button @click="printAsPdf">{{ t('systemHelpPrintPdf') || '打印/PDF' }}</el-button>
          <el-button type="primary" @click="openStandalone">{{ t('systemHelpOpenNewTab') || '新窗口打开' }}</el-button>
        </div>
      </div>

      <div class="highlights">
        <div class="highlight-item">{{ t('systemHelpPointFlexible') || '灵活配置: 仅需 Base URL + API Key，可接入任意兼容端点。' }}</div>
        <div class="highlight-item">{{ t('systemHelpPointPlugin') || '即插即用: 支持 OpenAI / Anthropic / Ollama / 本地 OpenAI 兼容服务。' }}</div>
        <div class="highlight-item">{{ t('systemHelpPointAsync') || '异步研判: 规则卡片秒级返回，AI 总结后台生成并自动更新。' }}</div>
      </div>
    </el-card>

    <div class="workspace-grid">
      <el-card class="catalog-card" shadow="never">
        <template #header>
          <span>{{ t('systemHelpCatalogTitle') || '架构目录' }}</span>
        </template>
        <el-select v-model="selectedVersion" class="version-select" @change="onVersionChange">
          <el-option v-for="version in versionOptions" :key="version.value" :label="version.label" :value="version.value" />
        </el-select>
        <div class="catalog-list">
          <button
            v-for="section in sections"
            :key="section.id"
            class="catalog-item"
            :class="{ active: section.id === selectedSection }"
            @click="jumpToSection(section.id)"
          >
            {{ section.label }}
          </button>
        </div>
      </el-card>

      <el-card class="diagram-card">
        <template #header>
          <div class="diagram-header">
            <span>{{ t('systemHelpDiagramTitle') || '系统全景架构图' }}</span>
            <span class="diagram-tip">{{ t('systemHelpDiagramTip') || '支持缩放与滚动查看' }}</span>
          </div>
        </template>

        <div class="diagram-wrap">
          <iframe
            :key="iframeKey"
            class="diagram-frame"
            :src="diagramUrl"
            title="System Architecture Diagram"
          />
        </div>
      </el-card>
    </div>

    <el-card class="release-card" shadow="never">
      <template #header>
        <span>{{ t('systemHelpReleaseTitle') || '受控发布说明' }}</span>
      </template>
      <div class="release-grid">
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseOwner') || '负责人' }}</div>
          <div class="value">NOC Architecture Team</div>
        </div>
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseReviewer') || '审核人' }}</div>
          <div class="value">Platform Governance</div>
        </div>
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseWindow') || '生效窗口' }}</div>
          <div class="value">2026-07-21 00:00 - 23:59</div>
        </div>
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseSummary') || '变更摘要' }}</div>
          <div class="value">{{ t('systemHelpReleaseSummaryText') || '新增系统内架构中心、版本切换、目录导航与打印导出能力。' }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const iframeKey = ref(0)
const selectedSection = ref('overall-architecture')
const selectedVersion = ref('v1.1')

const versionOptions = [
  { value: 'v1.1', label: 'v1.1 (Latest)', url: '/system-architecture.html', updatedAt: '2026-07-21' },
  { value: 'v1.0', label: 'v1.0 (Baseline)', url: '/system-architecture-v1.0.html', updatedAt: '2026-07-20' },
]

const sections = [
  { id: 'overall-architecture', label: '📐 整体系统架构' },
  { id: 'core-dataflow-offline', label: '🔄 核心数据流：设备离线检测' },
  { id: 'realtime-alert-stream', label: '🚨 实时告警事件流系统' },
  { id: 'health-scoring', label: '💊 设备健康评分算法' },
  { id: 'ai-analysis-system', label: '🤖 AI研判与建议系统' },
  { id: 'fault-ai-triage', label: '🔬 故障创建与AI预判流程' },
  { id: 'cache-strategy', label: '⚡ 多层缓存策略' },
  { id: 'frontend-auto-refresh', label: '🔄 前端自动刷新机制' },
  { id: 'cost-trend-analysis', label: '💰 成本分析与趋势预测' },
  { id: 'deployment-architecture', label: '🏗️ 部署架构' },
]

const selectedVersionMeta = computed(() => {
  return versionOptions.find(v => v.value === selectedVersion.value) || versionOptions[0]
})

const diagramUrl = computed(() => {
  const base = selectedVersionMeta.value.url
  const anchor = selectedSection.value ? `#${selectedSection.value}` : ''
  return `${base}${anchor}`
})

function onVersionChange() {
  iframeKey.value += 1
}

function jumpToSection(sectionId) {
  selectedSection.value = sectionId
  iframeKey.value += 1
}

function openStandalone() {
  window.open(diagramUrl.value, '_blank', 'noopener')
}

function refreshDiagram() {
  iframeKey.value += 1
}

function printAsPdf() {
  const iframe = document.querySelector('.diagram-frame')
  if (iframe && iframe.contentWindow) {
    iframe.contentWindow.focus()
    iframe.contentWindow.print()
  }
}
</script>

<style scoped>
.system-help-page {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  border: 1px solid #e4e7ed;
  background: linear-gradient(130deg, #f5f7fa 0%, #eef6ff 100%);
}

.hero-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.hero-header h1 {
  margin: 0;
  font-size: 22px;
  color: #303133;
}

.hero-header p {
  margin: 8px 0 0;
  color: #606266;
  font-size: 14px;
}

.meta-row {
  margin-top: 10px;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 12px;
}

.hero-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.highlights {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}

.highlight-item {
  background: #ffffff;
  border: 1px solid #e5eaf3;
  border-left: 4px solid #409eff;
  border-radius: 8px;
  padding: 10px 12px;
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
}

.diagram-card {
  border: 1px solid #e4e7ed;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}

.catalog-card {
  border: 1px solid #e4e7ed;
  height: fit-content;
  position: sticky;
  top: 84px;
}

.version-select {
  width: 100%;
  margin-bottom: 12px;
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 70vh;
  overflow: auto;
}

.catalog-item {
  text-align: left;
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
}

.catalog-item.active,
.catalog-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
  color: #1d4ed8;
}

.diagram-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-weight: 600;
}

.diagram-tip {
  font-size: 12px;
  color: #909399;
  font-weight: 400;
}

.diagram-wrap {
  width: 100%;
  min-height: 74vh;
}

.diagram-frame {
  width: 100%;
  height: 74vh;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}

.release-card {
  border: 1px solid #e4e7ed;
}

.release-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.release-item {
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  padding: 10px;
  background: #fafcff;
}

.release-item .label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.release-item .value {
  font-size: 14px;
  color: #334155;
}

@media (max-width: 900px) {
  .hero-header {
    flex-direction: column;
  }

  .hero-actions {
    width: 100%;
  }

  .hero-actions .el-button {
    flex: 1;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .catalog-card {
    position: static;
  }

  .diagram-wrap,
  .diagram-frame {
    min-height: 66vh;
    height: 66vh;
  }
}
</style>

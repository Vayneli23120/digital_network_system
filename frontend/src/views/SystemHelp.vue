<template>
  <div class="system-help-page">
    <el-card class="hero-card" shadow="never">
      <div class="hero-header">
        <div>
          <h1>{{ t('systemHelpTitle') || '系统架构中心' }}</h1>
          <p>{{ t('systemHelpSubtitle') || '统一展示系统拓扑、模块关系与数据流，便于运维交接和故障分析。' }}</p>
          <div class="meta-row">
            <span>{{ t('systemHelpVersionLabel') || '架构版本' }}: {{ architectureVersion }}</span>
            <span>{{ t('systemHelpUpdatedAtLabel') || '最近更新' }}: {{ updatedAt }}</span>
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
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const diagramUrl = '/system-architecture.html'
const iframeKey = ref(0)
const architectureVersion = 'v1.0.0'
const updatedAt = '2026-07-21'

function openStandalone() {
  window.open(diagramUrl, '_blank', 'noopener')
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
  max-width: 1400px;
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

  .diagram-wrap,
  .diagram-frame {
    min-height: 66vh;
    height: 66vh;
  }
}
</style>

// Compliance 视图纯逻辑：无 vue 依赖、无 i18n 调用，便于单测。
// 从 frontend/src/views/Compliance.vue 拆分（item 946 切片 1），行为与原实现完全一致。

// HTML 转义：v-html 渲染前先惰性化用户内容，防止存储型 XSS
export const escapeHtml = (str) => {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// 渲染章节内容（简单的 Markdown 渲染）
export const renderSectionContent = (content) => {
  if (!content) return ''

  // 先整体转义，正则只作用于白名单标签的生成，捕获内容均为惰性化文本
  let html = escapeHtml(content)

  // 渲染代码块
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')

  // 渲染行内代码
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // 渲染粗体
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // 渲染斜体
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

  // 渲染列表
  html = html.replace(/^[-*]\s+(.+)/gm, '<li>$1</li>')

  // 渲染段落
  html = html.split('\n').map(line => {
    if (line.trim() && !line.startsWith('<')) {
      return `<p>${line}</p>`
    }
    return line
  }).join('\n')

  return html
}

// 解析文档章节，返回 [{ number, title, content }]
// fallbackTitle：内容未解析出任何标题时使用的默认章节标题（调用方传 i18n 文案）
export const parseDocumentSections = (content, fallbackTitle) => {
  const sections = []
  const lines = content.split('\n')

  let currentSection = null
  let sectionContent = []

  // 解析标题结构（支持 ## 格式的 Markdown 标题）
  for (const line of lines) {
    const headingMatch = line.match(/^#{1,3}\s+(\d+(\.\d+)*\.?)?\s*(.+)/)
    if (headingMatch) {
      // 保存上一个章节
      if (currentSection) {
        currentSection.content = sectionContent.join('\n')
        sections.push(currentSection)
      }

      // 开始新章节
      currentSection = {
        number: headingMatch[2] || '',
        title: headingMatch[3].trim(),
        content: ''
      }
      sectionContent = []
    } else if (currentSection) {
      sectionContent.push(line)
    }
  }

  // 保存最后一个章节
  if (currentSection) {
    currentSection.content = sectionContent.join('\n')
    sections.push(currentSection)
  }

  // 如果没有解析到章节，创建一个默认章节
  if (sections.length === 0) {
    sections.push({
      number: '',
      title: fallbackTitle,
      content: content
    })
  }

  return sections
}

// 规则分类 → element-plus tag type
export const categoryType = (cat) => ({ security: 'danger', availability: 'warning', compliance: 'info' }[cat] || '')

// 规则严重级别 → element-plus tag type
export const severityType = (sev) => ({ critical: 'danger', high: 'warning', medium: 'info', low: '' }[sev] || '')

// 分析配置行与检查结果关联，返回行级分析结果（结果内为 configLineAnalysis 结构）
export const analyzeConfigLines = (configText, results) => {
  const lines = configText.split('\n')
  const analysis = []

  // 收集失败项的 pattern
  const failedPatterns = results
    .filter(r => !r.passed && r.pattern)
    .map(r => ({
      ...r,
      patternLower: r.pattern.toLowerCase()
    }))

  // 收集通过项的 pattern
  const passedPatterns = results
    .filter(r => r.passed && r.pattern)
    .map(r => r.pattern.toLowerCase())

  for (let i = 0; i < lines.length; i++) {
    const lineNum = i + 1
    const content = lines[i]
    const contentLower = content.toLowerCase()
    const issues = []
    let isPassed = false

    // 检查失败项是否匹配该行
    for (const failed of failedPatterns) {
      // 简单的关键词匹配或尝试正则匹配
      try {
        if (contentLower.includes(failed.patternLower) ||
            new RegExp(failed.pattern, 'i').test(content)) {
          issues.push({
            check_id: failed.check_id,
            check_name: failed.check_name,
            severity: failed.severity,
            category: failed.category,
            detail: failed.detail,
            recommendation: failed.recommendation
          })
        }
      } catch {
        // 正则无效时使用关键词匹配
        if (contentLower.includes(failed.patternLower)) {
          issues.push({
            check_id: failed.check_id,
            check_name: failed.check_name,
            severity: failed.severity,
            category: failed.category,
            detail: failed.detail,
            recommendation: failed.recommendation
          })
        }
      }
    }

    // 检查是否通过了某些检查
    for (const passedPattern of passedPatterns) {
      if (contentLower.includes(passedPattern)) {
        isPassed = true
        break
      }
    }

    analysis.push({
      lineNum,
      content,
      issues,
      isPassed: isPassed && issues.length === 0
    })
  }

  return analysis
}

// 获取配置行样式类
export const getLineClass = (line) => {
  if (!line.issues || line.issues.length === 0) {
    return line.isPassed ? 'passed' : 'normal'
  }

  // 按最高严重程度确定样式
  const severities = line.issues.map(i => i.severity)
  if (severities.includes('critical')) return 'critical'
  if (severities.includes('high')) return 'high'
  if (severities.includes('medium')) return 'medium'
  return 'low'
}

// 配置高亮面板的严重级别 → element-plus tag type（与 severityType 不同：low → success）
export const severityTagType = (sev) => {
  const types = { critical: 'danger', high: 'warning', medium: 'info', low: 'success' }
  return types[sev] || ''
}

// 配置高亮面板的分类 → element-plus tag type
export const categoryTagType = (cat) => {
  const types = { security: 'danger', availability: 'warning', compliance: 'info' }
  return types[cat] || ''
}

// 首字母大写
export const capitalize = (str) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}

import { Card, Typography, Input, Button, Space, List, Tag, Divider, Spin, Empty, message } from 'antd'
import {
  RobotOutlined,
  SendOutlined,
  BulbOutlined,
  WarningOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useState } from 'react'

const { Title, Text } = Typography
const { TextArea } = Input

interface AnalysisItem {
  id: string
  type: 'fault' | 'config' | 'change'
  query: string
  result: string
  confidence: number
  timestamp: string
}

export default function AIAnalysisPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<AnalysisItem[]>([])

  const handleAnalyze = async () => {
    if (!query.trim()) {
      message.warning('请输入分析内容')
      return
    }

    setLoading(true)

    // TODO: 实际调用 API
    setTimeout(() => {
      const newItem: AnalysisItem = {
        id: `analysis-${Date.now()}`,
        type: 'fault',
        query: query,
        result: '分析结果示例：根据设备配置和故障历史，可能的原因为接口 VLAN 配置不一致。建议检查端口 VLAN 分配并进行修正。',
        confidence: 0.85,
        timestamp: new Date().toISOString(),
      }

      setHistory(prev => [newItem, ...prev])
      setQuery('')
      setLoading(false)
      message.success('分析完成')
    }, 2000)
  }

  const quickActions = [
    { label: '故障根因分析', icon: <WarningOutlined />, type: 'fault' },
    { label: '配置合规检查', icon: <CheckCircleOutlined />, type: 'config' },
    { label: '变更风险评估', icon: <BulbOutlined />, type: 'change' },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        <RobotOutlined style={{ marginRight: 8 }} />
        AI 分析中心
      </Title>

      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 快捷操作 */}
          <div>
            <Text strong>快捷分析：</Text>
            <Space style={{ marginTop: 8 }}>
              {quickActions.map(action => (
                <Button
                  key={action.type}
                  icon={action.icon}
                  onClick={() => setQuery(`${action.label}：请描述具体情况...`)}
                >
                  {action.label}
                </Button>
              ))}
            </Space>
          </div>

          <Divider />

          {/* 分析输入 */}
          <div>
            <Text strong>输入分析内容：</Text>
            <TextArea
              rows={4}
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="描述需要分析的问题，例如：设备 SW-Core-01 出现端口不通，请分析可能的根因..."
              style={{ marginTop: 8 }}
            />
          </div>

          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleAnalyze}
            loading={loading}
            style={{ alignSelf: 'flex-end' }}
          >
            开始分析
          </Button>
        </Space>
      </Card>

      {/* 分析历史 */}
      <Card title="分析历史">
        {loading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="AI 正在分析..." />
          </div>
        )}

        {!loading && history.length === 0 && (
          <Empty description="暂无分析记录" />
        )}

        <List
          dataSource={history}
          renderItem={item => (
            <List.Item>
              <Card style={{ width: '100%' }} size="small">
                <div>
                  <Tag color={item.type === 'fault' ? 'red' : item.type === 'config' ? 'blue' : 'orange'}>
                    {item.type === 'fault' ? '故障分析' : item.type === 'config' ? '配置检查' : '风险评估'}
                  </Tag>
                  <Text type="secondary" style={{ marginLeft: 8 }}>
                    {new Date(item.timestamp).toLocaleString()}
                  </Text>
                </div>

                <div style={{ marginTop: 8 }}>
                  <Text strong>问题：</Text>
                  <Text>{item.query}</Text>
                </div>

                <div style={{ marginTop: 8 }}>
                  <Text strong>分析结果：</Text>
                  <Text>{item.result}</Text>
                </div>

                <div style={{ marginTop: 8 }}>
                  <Tag color="green">置信度：{(item.confidence * 100).toFixed(0)}%</Tag>
                </div>
              </Card>
            </List.Item>
          )}
        />
      </Card>
    </div>
  )
}
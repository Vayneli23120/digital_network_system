import { Card, Row, Col, Statistic, Progress, Tag, Typography } from 'antd'
import {
  DashboardOutlined,
  RobotOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons'

const { Title } = Typography

export default function DashboardPage() {
  // TODO: 从 API 获取实际数据
  const stats = {
    totalDevices: 120,
    onlineDevices: 108,
    offlineDevices: 12,
    totalJobs: 245,
    successRate: 95.2,
    pendingJobs: 3,
    runningJobs: 2,
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        <DashboardOutlined style={{ marginRight: 8 }} />
        系统概览
      </Title>

      <Row gutter={[16, 16]}>
        {/* 设备统计 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="设备总数"
              value={stats.totalDevices}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="在线设备"
              value={stats.onlineDevices}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="离线设备"
              value={stats.offlineDevices}
              valueStyle={{ color: '#cf1322' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="作业成功率"
              value={stats.successRate}
              suffix="%"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>

        {/* 作业状态 */}
        <Col xs={24} lg={12}>
          <Card title="作业状态">
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="等待中"
                  value={stats.pendingJobs}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="运行中"
                  value={stats.runningJobs}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="总计"
                  value={stats.totalJobs}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        {/* AI 分析 */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <span>
                <RobotOutlined style={{ marginRight: 8 }} />
                AI 分析中心
              </span>
            }
            extra={<Tag color="green">可用</Tag>}
          >
            <p>AI 故障分析、配置合规检查、变更风险评估等功能已就绪。</p>
            <p>前往 <a href="/ai-analysis">AI 分析中心</a> 开始使用。</p>
          </Card>
        </Col>

        {/* 系统健康度 */}
        <Col xs={24}>
          <Card title="系统健康度">
            <Row gutter={16}>
              <Col span={6}>
                <div style={{ textAlign: 'center' }}>
                  <Progress type="circle" percent={95} size={80} />
                  <div style={{ marginTop: 8 }}>数据库</div>
                </div>
              </Col>
              <Col span={6}>
                <div style={{ textAlign: 'center' }}>
                  <Progress type="circle" percent={100} size={80} status="success" />
                  <div style={{ marginTop: 8 }}>Redis</div>
                </div>
              </Col>
              <Col span={6}>
                <div style={{ textAlign: 'center' }}>
                  <Progress type="circle" percent={88} size={80} />
                  <div style={{ marginTop: 8 }}>任务队列</div>
                </div>
              </Col>
              <Col span={6}>
                <div style={{ textAlign: 'center' }}>
                  <Progress type="circle" percent={92} size={80} />
                  <div style={{ marginTop: 8 }}>AI 服务</div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
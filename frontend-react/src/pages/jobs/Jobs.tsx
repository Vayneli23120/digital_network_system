import { Card, Table, Tag, Button, Space, Typography, Progress, Tooltip, Badge } from 'antd'
import {
  DatabaseOutlined,
  ReloadOutlined,
  StopOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useState } from 'react'
import { useJobs, useCancelJob } from '@/api'
import type { Job, JobStatus } from '@/types/api'

const { Title } = Typography

const statusColors: Record<JobStatus, string> = {
  pending: 'default',
  queued: 'blue',
  running: 'orange',
  success: 'green',
  failed: 'red',
  cancelled: 'default',
  timeout: 'red',
  partial: 'gold',
}

const statusLabels: Record<JobStatus, string> = {
  pending: '等待中',
  queued: '已入队',
  running: '运行中',
  success: '成功',
  failed: '失败',
  cancelled: '已取消',
  timeout: '超时',
  partial: '部分成功',
}

const typeLabels: Record<string, string> = {
  backup: '配置备份',
  deploy: '配置部署',
  compliance_scan: '合规扫描',
  discovery: '设备发现',
  health_check: '健康检查',
  command_exec: '命令执行',
}

export default function JobsPage() {
  const [filters, setFilters] = useState<{ status?: JobStatus; job_type?: string }>({})
  const { data, isLoading, refetch } = useJobs({ ...filters, limit: 50 })
  const cancelJob = useCancelJob()

  const handleCancel = (jobId: string) => {
    cancelJob.mutate(jobId)
  }

  const columns = [
    {
      title: '作业ID',
      dataIndex: 'id',
      key: 'id',
      width: 280,
      render: (id: string) => (
        <Tooltip title={id}>
          <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
            {id.slice(0, 8)}...
          </span>
        </Tooltip>
      ),
    },
    {
      title: '类型',
      dataIndex: 'job_type',
      key: 'job_type',
      render: (type: string) => typeLabels[type] || type,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: JobStatus) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
      filters: Object.entries(statusLabels).map(([value, label]) => ({ text: label, value })),
      onFilter: (value: unknown, record: Job) => record.status === value,
    },
    {
      title: '进度',
      dataIndex: 'progress_percent',
      key: 'progress_percent',
      render: (percent: number) => (
        <Progress
          percent={percent}
          size="small"
          status={percent === 100 ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '操作人',
      dataIndex: 'operator',
      key: 'operator',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString(),
      sorter: (a: Job, b: Job) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Job) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            href={`/jobs/${record.id}`}
          >
            详情
          </Button>
          {['pending', 'queued', 'running'].includes(record.status) && (
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleCancel(record.id)}
              loading={cancelJob.isPending}
            >
              取消
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        <DatabaseOutlined style={{ marginRight: 8 }} />
        作业监控
      </Title>

      <Card
        extra={
          <Space>
            <Badge count={data?.total || 0} showZero style={{ marginRight: 16 }}>
              <span>总作业数</span>
            </Badge>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={data?.items || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            total: data?.total || 0,
            pageSize: 50,
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`,
          }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  )
}
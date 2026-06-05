import { Form, Input, Button, Card, Typography, message } from 'antd'
import { UserOutlined, LockOutlined, Monitor } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuthStore } from '@/app/store/auth'
import apiClient from '@/api/client'

const { Title, Text } = Typography

interface LoginForm {
  username: string
  password: string
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { login } = useAuthStore()

  const onFinish = async (values: LoginForm) => {
    setLoading(true)
    setError('')

    try {
      const response = await apiClient.post('/auth/login', {
        username: values.username,
        password: values.password,
      }) as { access_token: string; username?: string }

      // Token 格式校验
      const token = response.access_token
      const parts = token.split('.')
      if (parts.length !== 3) {
        setError('服务器返回的 Token 格式无效')
        return
      }

      // 登录成功
      login(token, response.username || values.username)
      message.success('登录成功')
      navigate('/')

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '登录失败'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #001529 0%, #003a70 100%)',
      }}
    >
      <Card
        style={{
          width: 400,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Monitor style={{ fontSize: 48, color: '#1890ff' }} />
          <Title level={3} style={{ marginTop: 16 }}>
            NAS
          </Title>
          <Text type="secondary">网络自动化系统</Text>
        </div>

        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
            />
          </Form.Item>

          {error && (
            <div style={{ marginBottom: 16, color: '#cf1322', textAlign: 'center' }}>
              {error}
            </div>
          )}

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', color: '#999', fontSize: 12 }}>
          v2.0.0
        </div>
      </Card>
    </div>
  )
}
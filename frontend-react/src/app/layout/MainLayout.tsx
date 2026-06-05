import { Outlet, Navigate } from 'react-router-dom'
import { Layout, Menu, Dropdown, Avatar } from 'antd'
import {
  DashboardOutlined,
  RobotOutlined,
  DatabaseOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/app/store/auth'

const { Header, Sider, Content } = Layout

const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/ai-analysis',
    icon: <RobotOutlined />,
    label: 'AI 分析',
  },
  {
    key: '/jobs',
    icon: <DatabaseOutlined />,
    label: '作业监控',
  },
  // 更多菜单项将在后续添加
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { currentUser, logout } = useAuthStore()

  const handleMenuClick = (key: string) => {
    navigate(key)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        style={{
          background: '#001529',
        }}
        collapsible
        collapsedWidth={80}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 18,
            fontWeight: 'bold',
          }}
        >
          NAS
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => handleMenuClick(key)}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 500 }}>
            网络自动化系统
          </div>

          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar icon={<UserOutlined />} />
              <span>{currentUser || '用户'}</span>
            </div>
          </Dropdown>
        </Header>

        <Content
          style={{
            margin: 24,
            padding: 24,
            background: '#fff',
            borderRadius: 8,
            minHeight: 'calc(100vh - 112px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
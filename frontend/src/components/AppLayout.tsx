import { useState, ReactNode } from 'react'
import { Layout, Menu, Button, message, Tag } from 'antd'
import { LogoutOutlined, BookOutlined, UserOutlined, BarChartOutlined, IdcardOutlined, CalendarOutlined, FileTextOutlined, WifiOutlined, LoginOutlined, AppstoreOutlined, NotificationOutlined, ScheduleOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const { Header, Content, Sider } = Layout

const COLLAPSED_KEY = 'sidebar_collapsed'

interface AppLayoutProps {
  children: ReactNode
  standaloneMode?: boolean  // 独立模式（只使用校园网）
}

export default function AppLayout({ children, standaloneMode = false }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { checkAuth, isAuthenticated } = useAuth()
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem(COLLAPSED_KEY)
    return saved === 'true'
  })

  const handleCollapse = (value: boolean) => {
    setCollapsed(value)
    localStorage.setItem(COLLAPSED_KEY, String(value))
  }

  const onLogout = async () => {
    try {
      await api.post('/auth/logout')
      message.success('已退出登录')
      await checkAuth()
      navigate('/login')
    } catch {
      message.error('退出失败')
    }
  }

  // 根据当前路径确定选中的菜单项
  const getSelectedKey = () => {
    const path = location.pathname
    if (path === '/dashboard') return 'dashboard'
    if (path === '/schedule') return 'schedule'
    if (path === '/grades') return 'grades'
    if (path === '/user-info') return 'user-info'
    if (path === '/progress') return 'progress'
    if (path === '/exams') return 'exams'
    if (path === '/courses') return 'courses'
    if (path === '/calendar') return 'calendar'
    if (path === '/notices') return 'notices'
    if (path === '/wifi') return 'wifi'
    return 'dashboard'
  }

  // 独立模式下使用的菜单
  const standaloneMenuItems = (
    <Menu theme="dark" selectedKeys={[getSelectedKey()]} mode="inline">
      <Menu.Item key="wifi" icon={<WifiOutlined />} onClick={() => navigate('/wifi')}>校园网</Menu.Item>
    </Menu>
  )

  // 完整模式下使用的菜单
  const fullMenuItems = (
    <Menu theme="dark" selectedKeys={[getSelectedKey()]} mode="inline">
      <Menu.Item key="dashboard" icon={<IdcardOutlined />} onClick={() => navigate('/dashboard')}>首页</Menu.Item>
      <Menu.Item key="user-info" icon={<UserOutlined />} onClick={() => navigate('/user-info')}>用户信息</Menu.Item>
      <Menu.Item key="schedule" icon={<CalendarOutlined />} onClick={() => navigate('/schedule')}>课表查询</Menu.Item>
      <Menu.Item key="grades" icon={<BookOutlined />} onClick={() => navigate('/grades')}>成绩查询</Menu.Item>
      <Menu.Item key="exams" icon={<FileTextOutlined />} onClick={() => navigate('/exams')}>考试安排</Menu.Item>
      <Menu.Item key="courses" icon={<AppstoreOutlined />} onClick={() => navigate('/courses')}>选课查询</Menu.Item>
      <Menu.Item key="progress" icon={<BarChartOutlined />} onClick={() => navigate('/progress')}>
        学业进度 <Tag color="blue" style={{ marginLeft: 4, fontSize: 10 }}>Beta</Tag>
      </Menu.Item>
      <Menu.Item key="calendar" icon={<ScheduleOutlined />} onClick={() => navigate('/calendar')}>校历</Menu.Item>
      <Menu.Item key="notices" icon={<NotificationOutlined />} onClick={() => navigate('/notices')}>通知公告</Menu.Item>
      <Menu.Item key="wifi" icon={<WifiOutlined />} onClick={() => navigate('/wifi')}>校园网</Menu.Item>
    </Menu>
  )

  // 判断是否为纯独立模式（没有教务系统登录）
  const isPureStandaloneMode = standaloneMode && !isAuthenticated

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={handleCollapse}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          height: '100vh',
          overflow: 'auto',
          zIndex: 100,
        }}
      >
        <div style={{
          height: 32,
          margin: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontWeight: 'bold',
          fontSize: collapsed ? 14 : 16,
          whiteSpace: 'nowrap',
          overflow: 'hidden'
        }}>
          {collapsed ? 'USTB' : 'USTB Manager'}
        </div>
        {isPureStandaloneMode ? standaloneMenuItems : fullMenuItems}
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8 }}>
          {isPureStandaloneMode && (
            <Button icon={<LoginOutlined />} onClick={() => navigate('/login')}>
              登录更多功能
            </Button>
          )}
          <Button icon={<LogoutOutlined />} onClick={onLogout}>退出</Button>
        </Header>
        <Content style={{ margin: 24 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

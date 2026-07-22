import { useState, useEffect, ReactNode, useMemo } from 'react'
import { ConfigProvider, Layout, Menu, Button, Tag, Tooltip, Grid, Drawer, Dropdown, message } from 'antd'
import {
  LogoutOutlined, BookOutlined, UserOutlined, BarChartOutlined, IdcardOutlined,
  CalendarOutlined, FileTextOutlined, WifiOutlined, LoginOutlined, AppstoreOutlined,
  NotificationOutlined, ScheduleOutlined, SunOutlined, MoonOutlined, DesktopOutlined,
  MenuOutlined, CheckOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useTheme, ThemeMode } from '../contexts/ThemeContext'

const { Header, Content, Sider } = Layout

const COLLAPSED_KEY = 'sidebar_collapsed'

interface AppLayoutProps {
  children: ReactNode
  standaloneMode?: boolean  // 独立模式（只使用校园网）
}

// 页面标题映射
const PAGE_TITLES: Record<string, string> = {
  '/dashboard': '首页',
  '/user-info': '用户信息',
  '/schedule': '课表查询',
  '/grades': '成绩查询',
  '/exams': '考试安排',
  '/courses': '选课查询',
  '/progress': '学业进度',
  '/calendar': '校历',
  '/notices': '通知公告',
  '/wifi': '校园网',
}

const THEME_OPTIONS: { key: ThemeMode; label: string; icon: ReactNode }[] = [
  { key: 'light', label: '浅色', icon: <SunOutlined /> },
  { key: 'dark', label: '深色', icon: <MoonOutlined /> },
  { key: 'system', label: '跟随系统', icon: <DesktopOutlined /> },
]

export default function AppLayout({ children, standaloneMode = false }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { checkAuth, isAuthenticated } = useAuth()
  const { mode: themeMode, setMode: setThemeMode } = useTheme()
  const screens = Grid.useBreakpoint()
  const isMobile = !screens.lg

  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem(COLLAPSED_KEY)
    return saved === 'true'
  })
  const [drawerOpen, setDrawerOpen] = useState(false)

  // 路由变化时关闭移动端抽屉
  useEffect(() => {
    setDrawerOpen(false)
  }, [location.pathname])

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
    if (PAGE_TITLES[path]) return path.slice(1)
    return 'dashboard'
  }

  const pageTitle = PAGE_TITLES[location.pathname] || 'USTB Manager'

  // 判断是否为纯独立模式（没有教务系统登录）
  const isPureStandaloneMode = standaloneMode && !isAuthenticated

  const menuItems = useMemo(() => {
    if (isPureStandaloneMode) {
      return [{ key: 'wifi', icon: <WifiOutlined />, label: '校园网' }]
    }
    return [
      { key: 'dashboard', icon: <IdcardOutlined />, label: '首页' },
      { key: 'user-info', icon: <UserOutlined />, label: '用户信息' },
      { type: 'divider' as const },
      { key: 'schedule', icon: <CalendarOutlined />, label: '课表查询' },
      { key: 'grades', icon: <BookOutlined />, label: '成绩查询' },
      { key: 'exams', icon: <FileTextOutlined />, label: '考试安排' },
      { key: 'courses', icon: <AppstoreOutlined />, label: '选课查询' },
      {
        key: 'progress',
        icon: <BarChartOutlined />,
        label: (
          <span>
            学业进度 <Tag color="blue" style={{ marginLeft: 4, fontSize: 10, lineHeight: '14px' }}>Beta</Tag>
          </span>
        ),
      },
      { type: 'divider' as const },
      { key: 'calendar', icon: <ScheduleOutlined />, label: '校历' },
      { key: 'notices', icon: <NotificationOutlined />, label: '通知公告' },
      { key: 'wifi', icon: <WifiOutlined />, label: '校园网' },
    ]
  }, [isPureStandaloneMode])

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(`/${key}`)
  }

  const themeMenu = {
    items: THEME_OPTIONS.map(opt => ({
      key: opt.key,
      icon: opt.icon,
      label: (
        <span style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          {opt.label}
          {themeMode === opt.key && <CheckOutlined style={{ color: 'var(--ant-color-primary)' }} />}
        </span>
      ),
      onClick: () => setThemeMode(opt.key),
    })),
    selectedKeys: [themeMode],
  }

  const ThemeIcon = themeMode === 'dark' ? MoonOutlined : themeMode === 'light' ? SunOutlined : DesktopOutlined

  const menuContent = (
    <>
      <div className={`app-sider-brand ${(!isMobile && collapsed) ? 'collapsed' : ''}`}>
        <div className="app-sider-brand-logo">U</div>
        <span className="app-sider-brand-name">USTB Manager</span>
      </div>
      <Menu
        selectedKeys={[getSelectedKey()]}
        mode="inline"
        items={menuItems}
        onClick={handleMenuClick}
        style={{ borderInlineEnd: 'none', padding: '8px 0', background: 'transparent' }}
      />
    </>
  )

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {isMobile ? (
        <Drawer
          placement="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          size={240}
          styles={{ body: { padding: 0 } }}
        >
          {menuContent}
        </Drawer>
      ) : (
        // ConfigProvider 局部覆盖：让折叠触发条背景与侧边栏一致
        <ConfigProvider theme={{ components: { Layout: { triggerBg: 'var(--app-sidebar-bg)', triggerColor: 'var(--app-text-secondary)' } } }}>
          <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={handleCollapse}
            width={220}
            collapsedWidth={72}
            className="app-sider"
            style={{
              position: 'fixed',
              left: 0,
              top: 0,
              bottom: 0,
              height: '100vh',
              overflow: 'auto',
              zIndex: 100,
              background: 'var(--app-sidebar-bg)',
            }}
          >
            {menuContent}
          </Sider>
        </ConfigProvider>
      )}

      <Layout style={{
        marginLeft: isMobile ? 0 : (collapsed ? 72 : 220),
        transition: 'margin-left 0.2s',
        background: 'var(--app-content-bg)',
      }}>
        <Header
          className="app-header"
          style={{
            background: 'var(--app-header-bg)',
            padding: '0 20px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          {isMobile && (
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setDrawerOpen(true)}
              aria-label="打开菜单"
            />
          )}
          <div className="app-header-title" style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {pageTitle}
          </div>
          {isPureStandaloneMode && (
            <Button icon={<LoginOutlined />} onClick={() => navigate('/login')} size={isMobile ? 'small' : 'middle'}>
              登录更多功能
            </Button>
          )}
          <Dropdown menu={themeMenu} placement="bottomRight" trigger={['click']}>
            <Tooltip title="主题设置">
              <Button type="text" icon={<ThemeIcon />} aria-label="主题设置" />
            </Tooltip>
          </Dropdown>
          <Tooltip title="退出登录">
            <Button type="text" icon={<LogoutOutlined />} onClick={onLogout} aria-label="退出登录" />
          </Tooltip>
        </Header>
        <Content style={{ margin: isMobile ? 16 : 24, minWidth: 0 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

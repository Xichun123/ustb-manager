import { useEffect } from 'react'
import { Tabs, Card, Layout, Spin, Button, Divider } from 'antd'
import { useNavigate } from 'react-router-dom'
import { WifiOutlined } from '@ant-design/icons'
import { QRLogin } from '../components/QRLogin'
import { SMSLogin } from '../components/SMSLogin'
import { CookieLogin } from '../components/CookieLogin'
import { useAuth } from '../contexts/AuthContext'

const { Content } = Layout

export function LoginPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuth()

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  // 在检查认证状态时显示loading，避免在已登录时渲染QRLogin
  if (isLoading) {
    return (
      <Layout style={{ minHeight: '100vh', justifyContent: 'center', alignItems: 'center', background: '#f0f2f5' }}>
        <Spin size="large" tip="检查登录状态..." />
      </Layout>
    )
  }

  const items = [
    { key: 'qr', label: '微信扫码', children: <QRLogin /> },
    { key: 'sms', label: '短信验证', children: <SMSLogin /> },
    { key: 'cookie', label: 'Cookie登录', children: <CookieLogin /> },
  ]

  return (
    <Layout style={{ minHeight: '100vh', justifyContent: 'center', alignItems: 'center', background: '#f0f2f5' }}>
      <Content>
        <Card title="USTB Manager 登录" style={{ width: 450 }}>
          <Tabs defaultActiveKey="qr" items={items} centered destroyInactiveTabPane />
          <Divider style={{ margin: '16px 0' }}>或者</Divider>
          <Button
            block
            icon={<WifiOutlined />}
            onClick={() => navigate('/wifi-standalone')}
          >
            只使用校园网功能
          </Button>
        </Card>
      </Content>
    </Layout>
  )
}
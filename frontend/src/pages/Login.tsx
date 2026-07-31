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
      <Layout className="auth-page-bg" style={{ minHeight: '100vh', justifyContent: 'center', alignItems: 'center' }}>
        <Spin size="large" description="检查登录状态..." />
      </Layout>
    )
  }

  const items = [
    { key: 'qr', label: '微信扫码', children: <QRLogin /> },
    { key: 'sms', label: '短信验证', children: <SMSLogin /> },
    { key: 'cookie', label: 'Cookie登录', children: <CookieLogin /> },
  ]

  return (
    <Layout className="auth-page-bg" style={{ minHeight: '100vh', justifyContent: 'center', alignItems: 'center' }}>
      <Content style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1, padding: 24 }}>
        {/* 品牌区 */}
        <div style={{ textAlign: 'center', marginBottom: 28, color: '#fff' }}>
          <img className="auth-brand-logo" src="/app-icon.png" alt="" aria-hidden="true" />
          <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: 0.5 }}>USTB Manager</div>
          <div style={{ fontSize: 13, opacity: 0.85, marginTop: 6 }}>北科大学业一站式管理平台</div>
        </div>

        <Card
          style={{
            width: 440,
            maxWidth: 'calc(100vw - 32px)',
            borderRadius: 16,
            boxShadow: '0 12px 48px rgba(0, 0, 0, 0.25)',
          }}
          styles={{ body: { padding: '20px 24px 24px' } }}
        >
          <Tabs defaultActiveKey="qr" items={items} centered destroyOnHidden />
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

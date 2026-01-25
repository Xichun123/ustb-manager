import { useEffect, useState } from 'react'
import { Card, Form, Input, Button, message, Layout, Spin } from 'antd'
import { UserOutlined, LockOutlined, WifiOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

const { Content } = Layout

export default function WifiStandalonePage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(true)

  // 检查是否已经登录过校园网
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await api.get('/wifi/standalone-status')
        if (res.data.logged_in || res.data.has_credential) {
          // 已有登录状态或保存的凭据，直接跳转到 wifi 页面
          navigate('/wifi', { replace: true })
        }
      } catch (err) {
        // 忽略错误
      } finally {
        setChecking(false)
      }
    }
    checkStatus()
  }, [navigate])

  const handleSubmit = async (values: { student_id: string; password: string }) => {
    setLoading(true)
    try {
      await api.post('/wifi/standalone-login', values)
      message.success('登录成功')
      navigate('/wifi', { replace: true })
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登录失败'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  if (checking) {
    return (
      <Layout style={{ minHeight: '100vh', justifyContent: 'center', alignItems: 'center', background: '#f0f2f5' }}>
        <Spin size="large" tip="检查登录状态..." />
      </Layout>
    )
  }

  return (
    <Layout style={{ minHeight: '100vh', justifyContent: 'center', alignItems: 'center', background: '#f0f2f5' }}>
      <Content>
        <Card
          title={
            <span>
              <WifiOutlined style={{ marginRight: 8 }} />
              校园网登录
            </span>
          }
          style={{ width: 400 }}
          extra={
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/login')}
            >
              返回
            </Button>
          }
        >
          <div style={{ marginBottom: 16, color: '#666' }}>
            使用学号和校园网密码登录，可查看流量余额、管理设备等。
          </div>
          <Form form={form} onFinish={handleSubmit} layout="vertical">
            <Form.Item
              name="student_id"
              label="学号"
              rules={[{ required: true, message: '请输入学号' }]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="请输入学号"
                autoFocus
              />
            </Form.Item>
            <Form.Item
              name="password"
              label="校园网密码"
              rules={[{ required: true, message: '请输入校园网密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="请输入校园网密码"
              />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" loading={loading} block>
                登录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Content>
    </Layout>
  )
}

import { useEffect, useState } from 'react'
import { Card, Form, Input, Button, message, Layout, Spin } from 'antd'
import { UserOutlined, LockOutlined, WifiOutlined, ArrowLeftOutlined, ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

const { Content } = Layout

interface WifiLoginChallenge {
  challenge_token: string
  captcha_image: string
  expires_in: number
  mode?: 'direct' | 'webvpn'
}

export default function WifiStandalonePage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(true)
  const [challengeLoading, setChallengeLoading] = useState(false)
  const [challenge, setChallenge] = useState<WifiLoginChallenge | null>(null)
  const studentIdValue = Form.useWatch('student_id', form)
  const passwordValue = Form.useWatch('password', form)

  const loadChallenge = async (resetCaptcha = true, studentId?: string, password?: string, silent = false) => {
    setChallengeLoading(true)
    try {
      const payload = {
        ...(studentId ? { student_id: studentId } : {}),
        ...(password ? { password } : {}),
      }
      const res = await api.post<WifiLoginChallenge>('/wifi/login/challenge', payload)
      setChallenge(res.data)
      if (resetCaptcha) {
        form.setFieldValue('captcha_code', '')
      }
      return true
    } catch (err: any) {
      const detail = err.response?.data?.detail || '获取验证码失败'
      if (!silent) {
        message.error(detail)
      }
      return false
    } finally {
      setChallengeLoading(false)
    }
  }

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await api.get('/wifi/standalone-status')
        if (res.data.logged_in || res.data.has_credential) {
          navigate('/wifi', { replace: true })
        }
      } catch (_err) {
        // ignore
      } finally {
        setChecking(false)
      }
    }
    checkStatus()
  }, [navigate])

  useEffect(() => {
    if (challenge?.mode === 'webvpn') {
      setChallenge(null)
      form.setFieldValue('captcha_code', '')
    }
  }, [studentIdValue, passwordValue])

  const handleSubmit = async (values: { student_id: string; password: string; captcha_code: string }) => {
    if (!challenge?.challenge_token) {
      const ok = await loadChallenge(true, values.student_id, values.password)
      if (ok) {
        message.info('验证码已加载，请输入后再登录')
      }
      return
    }

    setLoading(true)
    try {
      await api.post('/wifi/standalone-login', {
        student_id: values.student_id,
        password: values.password,
        challenge_token: challenge.challenge_token,
        captcha_code: values.captcha_code,
      })
      message.success('登录成功')
      navigate('/wifi', { replace: true })
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登录失败'
      message.error(detail)
      await loadChallenge()
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
            请输入学号和校园网密码后获取 zifuwu 验证码。
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
            <Form.Item
              name="captcha_code"
              label="验证码"
              rules={[{ required: true, message: '请输入验证码' }]}
            >
              <Input
                prefix={<SafetyCertificateOutlined />}
                placeholder="请输入图中验证码"
                suffix={
                  <Button
                    type="text"
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => loadChallenge(true, studentIdValue, passwordValue)}
                    loading={challengeLoading}
                  />
                }
              />
            </Form.Item>
            <div style={{ marginBottom: 16 }}>
              {challenge?.captcha_image ? (
                <img
                  src={challenge.captcha_image}
                  alt="校园网验证码"
                  onClick={() => loadChallenge(true, studentIdValue, passwordValue)}
                  style={{
                    display: 'block',
                    width: 160,
                    height: 52,
                    border: '1px solid #d9d9d9',
                    borderRadius: 6,
                    cursor: 'pointer',
                    background: '#fff',
                  }}
                />
              ) : (
                <div
                  style={{
                    width: 160,
                    height: 52,
                    border: '1px dashed #d9d9d9',
                    borderRadius: 6,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#999',
                  }}
                >
                  {challengeLoading ? '加载中...' : ((studentIdValue && passwordValue) ? '点击刷新验证码' : '先输入学号和密码后获取验证码')}
                </div>
              )}
              <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                先输入学号和密码，再点击验证码图片或刷新按钮获取
              </div>
            </div>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" loading={loading} block disabled={challengeLoading}>
                登录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Content>
    </Layout>
  )
}

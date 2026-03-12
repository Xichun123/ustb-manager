import { useEffect, useState } from 'react'
import { Modal, Form, Input, Button, message } from 'antd'
import { LockOutlined, ReloadOutlined, SafetyCertificateOutlined, WifiOutlined } from '@ant-design/icons'
import { api } from '../services/api'

interface WifiLoginModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

interface WifiLoginChallenge {
  challenge_token: string
  captcha_image: string
  expires_in: number
  mode?: 'direct' | 'webvpn'
}

export default function WifiLoginModal({ open, onClose, onSuccess }: WifiLoginModalProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [challengeLoading, setChallengeLoading] = useState(false)
  const [challenge, setChallenge] = useState<WifiLoginChallenge | null>(null)
  const passwordValue = Form.useWatch('password', form)

  const loadChallenge = async (resetCaptcha = true, password?: string, silent = false) => {
    setChallengeLoading(true)
    try {
      const payload = password ? { password } : {}
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
    if (open) {
      form.resetFields()
      setChallenge(null)
      return
    }
    setChallenge(null)
    form.resetFields()
  }, [open])

  useEffect(() => {
    if (challenge?.mode === 'webvpn') {
      setChallenge(null)
      form.setFieldValue('captcha_code', '')
    }
  }, [passwordValue])

  const handleSubmit = async (values: { password: string; captcha_code: string }) => {
    if (!challenge?.challenge_token) {
      const ok = await loadChallenge(true, values.password)
      if (ok) {
        message.info('验证码已加载，请输入后再登录')
      }
      return
    }

    setLoading(true)
    try {
      await api.post('/wifi/login', {
        password: values.password,
        challenge_token: challenge.challenge_token,
        captcha_code: values.captcha_code,
      })
      message.success('校园网登录成功')
      form.resetFields()
      onSuccess()
      onClose()
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登录失败'
      message.error(detail)
      await loadChallenge()
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title={
        <span>
          <WifiOutlined style={{ marginRight: 8 }} />
          校园网登录
        </span>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnClose
    >
      <div style={{ marginBottom: 16, color: '#666' }}>
        使用您的校园网密码登录，学号将自动从教务系统获取。
        请输入密码后获取 zifuwu 验证码。
      </div>
      <Form form={form} onFinish={handleSubmit} layout="vertical">
        <Form.Item
          name="password"
          label="校园网密码"
          rules={[{ required: true, message: '请输入校园网密码' }]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="请输入校园网密码"
            autoFocus
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
                onClick={() => loadChallenge(true, passwordValue)}
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
              onClick={() => loadChallenge(true, passwordValue)}
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
              {challengeLoading ? '加载中...' : (passwordValue ? '点击刷新验证码' : '先输入密码后获取验证码')}
            </div>
          )}
          <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
            先输入密码，再点击验证码图片或刷新按钮获取
          </div>
        </div>
        <Form.Item style={{ marginBottom: 0 }}>
          <Button type="primary" htmlType="submit" loading={loading} block disabled={challengeLoading}>
            登录
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  )
}

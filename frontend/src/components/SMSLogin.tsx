import { useState, useEffect, useRef } from 'react'
import { Form, Input, Button, message } from 'antd'
import { MobileOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const PHONE_STORAGE_KEY = 'ustb_saved_phone'

export function SMSLogin() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [inited, setInited] = useState(false)
  const navigate = useNavigate()
  const mounted = useRef(true)
  const { setAuthenticated } = useAuth()

  useEffect(() => {
    mounted.current = true
    // 加载保存的手机号
    const savedPhone = localStorage.getItem(PHONE_STORAGE_KEY)
    if (savedPhone) {
      form.setFieldsValue({ phone: savedPhone })
    }
    return () => { mounted.current = false }
  }, [])

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown])

  const onSendCode = async () => {
    const phone = form.getFieldValue('phone')
    if (!phone) {
      message.error('请输入手机号')
      return
    }
    setLoading(true)
    try {
      if (!inited) {
        await api.post('/auth/sms/init')
        if (mounted.current) setInited(true)
      }
      await api.post('/auth/sms/send', { phone })
      if (mounted.current) {
        message.success('验证码已发送')
        setCountdown(60)
      }
    } catch (error: any) {
      if (mounted.current) {
        const status = error?.response?.status
        const errorMsg = error?.response?.data?.detail || '发送失败'
        
        if (status === 429) {
          message.warning(errorMsg)
        } else {
          message.error(errorMsg)
        }
      }
    } finally {
      if (mounted.current) setLoading(false)
    }
  }

  const onFinish = async (values: { phone: string; code: string }) => {
    setLoading(true)
    try {
      await api.post('/auth/sms/verify', values)
      if (mounted.current) {
        // 登录成功，保存手机号
        localStorage.setItem(PHONE_STORAGE_KEY, values.phone)
        message.success('登录成功')
        setAuthenticated(true)
        navigate('/dashboard', { replace: true })
      }
    } catch {
      if (mounted.current) message.error('验证失败')
    } finally {
      if (mounted.current) setLoading(false)
    }
  }

  return (
    <Form form={form} onFinish={onFinish} layout="vertical" style={{ maxWidth: 300, margin: '0 auto' }}>
      <Form.Item name="phone" label="手机号" rules={[{ required: true, message: '请输入手机号' }]}>
        <Input prefix={<MobileOutlined />} placeholder="请输入手机号" aria-label="手机号" />
      </Form.Item>
      <Form.Item label="验证码">
        <div style={{ display: 'flex', gap: 8 }}>
          <Form.Item name="code" noStyle rules={[{ required: true, message: '请输入验证码' }]}>
            <Input prefix={<LockOutlined />} placeholder="请输入验证码" aria-label="验证码" />
          </Form.Item>
          <Button onClick={onSendCode} disabled={countdown > 0 || loading}>
            {countdown > 0 ? `${countdown}s` : '发送'}
          </Button>
        </div>
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" block loading={loading}>
          登录
        </Button>
      </Form.Item>
    </Form>
  )
}
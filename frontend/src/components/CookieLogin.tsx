import { useState, useRef, useEffect } from 'react'
import { Form, Input, Button, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

export function CookieLogin() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const mounted = useRef(true)
  const { setAuthenticated } = useAuth()

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const onFinish = async (values: { cookies: string }) => {
    setLoading(true)
    try {
      const response = await api.post('/auth/cookie/login', { cookies: values.cookies })
      if (mounted.current) {
        message.success(`登录成功！欢迎 ${response.data.student_name || response.data.student_id}`)
        setAuthenticated(true)
        navigate('/dashboard', { replace: true })
      }
    } catch (error: any) {
      if (mounted.current) {
        const errorMsg = error?.response?.data?.detail || '登录失败'
        message.error(errorMsg)
      }
    } finally {
      if (mounted.current) setLoading(false)
    }
  }

  return (
    <Form form={form} onFinish={onFinish} layout="vertical" style={{ maxWidth: 400, margin: '0 auto' }}>
      <Form.Item 
        name="cookies" 
        label="Cookie" 
        rules={[{ required: true, message: '请输入Cookie' }]}
        extra="格式: INCO=xxx; SESSION=yyy"
      >
        <Input.TextArea
          placeholder="INCO=xxx; SESSION=yyy" 
          aria-label="Cookie"
          rows={4}
        />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" block loading={loading}>
          登录
        </Button>
      </Form.Item>
    </Form>
  )
}

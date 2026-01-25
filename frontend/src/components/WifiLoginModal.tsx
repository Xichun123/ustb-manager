import { useState } from 'react'
import { Modal, Form, Input, Button, message } from 'antd'
import { LockOutlined, WifiOutlined } from '@ant-design/icons'
import { api } from '../services/api'

interface WifiLoginModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function WifiLoginModal({ open, onClose, onSuccess }: WifiLoginModalProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: { password: string }) => {
    setLoading(true)
    try {
      await api.post('/wifi/login', { password: values.password })
      message.success('校园网登录成功')
      form.resetFields()
      onSuccess()
      onClose()
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登录失败'
      message.error(detail)
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
        登录后可查看校园网余额和流量使用情况。
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
        <Form.Item style={{ marginBottom: 0 }}>
          <Button type="primary" htmlType="submit" loading={loading} block>
            登录
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  )
}

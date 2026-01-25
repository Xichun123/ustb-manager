import { useEffect, useState, useRef } from 'react'
import { Card, Image, Spin, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useSSE } from '../hooks/useSSE'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const { Text } = Typography

export function QRLogin() {
  const [qrImage, setQrImage] = useState<string>('')
  const [ready, setReady] = useState(false)
  const [loginSuccess, setLoginSuccess] = useState(false)
  const navigate = useNavigate()
  const { setAuthenticated } = useAuth()
  const initRef = useRef(false)
  const cancelledRef = useRef(false)

  useEffect(() => {
    // 在任何检查之前重置cancelled状态
    cancelledRef.current = false
    if (loginSuccess) return
    // 防止StrictMode下重复调用
    if (initRef.current) return
    initRef.current = true

    const init = async () => {
      try {
        const { data } = await api.post('/auth/qr/init')
        if (!cancelledRef.current) {
          setQrImage(data.qr_image)
          setReady(true)
        }
      } catch (error: unknown) {
        if (!cancelledRef.current) {
          // 409 表示已登录，跳转到 dashboard
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { status?: number } }
            if (axiosError.response?.status === 409) {
              setAuthenticated(true)
              navigate('/dashboard', { replace: true })
              return
            }
          }
          message.error('QR码加载失败')
        }
      }
    }
    init()

    return () => { cancelledRef.current = true }
  }, [loginSuccess])

  const { data: statusData } = useSSE(ready && !loginSuccess ? '/api/auth/qr/status' : null)

  useEffect(() => {
    if (!statusData || loginSuccess) return
    if (statusData.status === 'scanned') {
      message.info('已扫码，等待确认...')
    } else if (statusData.status === 'success') {
      setLoginSuccess(true)
      // 调用 complete 端点完成登录流程，确保 cookie 正确设置
      api.post('/auth/qr/complete')
        .then(() => {
          setAuthenticated(true)
          message.success('登录成功')
          navigate('/dashboard', { replace: true })
        })
        .catch((error) => {
          message.error('登录完成失败，请重试')
          console.error('Complete login failed:', error)
        })
    } else if (statusData.status === 'expired') {
      message.warning('二维码已过期，请刷新')
    } else if (statusData.status === 'error') {
      message.error(statusData.message || '登录失败，请重试')
    }
  }, [statusData, navigate, setAuthenticated, loginSuccess])

  return (
    <div style={{ textAlign: 'center' }}>
      <Card title="微信扫码登录" bordered={false} style={{ width: 300, margin: '0 auto' }}>
        {qrImage ? (
          <Image src={qrImage} alt="登录二维码" width={200} preview={false} />
        ) : (
          <Spin tip="加载中..." />
        )}
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">请使用微信扫描二维码</Text>
        </div>
      </Card>
    </div>
  )
}
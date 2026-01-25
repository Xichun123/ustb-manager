import { ReactNode, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Spin, Layout } from 'antd'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'

interface WifiRouteProps {
  children: ReactNode
}

export function WifiRoute({ children }: WifiRouteProps) {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [standaloneChecking, setStandaloneChecking] = useState(true)
  const [hasStandaloneAccess, setHasStandaloneAccess] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const checkStandalone = async () => {
      try {
        const res = await api.get('/wifi/standalone-status')
        // 如果有学号（不管是否已登录），都允许访问
        if (res.data.student_id) {
          setHasStandaloneAccess(true)
        }
      } catch {
        // 忽略错误
      } finally {
        setStandaloneChecking(false)
      }
    }
    checkStandalone()
  }, [])

  // 等待两个检查都完成
  if (authLoading || standaloneChecking) {
    return (
      <Layout style={{ minHeight: '100vh', justifyContent: 'center', alignItems: 'center' }}>
        <Spin size="large" tip="验证登录状态..." />
      </Layout>
    )
  }

  // 已登录教务系统或有独立模式访问权限
  if (isAuthenticated || hasStandaloneAccess) {
    return <>{children}</>
  }

  // 未登录，重定向到独立登录页面
  return <Navigate to="/wifi-standalone" state={{ from: location }} replace />
}

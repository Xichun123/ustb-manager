import { request, get, post } from './api'
import { clearAll, setSessionId, setUserInfo } from '../utils/storage'

const app = getApp<IAppOption>()
let authFlowVersion = 0

function getErrorMessage(data: any, fallback: string): string {
  if (!data) {
    return fallback
  }
  if (typeof data === 'string' && data) {
    return data
  }
  if (typeof data.detail === 'string' && data.detail) {
    return data.detail
  }
  if (typeof data.message === 'string' && data.message) {
    return data.message
  }
  return fallback
}

function beginAuthFlow(): number {
  authFlowVersion += 1
  app.globalData.isAuthenticated = false
  app.globalData.authBootstrapInProgress = true
  return authFlowVersion
}

function adoptSessionIfLatest(version: number, sessionId?: string): void {
  if (!sessionId) {
    return
  }
  if (version === authFlowVersion) {
    setSessionId(sessionId)
  }
}

/** Check authentication status */
export async function checkAuthStatus(): Promise<{ authenticated: boolean }> {
  const res = await request<{ authenticated: boolean }>({
    url: '/api/auth/status',
    method: 'GET',
    skipAuth: true,
  })
  return res.data
}

/** Initialize QR code login */
export async function initQRLogin(): Promise<{ session_id: string; qr_image: string }> {
  const flowVersion = beginAuthFlow()
  const res = await request<{ session_id: string; qr_image: string }>({
    url: '/api/auth/qr/init',
    method: 'POST',
    skipAuth: true,
  })
  if (res.statusCode === 200) {
    adoptSessionIfLatest(flowVersion, res.data.session_id)
    return res.data
  }
  if (res.statusCode === 409) {
    throw new Error('already_authenticated')
  }
  throw new Error('初始化二维码失败')
}

/** Poll QR code scan status */
export async function pollQRStatus(): Promise<{ status: string; message?: string }> {
  const res = await request<{ status: string; message?: string }>({
    url: '/api/auth/qr/poll',
    method: 'GET',
    skipAuth: true,
  })

  if (res.statusCode === 200) {
    return res.data
  }

  if (res.statusCode === 401) {
    throw new Error('二维码会话已失效，请刷新二维码')
  }

  throw new Error('二维码状态获取失败')
}

/** Complete QR login */
export async function completeQRLogin(): Promise<{ status: string; session_id?: string }> {
  const flowVersion = beginAuthFlow()
  const res = await request<{ status: string; session_id?: string }>({
    url: '/api/auth/qr/complete',
    method: 'POST',
    skipAuth: true,
  })

  if (res.statusCode !== 200) {
    if (res.statusCode === 401) {
      throw new Error('二维码已确认，但登录会话未完成，请重试')
    }
    throw new Error('完成扫码登录失败')
  }

  adoptSessionIfLatest(flowVersion, res.data.session_id)
  app.globalData.authBootstrapInProgress = false
  return res.data
}

/** Initialize SMS login */
export async function initSMSLogin(): Promise<{ session_id: string }> {
  const flowVersion = beginAuthFlow()
  const res = await request<{ session_id: string }>({
    url: '/api/auth/sms/init',
    method: 'POST',
    skipAuth: true,
  })
  if (res.statusCode === 200) {
    adoptSessionIfLatest(flowVersion, res.data.session_id)
    return res.data
  }
  throw new Error('初始化SMS登录失败')
}

/** Send SMS verification code */
export async function sendSMS(phone: string): Promise<void> {
  const res = await request({
    url: '/api/auth/sms/send',
    method: 'POST',
    data: { phone },
    skipAuth: true,
  })
  if (res.statusCode === 429) {
    throw new Error(getErrorMessage(res.data, '发送过于频繁，请稍后再试'))
  }
  if (res.statusCode !== 200) {
    throw new Error(getErrorMessage(res.data, '发送验证码失败'))
  }
}

/** Verify SMS code */
export async function verifySMS(phone: string, code: string): Promise<void> {
  const flowVersion = beginAuthFlow()
  const res = await request<{ status: string; session_id?: string }>({
    url: '/api/auth/sms/verify',
    method: 'POST',
    data: { phone, code },
    skipAuth: true,
  })
  if (res.statusCode !== 200) {
    throw new Error(getErrorMessage(res.data, '验证码错误或已过期'))
  }
  adoptSessionIfLatest(flowVersion, res.data.session_id)
  app.globalData.isAuthenticated = true
  app.globalData.authBootstrapInProgress = false
}

/** Cookie login */
export async function cookieLogin(cookies: string): Promise<{ student_id: string; student_name: string; session_id?: string }> {
  const flowVersion = beginAuthFlow()
  const res = await request<{ status: string; student_id: string; student_name: string; session_id?: string }>({
    url: '/api/auth/cookie/login',
    method: 'POST',
    data: { cookies },
    skipAuth: true,
  })
  if (res.statusCode === 200) {
    adoptSessionIfLatest(flowVersion, res.data.session_id)
    app.globalData.isAuthenticated = true
    app.globalData.authBootstrapInProgress = false
    return res.data
  }
  if (res.statusCode === 400) {
    throw new Error('Cookie 格式无效')
  }
  throw new Error('Cookie 无效或已过期')
}

/** Logout */
export async function logout(): Promise<void> {
  try {
    await post('/api/auth/logout')
  } finally {
    authFlowVersion += 1
    app.globalData.isAuthenticated = false
    app.globalData.authBootstrapInProgress = false
    app.globalData.userInfo = null
    clearAll()
  }
}

/** Fetch and cache user info after login */
export async function fetchAndCacheUserInfo(): Promise<void> {
  try {
    const info = await get<any>('/api/grades/student-info')
    const userInfo = {
      name: info.XM || '',
      student_id: info.XH || '',
      dept: info.YXMC || '',
      major: info.ZYMC || '',
      class_name: info.BJMC || '',
    }
    setUserInfo(userInfo)
    app.globalData.userInfo = userInfo
  } catch (_e) {
    // Non-critical, user info will be fetched when needed
  }
}

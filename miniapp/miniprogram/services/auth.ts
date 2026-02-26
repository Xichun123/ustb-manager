import { request, get, post } from './api'
import { setSessionId, setUserInfo, removeSessionId, removeUserInfo, clearAll } from '../utils/storage'

const app = getApp<IAppOption>()

/** Check authentication status */
export async function checkAuthStatus(): Promise<{ authenticated: boolean }> {
  return get('/api/auth/status')
}

/** Initialize QR code login */
export async function initQRLogin(): Promise<{ session_id: string; qr_image: string }> {
  const res = await request<{ session_id: string; qr_image: string }>({
    url: '/api/auth/qr/init',
    method: 'POST',
    skipAuth: true,
  })
  if (res.statusCode === 200) {
    setSessionId(res.data.session_id)
    return res.data
  }
  if (res.statusCode === 409) {
    throw new Error('already_authenticated')
  }
  throw new Error('初始化二维码失败')
}

/** Poll QR code scan status */
export async function pollQRStatus(): Promise<{ status: string }> {
  return get('/api/auth/qr/poll')
}

/** Complete QR login */
export async function completeQRLogin(): Promise<{ status: string }> {
  return post('/api/auth/qr/complete')
}

/** Initialize SMS login */
export async function initSMSLogin(): Promise<{ session_id: string }> {
  const res = await request<{ session_id: string }>({
    url: '/api/auth/sms/init',
    method: 'POST',
    skipAuth: true,
  })
  if (res.statusCode === 200) {
    setSessionId(res.data.session_id)
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
  })
  if (res.statusCode === 429) {
    throw new Error('发送过于频繁，请稍后再试')
  }
  if (res.statusCode !== 200) {
    throw new Error('发送验证码失败')
  }
}

/** Verify SMS code */
export async function verifySMS(phone: string, code: string): Promise<void> {
  const res = await request({
    url: '/api/auth/sms/verify',
    method: 'POST',
    data: { phone, code },
  })
  if (res.statusCode !== 200) {
    throw new Error('验证码错误或已过期')
  }
  app.globalData.isAuthenticated = true
}

/** Cookie login */
export async function cookieLogin(cookies: string): Promise<{ student_id: string; student_name: string }> {
  const res = await request<{ status: string; student_id: string; student_name: string }>({
    url: '/api/auth/cookie/login',
    method: 'POST',
    data: { cookies },
    skipAuth: true,
  })
  if (res.statusCode === 200) {
    app.globalData.isAuthenticated = true
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
    app.globalData.isAuthenticated = false
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

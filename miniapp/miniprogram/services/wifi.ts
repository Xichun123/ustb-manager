import { getWifiStudentId, setWifiStudentId } from '../utils/storage'
import { request } from './api'

export type WifiLoginMode = 'authenticated' | 'standalone'

interface WifiStatusResponse {
  logged_in: boolean
  has_credential: boolean
}

interface WifiStandaloneStatusResponse {
  logged_in: boolean
  student_id: string | null
  has_credential: boolean
}

interface WifiApiError {
  detail?: string
  message?: string
}

export interface WifiResolvedStatus {
  logged_in: boolean
  has_credential: boolean
  student_id: string | null
  mode: WifiLoginMode
}

export interface WifiLoginChallenge {
  challenge_token: string
  captcha_image: string
  expires_in: number
  mode?: 'direct' | 'webvpn'
}

export interface WifiFlowResponse {
  account: string
  balance: number
  used_flow: number
  used_flow_v4?: number
  used_flow_v6?: number
  available_flow: number
  status: string
  package: string
  expire_date: string
  online_devices: any[]
  recent_history: any[]
  update_time: string
}

function getErrorDetail(data: WifiApiError | string | null | undefined, fallback: string): string {
  if (typeof data === 'string' && data) {
    return data
  }
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string' && data.detail) {
      return data.detail
    }
    if (typeof data.message === 'string' && data.message) {
      return data.message
    }
  }
  return fallback
}

export async function getWifiStatus(): Promise<WifiResolvedStatus> {
  const authRes = await request<WifiStatusResponse>({
    url: '/api/wifi/status',
    method: 'GET',
    isWifi: true,
  })

  if (authRes.statusCode === 200) {
    return {
      ...authRes.data,
      student_id: getWifiStudentId() || null,
      mode: 'authenticated',
    }
  }

  if (authRes.statusCode !== 401) {
    throw new Error(getErrorDetail(authRes.data as WifiApiError, '获取校园网状态失败'))
  }

  const standaloneRes = await request<WifiStandaloneStatusResponse>({
    url: '/api/wifi/standalone-status',
    method: 'GET',
    isWifi: true,
    skipAuth: true,
  })

  if (standaloneRes.statusCode !== 200) {
    throw new Error(getErrorDetail(standaloneRes.data as WifiApiError, '获取校园网状态失败'))
  }

  if (standaloneRes.data.student_id) {
    setWifiStudentId(standaloneRes.data.student_id)
  }

  return {
    ...standaloneRes.data,
    student_id: standaloneRes.data.student_id || getWifiStudentId() || null,
    mode: 'standalone',
  }
}

export async function getWifiFlow(): Promise<WifiFlowResponse> {
  const res = await request<WifiFlowResponse>({
    url: '/api/wifi/flow',
    method: 'GET',
    isWifi: true,
  })

  if (res.statusCode >= 200 && res.statusCode < 300) {
    return res.data
  }

  throw new Error(getErrorDetail(res.data as WifiApiError, '加载流量信息失败'))
}

export async function getWifiDevices(): Promise<{ total: number; devices: any[] }> {
  const res = await request<{ total: number; devices: any[] }>({
    url: '/api/wifi/devices',
    method: 'GET',
    isWifi: true,
  })

  if (res.statusCode >= 200 && res.statusCode < 300) {
    return res.data
  }

  throw new Error(getErrorDetail(res.data as WifiApiError, '加载设备列表失败'))
}

export async function getWifiPayments(): Promise<{ payments: any[] }> {
  const res = await request<{ payments: any[] }>({
    url: '/api/wifi/payments',
    method: 'GET',
    isWifi: true,
  })

  if (res.statusCode >= 200 && res.statusCode < 300) {
    return res.data
  }

  throw new Error(getErrorDetail(res.data as WifiApiError, '加载充值记录失败'))
}

export async function createWifiLoginChallenge(payload: { student_id?: string; password: string }): Promise<WifiLoginChallenge> {
  const res = await request<WifiLoginChallenge>({
    url: '/api/wifi/login/challenge',
    method: 'POST',
    data: payload,
    isWifi: true,
  })

  if (res.statusCode >= 200 && res.statusCode < 300) {
    return res.data
  }

  throw new Error(getErrorDetail(res.data as WifiApiError, '获取验证码失败'))
}

export async function loginWifi(
  mode: WifiLoginMode,
  payload: {
    student_id?: string
    password: string
    challenge_token: string
    captcha_code: string
  },
): Promise<void> {
  const url = mode === 'standalone' ? '/api/wifi/standalone-login' : '/api/wifi/login'
  const res = await request<{ student_id?: string }>({
    url,
    method: 'POST',
    data: payload,
    isWifi: true,
  })

  if (res.statusCode >= 200 && res.statusCode < 300) {
    if (mode === 'standalone' && (res.data.student_id || payload.student_id)) {
      setWifiStudentId(res.data.student_id || payload.student_id || '')
    }
    return
  }

  throw new Error(getErrorDetail(res.data as WifiApiError, '登录失败'))
}

export async function unbindWifiMac(macAddress: string): Promise<void> {
  const res = await request({
    url: '/api/wifi/unbind-mac',
    method: 'POST',
    data: { mac_address: macAddress },
    isWifi: true,
  })

  if (res.statusCode >= 200 && res.statusCode < 300) {
    return
  }

  throw new Error(getErrorDetail(res.data as WifiApiError, '解绑失败'))
}

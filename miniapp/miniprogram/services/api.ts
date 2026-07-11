import {
  clearAll,
  getSessionId,
  getWifiStudentId,
  setWifiStudentId,
} from '../utils/storage'

const app = getApp<IAppOption>()

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
  header?: Record<string, string>
  skipAuth?: boolean
  isWifi?: boolean
}

interface ApiResponse<T = any> {
  data: T
  statusCode: number
  header: Record<string, string>
}

interface ErrorEnvelope {
  error?: {
    code?: string
    message?: string
    retryable?: boolean
    request_id?: string
  }
  detail?: string
}

export class ApiError extends Error {
  code: string
  retryable: boolean
  requestId: string
  statusCode: number

  constructor(statusCode: number, data: ErrorEnvelope) {
    super(data.error?.message || data.detail || `请求失败: ${statusCode}`)
    this.name = 'ApiError'
    this.code = data.error?.code || 'REQUEST_ERROR'
    this.retryable = !!data.error?.retryable
    this.requestId = data.error?.request_id || ''
    this.statusCode = statusCode
  }
}

function apiError(statusCode: number, data: unknown): ApiError {
  const envelope = data && typeof data === 'object' ? data as ErrorEnvelope : {}
  return new ApiError(statusCode, envelope)
}

function extractCookieValue(header: Record<string, string>, name: string): string | null {
  const setCookie = header['Set-Cookie'] || header['set-cookie'] || ''
  const cookies = Array.isArray(setCookie) ? setCookie : [setCookie]
  for (const cookie of cookies) {
    const match = cookie.match(new RegExp(`${name}=([^;]+)`))
    if (match) return match[1]
  }
  return null
}

/** Core request function wrapping wx.request as Promise */
export function request<T = any>(options: RequestOptions): Promise<ApiResponse<T>> {
  const {
    url,
    method = 'GET',
    data,
    header = {},
    skipAuth = false,
    isWifi = false,
  } = options

  const sessionId = getSessionId()
  const wifiStudentId = getWifiStudentId()
  const cookieParts: string[] = []
  const existingCookie = header['Cookie'] || header['cookie']

  if (existingCookie) {
    cookieParts.push(existingCookie)
  }
  if (!isWifi) {
    header['X-Auth-Transport'] = 'bearer'
    if (sessionId) {
      header.Authorization = `Bearer ${sessionId}`
    }
  }
  if (wifiStudentId) {
    cookieParts.push(`wifi_student_id=${wifiStudentId}`)
  }
  if (cookieParts.length > 0) {
    header['Cookie'] = cookieParts.join('; ')
  }

  if (method === 'POST' && !header['Content-Type']) {
    header['Content-Type'] = 'application/json'
  }

  const fullUrl = url.startsWith('http') ? url : `${app.globalData.baseUrl}${url}`
  const isAuthStatusRequest = url.indexOf('/api/auth/status') !== -1 || url.indexOf('/auth/status') !== -1

  if (!skipAuth && !isWifi && app.globalData.authBootstrapInProgress && !isAuthStatusRequest) {
    return Promise.reject(new Error('认证准备中'))
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: fullUrl,
      method,
      data,
      header,
      success: (res: any) => {
        const newWifiStudentId = extractCookieValue(res.header || {}, 'wifi_student_id')
        if (newWifiStudentId) {
          setWifiStudentId(newWifiStudentId)
        }

        // Ignore late responses from an old session so they don't wipe a newer login flow.
        const sessionStillCurrent = sessionId
          ? getSessionId() === sessionId
          : !getSessionId()

        // Handle 401
        if (res.statusCode === 401 && !isWifi && !skipAuth) {
          if (sessionStillCurrent && !app.globalData.authBootstrapInProgress) {
            app.globalData.isAuthenticated = false
            app.globalData.authBootstrapInProgress = false
            app.globalData.userInfo = null
            clearAll()
            wx.redirectTo({ url: '/pages/login/login' })
          }
          reject(new Error('未登录或登录已过期'))
          return
        }

        resolve({
          data: res.data,
          statusCode: res.statusCode,
          header: res.header || {},
        })
      },
      fail: (err: any) => {
        reject(new Error(err.errMsg || '网络请求失败'))
      },
    })
  })
}

/** GET request */
export function get<T = any>(url: string, params?: Record<string, any>, options?: Partial<RequestOptions>): Promise<T> {
  let fullUrl = url
  if (params) {
    const qs = Object.entries(params)
      .filter(([_, v]) => v !== undefined && v !== null && v !== '')
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&')
    if (qs) fullUrl += `?${qs}`
  }

  return request<T>({ url: fullUrl, method: 'GET', ...options }).then(res => {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data
    }
    throw apiError(res.statusCode, res.data)
  })
}

/** POST request */
export function post<T = any>(url: string, data?: any, options?: Partial<RequestOptions>): Promise<T> {
  return request<T>({ url, method: 'POST', data, ...options }).then(res => {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data
    }
    throw apiError(res.statusCode, res.data)
  })
}

/** DELETE request */
export function del<T = any>(url: string, data?: any, options?: Partial<RequestOptions>): Promise<T> {
  return request<T>({ url, method: 'DELETE', data, ...options }).then(res => {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data
    }
    throw apiError(res.statusCode, res.data)
  })
}

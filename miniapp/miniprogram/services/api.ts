import { getSessionId, setSessionId } from '../utils/storage'

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

/** Extract session_id from Set-Cookie header */
function extractSessionId(header: Record<string, string>): string | null {
  const setCookie = header['Set-Cookie'] || header['set-cookie'] || ''
  const cookies = Array.isArray(setCookie) ? setCookie : [setCookie]
  for (const cookie of cookies) {
    const match = cookie.match(/ustb_sid=([^;]+)/)
    if (match) return match[1]
  }
  return null
}

/** Core request function wrapping wx.request as Promise */
export function request<T = any>(options: RequestOptions): Promise<ApiResponse<T>> {
  const { url, method = 'GET', data, header = {}, skipAuth = false, isWifi = false } = options

  const sessionId = getSessionId()
  if (sessionId && !skipAuth) {
    header['Cookie'] = `ustb_sid=${sessionId}`
  }

  if (method === 'POST' && !header['Content-Type']) {
    header['Content-Type'] = 'application/json'
  }

  const fullUrl = url.startsWith('http') ? url : `${app.globalData.baseUrl}${url}`

  return new Promise((resolve, reject) => {
    wx.request({
      url: fullUrl,
      method,
      data,
      header,
      success: (res: any) => {
        // Save session from Set-Cookie
        const newSid = extractSessionId(res.header || {})
        if (newSid) {
          setSessionId(newSid)
        }

        // Handle 401
        if (res.statusCode === 401 && !isWifi) {
          app.globalData.isAuthenticated = false
          wx.redirectTo({ url: '/pages/login/login' })
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
    throw new Error(`请求失败: ${res.statusCode}`)
  })
}

/** POST request */
export function post<T = any>(url: string, data?: any, options?: Partial<RequestOptions>): Promise<T> {
  return request<T>({ url, method: 'POST', data, ...options }).then(res => {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.data
    }
    throw new Error(`请求失败: ${res.statusCode}`)
  })
}

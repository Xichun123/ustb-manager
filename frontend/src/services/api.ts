import axios from 'axios'

interface ErrorEnvelope {
  error?: {
    code?: string
    message?: string
    retryable?: boolean
    request_id?: string
  }
}

export const AUTH_REQUIRED_EVENT = 'ustb:auth-required'

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError<ErrorEnvelope>(error)) return fallback
  return error.response?.data?.error?.message || fallback
}

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器：把项目会话失效交给认证状态机处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const requestUrl = error.config?.url || ''
      const isWifiRequest = requestUrl.startsWith('/wifi/') || requestUrl.startsWith('wifi/')

      // 校园网接口 401 由页面自行处理
      if (!isWifiRequest) {
        window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT))
      }
    }
    return Promise.reject(error)
  }
)

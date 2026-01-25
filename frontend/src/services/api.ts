import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// 响应拦截器：处理401错误自动跳转登录页
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const requestUrl = error.config?.url || ''
      const isWifiRequest = requestUrl.startsWith('/wifi/') || requestUrl.startsWith('wifi/')

      // 避免在登录页重复跳转；校园网接口 401 由页面自行处理
      if (!isWifiRequest && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

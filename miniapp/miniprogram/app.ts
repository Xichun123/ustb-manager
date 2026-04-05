// app.ts
import { API_BASE_URL } from './config/api'
import { clearAll, getSessionId, getUserInfo, hasSessionId } from './utils/storage'

function isBootstrapState(state?: string): boolean {
  return state === 'qr_ready'
    || state === 'sms_ready'
    || state === 'sms_sent'
    || state === 'confirmed'
}

function checkAuth(app: WechatMiniprogram.App.Instance<IAppOption>) {
  const sessionId = getSessionId()
  if (!sessionId) {
    app.globalData.isAuthenticated = false
    app.globalData.authBootstrapInProgress = false
    return
  }

  wx.request({
    url: `${app.globalData.baseUrl}/api/auth/status`,
    header: {
      Cookie: `ustb_sid=${sessionId}`,
    },
    success: (res: any) => {
      if (res.statusCode === 200 && res.data && res.data.authenticated) {
        app.globalData.isAuthenticated = true
        app.globalData.authBootstrapInProgress = false
      } else if (res.statusCode === 200 && res.data && isBootstrapState(res.data.state)) {
        app.globalData.isAuthenticated = false
        app.globalData.authBootstrapInProgress = true
      } else {
        app.globalData.isAuthenticated = false
        app.globalData.authBootstrapInProgress = false
        app.globalData.userInfo = null
        clearAll()
      }
    },
    fail: () => {
      // Keep the locally cached session optimistic; a later 401 will clear it.
      app.globalData.isAuthenticated = hasSessionId()
      app.globalData.authBootstrapInProgress = false
    },
  })
}

App<IAppOption>({
  globalData: {
    // Defer protected page loading until /auth/status confirms the session is active.
    isAuthenticated: false,
    authBootstrapInProgress: hasSessionId(),
    userInfo: getUserInfo(),
    baseUrl: API_BASE_URL,
  },

  onLaunch() {
    checkAuth(this)
  },
})

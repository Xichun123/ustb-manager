// app.ts
import { API_BASE_URL } from './config/api'
import { getSessionId, hasSessionId, removeSessionId, removeUserInfo } from './utils/storage'

function checkAuth(app: WechatMiniprogram.App.Instance<IAppOption>) {
  const sessionId = getSessionId()
  if (!sessionId) {
    app.globalData.isAuthenticated = false
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
      } else {
        app.globalData.isAuthenticated = false
        removeSessionId()
        removeUserInfo()
      }
    },
    fail: () => {
      // Keep the locally cached session optimistic; a later 401 will clear it.
      app.globalData.isAuthenticated = hasSessionId()
    },
  })
}

App<IAppOption>({
  globalData: {
    isAuthenticated: hasSessionId(),
    userInfo: null,
    baseUrl: API_BASE_URL,
  },

  onLaunch() {
    checkAuth(this)
  },
})

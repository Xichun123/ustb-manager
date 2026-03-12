// app.ts
import { API_BASE_URL } from './config/api'
import { clearAll, getSessionId, getUserInfo, hasSessionId } from './utils/storage'

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
        app.globalData.userInfo = null
        clearAll()
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
    userInfo: getUserInfo(),
    baseUrl: API_BASE_URL,
  },

  onLaunch() {
    checkAuth(this)
  },
})

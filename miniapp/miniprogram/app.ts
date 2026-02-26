// app.ts
import { getSessionId } from './utils/storage'

App<IAppOption>({
  globalData: {
    isAuthenticated: false,
    userInfo: null,
    baseUrl: 'https://nike.050919.xyz',
  },

  onLaunch() {
    this.checkAuth()
  },

  checkAuth() {
    const sessionId = getSessionId()
    if (!sessionId) {
      this.globalData.isAuthenticated = false
      return
    }

    wx.request({
      url: `${this.globalData.baseUrl}/api/auth/status`,
      header: {
        Cookie: `ustb_sid=${sessionId}`,
      },
      success: (res: any) => {
        if (res.statusCode === 200 && res.data && res.data.authenticated) {
          this.globalData.isAuthenticated = true
        } else {
          this.globalData.isAuthenticated = false
        }
      },
      fail: () => {
        this.globalData.isAuthenticated = false
      },
    })
  },
})

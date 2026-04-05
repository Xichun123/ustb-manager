import {
  checkAuthStatus,
  initQRLogin,
  pollQRStatus,
  completeQRLogin,
  initSMSLogin,
  sendSMS,
  verifySMS,
  cookieLogin,
  fetchAndCacheUserInfo,
} from '../../services/auth'

const app = getApp<IAppOption>()

Page({
  data: {
    activeTab: 'qr' as 'qr' | 'sms' | 'cookie',
    loading: false,
    // SMS
    phone: '',
    code: '',
    smsInited: false,
    smsSending: false,
    countdown: 0,
    // Cookie
    cookieStr: '',
    // QR
    qrImage: '',
    qrStatus: '',
    qrPolling: false,
  },

  _countdownTimer: null as any,
  _pollTimer: null as any,
  _pollingInFlight: false,
  _completingQR: false,

  onUnload() {
    if (this._countdownTimer) clearInterval(this._countdownTimer)
    this.stopPolling()
  },

  onLoad() {
    // 默认扫码登录，自动加载二维码
    this.initQR()
  },

  // Tab switching
  switchTab(e: any) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    if (tab !== 'qr') {
      this.stopPolling()
      return
    }
    if (!this.data.qrImage) {
      this.initQR()
      return
    }
    if (!this.data.qrPolling && this.data.qrStatus !== '二维码已过期，请刷新' && this.data.qrStatus !== '登录成功！') {
      this.startPolling()
    }
  },

  // ===== SMS Login =====
  onPhoneInput(e: any) {
    this.setData({ phone: e.detail.value })
  },

  onCodeInput(e: any) {
    this.setData({ code: e.detail.value })
  },

  async sendCode() {
    const { phone } = this.data
    if (!phone || phone.length !== 11) {
      wx.showToast({ title: '请输入正确的手机号', icon: 'none' })
      return
    }

    try {
      this.setData({ smsSending: true })

      const ensureSmsSession = async (force = false) => {
        if (!force && this.data.smsInited) {
          return
        }
        await initSMSLogin()
        this.setData({ smsInited: true })
      }

      await ensureSmsSession()

      try {
        await sendSMS(phone)
      } catch (err: any) {
        if (!err || err.message !== '未登录或登录已过期') {
          throw err
        }
        await ensureSmsSession(true)
        await sendSMS(phone)
      }

      wx.showToast({ title: '验证码已发送', icon: 'success' })

      // Start countdown
      this.setData({ countdown: 60 })
      this._countdownTimer = setInterval(() => {
        const c = this.data.countdown - 1
        if (c <= 0) {
          clearInterval(this._countdownTimer)
          this.setData({ countdown: 0 })
        } else {
          this.setData({ countdown: c })
        }
      }, 1000)
    } catch (err: any) {
      wx.showToast({ title: err.message || '发送失败', icon: 'none' })
    } finally {
      this.setData({ smsSending: false })
    }
  },

  async smsLogin() {
    const { phone, code } = this.data
    if (!phone || !code) {
      wx.showToast({ title: '请填写完整信息', icon: 'none' })
      return
    }

    try {
      this.setData({ loading: true })
      await verifySMS(phone, code)
      await this.onLoginSuccess()
    } catch (err: any) {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // ===== Cookie Login =====
  onCookieInput(e: any) {
    this.setData({ cookieStr: e.detail.value })
  },

  async doCookieLogin() {
    const { cookieStr } = this.data
    if (!cookieStr.trim()) {
      wx.showToast({ title: '请输入Cookie', icon: 'none' })
      return
    }

    try {
      this.setData({ loading: true })
      await cookieLogin(cookieStr)
      await this.onLoginSuccess()
    } catch (err: any) {
      wx.showToast({ title: err.message || '登录失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  // ===== QR Login =====
  async initQR() {
    try {
      this.stopPolling()
      this._completingQR = false
      this.setData({ loading: true, qrStatus: '加载中...' })
      const data = await initQRLogin()
      this.setData({
        qrImage: data.qr_image,
        qrStatus: '请使用微信扫描二维码',
        qrPolling: false,
      })
      this.startPolling()
    } catch (err: any) {
      if (err.message === 'already_authenticated') {
        await this.onLoginSuccess()
        return
      }
      this.setData({ qrStatus: '加载二维码失败' })
      wx.showToast({ title: err.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  startPolling() {
    this.stopPolling()
    this.setData({ qrPolling: true })
    const pollOnce = async () => {
      if (!this.data.qrPolling || this.data.activeTab !== 'qr') {
        return
      }
      if (this._pollingInFlight) {
        this._pollTimer = setTimeout(pollOnce, 1200)
        return
      }

      this._pollingInFlight = true
      try {
        const res = await pollQRStatus()
        switch (res.status) {
          case 'waiting':
            this.setData({ qrStatus: '等待扫描...' })
            break
          case 'scanned':
            this.setData({ qrStatus: '已扫描，请在手机上确认' })
            break
          case 'success':
            this.setData({ qrPolling: false, qrStatus: '登录成功！' })
            await this.handleQRSuccess()
            return
          case 'expired':
            this.setData({ qrPolling: false, qrStatus: '二维码已过期，请刷新' })
            return
          case 'error':
            this.setData({
              qrPolling: false,
              qrStatus: res.message || '扫码登录失败，请刷新二维码重试',
            })
            wx.showToast({ title: '扫码登录失败', icon: 'none' })
            return
          default:
            this.setData({ qrStatus: '等待扫描...' })
            break
        }
      } catch (err: any) {
        const message = err && err.message ? err.message : '扫码状态获取失败'
        console.error('QR poll failed:', err)
        if (message.indexOf('二维码会话已失效') !== -1) {
          this.setData({ qrPolling: false, qrStatus: message })
          wx.showToast({ title: '二维码已失效', icon: 'none' })
          return
        }
        this.setData({ qrStatus: message })
      } finally {
        this._pollingInFlight = false
      }

      if (this.data.qrPolling && this.data.activeTab === 'qr') {
        this._pollTimer = setTimeout(pollOnce, 2000)
      }
    }

    pollOnce()
  },

  stopPolling() {
    if (this._pollTimer) {
      clearTimeout(this._pollTimer)
      this._pollTimer = null
    }
    this._pollingInFlight = false
    if (this.data.qrPolling) {
      this.setData({ qrPolling: false })
    }
  },

  async handleQRSuccess() {
    if (this._completingQR) {
      return
    }

    this._completingQR = true
    try {
      await completeQRLogin()
    } catch (err: any) {
      console.error('Complete QR login failed:', err)
      const authStatus = await checkAuthStatus().catch(() => null)
      if (!authStatus || !authStatus.authenticated) {
        this.setData({
          qrPolling: false,
          qrStatus: err && err.message ? err.message : '登录完成失败，请刷新二维码重试',
        })
        wx.showToast({ title: '扫码完成失败', icon: 'none' })
        return
      }
    }

    await this.onLoginSuccess()
  },

  refreshQR() {
    this.stopPolling()
    this._completingQR = false
    this.setData({ qrImage: '', qrStatus: '', qrPolling: false })
    this.initQR()
  },

  // ===== Common =====
  async onLoginSuccess() {
    app.globalData.isAuthenticated = true
    app.globalData.authBootstrapInProgress = false
    await fetchAndCacheUserInfo()
    await new Promise<void>((resolve) => {
      wx.switchTab({
        url: '/pages/index/index',
        success: () => resolve(),
        fail: (err) => {
          console.error('switchTab after login failed:', err)
          wx.reLaunch({
            url: '/pages/index/index',
            complete: () => resolve(),
          })
        },
      })
    })
  },

  goWifiOnly() {
    wx.switchTab({ url: '/pages/wifi/wifi' })
  },
})

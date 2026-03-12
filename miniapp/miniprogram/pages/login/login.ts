import { initQRLogin, pollQRStatus, completeQRLogin, initSMSLogin, sendSMS, verifySMS, cookieLogin, fetchAndCacheUserInfo } from '../../services/auth'

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

  onUnload() {
    if (this._countdownTimer) clearInterval(this._countdownTimer)
    if (this._pollTimer) clearInterval(this._pollTimer)
  },

  onLoad() {
    // 默认扫码登录，自动加载二维码
    this.initQR()
  },

  // Tab switching
  switchTab(e: any) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
    if (tab === 'qr' && !this.data.qrImage) {
      this.initQR()
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

      if (!this.data.smsInited) {
        await initSMSLogin()
        this.setData({ smsInited: true })
      }

      await sendSMS(phone)
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
      this.setData({ loading: true, qrStatus: '加载中...' })
      const data = await initQRLogin()
      this.setData({ qrImage: data.qr_image, qrStatus: '请使用微信扫描二维码' })
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
    if (this._pollTimer) clearInterval(this._pollTimer)

    this.setData({ qrPolling: true })
    this._pollTimer = setInterval(async () => {
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
            clearInterval(this._pollTimer)
            this.setData({ qrPolling: false, qrStatus: '登录成功！' })
            await completeQRLogin()
            await this.onLoginSuccess()
            break
          case 'expired':
            clearInterval(this._pollTimer)
            this.setData({ qrPolling: false, qrStatus: '二维码已过期，请刷新' })
            break
        }
      } catch (_e) {
        // Polling error, continue
      }
    }, 2000)
  },

  refreshQR() {
    if (this._pollTimer) clearInterval(this._pollTimer)
    this.setData({ qrImage: '', qrStatus: '' })
    this.initQR()
  },

  // ===== Common =====
  async onLoginSuccess() {
    app.globalData.isAuthenticated = true
    await fetchAndCacheUserInfo()
    wx.switchTab({ url: '/pages/index/index' })
  },

  goWifiOnly() {
    wx.switchTab({ url: '/pages/wifi/wifi' })
  },
})

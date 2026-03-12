import {
  createWifiLoginChallenge,
  getWifiDevices,
  getWifiFlow,
  getWifiPayments,
  getWifiStatus,
  loginWifi,
  type WifiLoginMode,
  unbindWifiMac,
} from '../../services/wifi'
import { formatFlow, formatMoney } from '../../utils/util'

function createIconDataUrl(pathMarkup: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#4a8cff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${pathMarkup}</svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

const WIFI_ICON_ASSETS = {
  mobile: createIconDataUrl('<rect x="7" y="3.5" width="10" height="17" rx="2.2"/><path d="M11 17h2"/>'),
  desktop: createIconDataUrl('<rect x="4" y="5" width="16" height="10" rx="2"/><path d="M8 19h8"/><path d="M10 15v4"/><path d="M14 15v4"/>'),
  plug: createIconDataUrl('<path d="M9 4v6"/><path d="M15 4v6"/><path d="M8 10h8"/><path d="M12 10v8"/><path d="M10 18h4"/>'),
  card: createIconDataUrl('<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/><path d="M7 15h4"/>'),
}

const app = getApp<IAppOption>()

Component({
  data: {
    loading: true,
    loggedIn: false,
    loginMode: 'authenticated' as WifiLoginMode,
    wifiStudentId: '',
    wifiPassword: '',
    captchaCode: '',
    challengeToken: '',
    captchaImage: '',
    challengeMode: '' as '' | 'direct' | 'webvpn',
    challengeLoading: false,
    loginLoading: false,
    flow: null as any,
    flowDisplay: {
      balance: '--',
      usedFlow: '--',
      usedFlowV4: '--',
      usedFlowV6: '--',
      availableFlow: '--',
      status: '--',
      package: '--',
    },
    onlineDevices: [] as any[],
    devices: [] as any[],
    payments: [] as any[],
    activeSection: 'overview' as string,
    iconAssets: WIFI_ICON_ASSETS,
  },

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 3 })
      }
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 3 })
      }
      this.checkWifiStatus()
    },
  },

  methods: {
    resetChallenge(resetCaptchaCode = true) {
      this.setData({
        challengeToken: '',
        captchaImage: '',
        challengeMode: '',
        ...(resetCaptchaCode ? { captchaCode: '' } : {}),
      })
    },

    async checkWifiStatus() {
      this.setData({ loading: true })
      try {
        const status = await getWifiStatus()
        const authenticatedStudentId = app.globalData.userInfo
          ? app.globalData.userInfo.student_id
          : ''
        const fallbackStudentId =
          status.mode === 'authenticated'
            ? authenticatedStudentId
            : (status.student_id || '')

        this.setData({
          loggedIn: status.logged_in,
          loginMode: status.mode,
          wifiStudentId: fallbackStudentId,
        })

        if (status.logged_in) {
          await this.loadFlowInfo()
        } else {
          this.setData({
            flow: null,
            onlineDevices: [],
            devices: [],
            payments: [],
          })
        }
      } catch (_e) {
        this.setData({
          loggedIn: false,
          loginMode: app.globalData.isAuthenticated ? 'authenticated' : 'standalone',
        })
      } finally {
        this.setData({ loading: false })
      }
    },

    async loadFlowInfo() {
      try {
        const flow = await getWifiFlow()
        this.setData({
          flow,
          flowDisplay: {
            balance: formatMoney(Number(flow.balance || 0)),
            usedFlow: formatFlow(Number(flow.used_flow || 0)),
            usedFlowV4: formatFlow(Number(flow.used_flow_v4 || 0)),
            usedFlowV6: formatFlow(Number(flow.used_flow_v6 || 0)),
            availableFlow: formatFlow(Number(flow.available_flow || 0)),
            status: flow.status || '--',
            package: flow.package || '--',
          },
          onlineDevices: flow.online_devices || [],
        })
      } catch (err: any) {
        wx.showToast({ title: err.message || '加载流量信息失败', icon: 'none' })
      }
    },

    async loadDevices() {
      try {
        const res = await getWifiDevices()
        this.setData({ devices: res.devices || [] })
      } catch (err: any) {
        wx.showToast({ title: err.message || '加载设备列表失败', icon: 'none' })
      }
    },

    async loadPayments() {
      try {
        const res = await getWifiPayments()
        this.setData({ payments: res.payments || [] })
      } catch (err: any) {
        wx.showToast({ title: err.message || '加载充值记录失败', icon: 'none' })
      }
    },

    switchSection(e: any) {
      const section = e.currentTarget.dataset.section
      this.setData({ activeSection: section })
      if (section === 'devices' && this.data.devices.length === 0) {
        this.loadDevices()
      }
      if (section === 'payments' && this.data.payments.length === 0) {
        this.loadPayments()
      }
    },

    showLogin() {
      this.resetChallenge()
      const authenticatedStudentId = app.globalData.userInfo
        ? app.globalData.userInfo.student_id
        : this.data.wifiStudentId
      this.setData({
        wifiStudentId: this.data.loginMode === 'authenticated'
          ? authenticatedStudentId
          : this.data.wifiStudentId,
        wifiPassword: '',
      })
    },

    onStudentIdInput(e: any) {
      this.setData({ wifiStudentId: String(e.detail.value || '').trim() })
      this.resetChallenge()
    },

    onPasswordInput(e: any) {
      this.setData({ wifiPassword: e.detail.value })
      this.resetChallenge()
    },

    onCaptchaInput(e: any) {
      this.setData({ captchaCode: e.detail.value })
    },

    async loadChallenge(silent = false) {
      const { loginMode, wifiStudentId, wifiPassword } = this.data
      const trimmedStudentId = String(wifiStudentId || '').trim()

      if (loginMode === 'standalone' && !trimmedStudentId) {
        if (!silent) {
          wx.showToast({ title: '请输入学号', icon: 'none' })
        }
        return false
      }
      if (!wifiPassword) {
        if (!silent) {
          wx.showToast({ title: '请输入校园网密码', icon: 'none' })
        }
        return false
      }

      this.setData({ challengeLoading: true })
      try {
        const challenge = await createWifiLoginChallenge({
          ...(loginMode === 'standalone' ? { student_id: trimmedStudentId } : {}),
          password: wifiPassword,
        })
        this.setData({
          challengeToken: challenge.challenge_token,
          captchaImage: challenge.captcha_image,
          challengeMode: challenge.mode || '',
          captchaCode: '',
        })
        return true
      } catch (err: any) {
        if (!silent) {
          wx.showToast({ title: err.message || '获取验证码失败', icon: 'none' })
        }
        return false
      } finally {
        this.setData({ challengeLoading: false })
      }
    },

    async refreshChallenge() {
      await this.loadChallenge()
    },

    async doWifiLogin() {
      const { loginMode, wifiStudentId, wifiPassword, captchaCode, challengeToken } = this.data
      const trimmedStudentId = String(wifiStudentId || '').trim()

      if (loginMode === 'standalone' && !trimmedStudentId) {
        wx.showToast({ title: '请输入学号', icon: 'none' })
        return
      }
      if (!wifiPassword) {
        wx.showToast({ title: '请输入校园网密码', icon: 'none' })
        return
      }

      if (!challengeToken) {
        const ok = await this.loadChallenge()
        if (ok) {
          wx.showToast({ title: '验证码已加载，请输入后再登录', icon: 'none' })
        }
        return
      }

      if (!String(captchaCode || '').trim()) {
        wx.showToast({ title: '请输入验证码', icon: 'none' })
        return
      }

      this.setData({ loginLoading: true })
      try {
        await loginWifi(loginMode, {
          ...(loginMode === 'standalone' ? { student_id: trimmedStudentId } : {}),
          password: wifiPassword,
          challenge_token: challengeToken,
          captcha_code: String(captchaCode).trim(),
        })
        wx.showToast({ title: '登录成功', icon: 'success' })
        this.setData({
          loggedIn: true,
          wifiPassword: '',
          captchaCode: '',
        })
        this.resetChallenge()
        await this.loadFlowInfo()
      } catch (err: any) {
        wx.showToast({ title: err.message || '登录失败', icon: 'none' })
        await this.loadChallenge(true)
      } finally {
        this.setData({ loginLoading: false })
      }
    },

    async unbindDevice(e: any) {
      const mac = e.currentTarget.dataset.mac
      const res = await new Promise<boolean>((resolve) => {
        wx.showModal({
          title: '确认解绑',
          content: `确定要解绑设备 ${mac} 吗？`,
          success: (r) => resolve(r.confirm),
        })
      })

      if (!res) return

      try {
        await unbindWifiMac(mac)
        wx.showToast({ title: '解绑成功', icon: 'success' })
        this.loadDevices()
      } catch (err: any) {
        wx.showToast({ title: err.message || '解绑失败', icon: 'none' })
      }
    },

    refreshFlow() {
      this.loadFlowInfo()
    },
  },
})

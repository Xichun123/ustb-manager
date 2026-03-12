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
import { getWifiPageState, getWifiStudentId, hasSessionId, setWifiPageState } from '../../utils/storage'
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
const WIFI_REFRESH_TTL = 60 * 1000

function parsePaymentNumber(value: any): number | null {
  if (typeof value === 'number' && !Number.isNaN(value)) {
    return value
  }

  if (typeof value === 'string') {
    const normalized = value.replace(/^[+\s]*/, '').replace(/^¥/, '').trim()
    if (!normalized) {
      return null
    }
    const parsed = Number(normalized)
    if (!Number.isNaN(parsed)) {
      return parsed
    }
  }

  return null
}

function getPaymentAmountDisplay(item: any): string {
  const payTypeAmount = parsePaymentNumber(item.pay_type)
  if (payTypeAmount !== null) {
    return formatMoney(payTypeAmount)
  }

  const amountValue = parsePaymentNumber(item.amount)
  if (amountValue !== null) {
    return formatMoney(amountValue)
  }

  return String(item.amount || item.pay_type || '--')
}

function getPaymentDetailDisplay(item: any): string {
  const payType = typeof item.amount === 'string'
    ? String(item.amount)
    : String(item.pay_type || '')
  const extra = String(item.remark || item.terminal || '').trim()

  if (payType && extra && payType !== extra) {
    return `${payType} · ${extra}`
  }

  return payType || extra
}

function buildInitialData() {
  const persisted = getWifiPageState()
  const fallbackMode = hasSessionId() ? 'authenticated' : 'standalone'

  return {
    loading: !persisted,
    refreshing: false,
    loggedIn: persisted ? persisted.loggedIn : false,
    loginMode: (persisted && persisted.loginMode ? persisted.loginMode : fallbackMode) as WifiLoginMode,
    wifiStudentId: persisted && persisted.wifiStudentId ? persisted.wifiStudentId : getWifiStudentId(),
    wifiPassword: '',
    captchaCode: '',
    challengeToken: '',
    captchaImage: '',
    challengeMode: '' as '' | 'direct' | 'webvpn',
    challengeLoading: false,
    loginLoading: false,
    flow: persisted ? persisted.flow : null,
    flowDisplay: persisted && persisted.flowDisplay ? persisted.flowDisplay : {
      balance: '--',
      usedFlow: '--',
      usedFlowV4: '--',
      usedFlowV6: '--',
      availableFlow: '--',
      status: '--',
      package: '--',
    },
    onlineDevices: persisted && Array.isArray(persisted.onlineDevices) ? persisted.onlineDevices : ([] as any[]),
    devices: persisted && Array.isArray(persisted.devices) ? persisted.devices : ([] as any[]),
    payments: persisted && Array.isArray(persisted.payments) ? persisted.payments : ([] as any[]),
    activeSection: persisted && persisted.activeSection ? persisted.activeSection : ('overview' as string),
    iconAssets: WIFI_ICON_ASSETS,
  }
}

Component({
  data: buildInitialData(),

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 3 })
      }
      const persisted = getWifiPageState()
      ;(this as any)._wifiLoaded = false
      ;(this as any)._wifiHasCache = !!persisted
      ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 3 })
      }
      const self = this as any
      const hasContent = !!(
        this.data.loggedIn
        || this.data.wifiStudentId
        || this.data.flow
        || this.data.devices.length > 0
        || this.data.payments.length > 0
      )

      if (!self._wifiLoaded) {
        this.checkWifiStatus({ showLoading: !self._wifiHasCache && !hasContent })
        return
      }

      if (!hasContent) {
        this.checkWifiStatus({ showLoading: true })
        return
      }

      if (Date.now() - (self._lastLoadedAt || 0) > WIFI_REFRESH_TTL) {
        this.checkWifiStatus({ showLoading: false })
      }
    },
  },

  methods: {
    persistState() {
      const updatedAt = Date.now()
      setWifiPageState({
        loggedIn: this.data.loggedIn,
        loginMode: this.data.loginMode,
        wifiStudentId: this.data.wifiStudentId,
        flow: this.data.flow,
        flowDisplay: this.data.flowDisplay,
        onlineDevices: this.data.onlineDevices,
        devices: this.data.devices,
        payments: this.data.payments,
        activeSection: this.data.activeSection,
        updatedAt,
      })
      ;(this as any)._lastLoadedAt = updatedAt
    },

    resetChallenge(resetCaptchaCode = true) {
      this.setData({
        challengeToken: '',
        captchaImage: '',
        challengeMode: '',
        ...(resetCaptchaCode ? { captchaCode: '' } : {}),
      })
    },

    async checkWifiStatus(options?: { showLoading?: boolean }) {
      const showLoading = !!(options && options.showLoading)
      if (showLoading) {
        this.setData({ loading: true })
      } else {
        this.setData({ refreshing: true })
      }
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
          await this.loadFlowInfo({ notifyOnError: showLoading })
          if (this.data.activeSection === 'devices') {
            await this.loadDevices({ notifyOnError: false })
          } else if (this.data.activeSection === 'payments') {
            await this.loadPayments({ notifyOnError: false })
          }
        } else {
          this.setData({
            flow: null,
            onlineDevices: [],
            devices: [],
            payments: [],
          })
          this.persistState()
        }
        ;(this as any)._wifiLoaded = true
      } catch (_e) {
        if (showLoading) {
          this.setData({
            loggedIn: false,
            loginMode: app.globalData.isAuthenticated ? 'authenticated' : 'standalone',
            flow: null,
            onlineDevices: [],
            devices: [],
            payments: [],
          })
          this.persistState()
        }
      } finally {
        if (showLoading) {
          this.setData({ loading: false })
        } else {
          this.setData({ refreshing: false })
        }
      }
    },

    async loadFlowInfo(options?: { notifyOnError?: boolean }) {
      const notifyOnError = !options || options.notifyOnError !== false
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
        this.persistState()
      } catch (err: any) {
        if (notifyOnError) {
          wx.showToast({ title: err.message || '加载流量信息失败', icon: 'none' })
        }
      }
    },

    async loadDevices(options?: { notifyOnError?: boolean }) {
      const notifyOnError = !options || options.notifyOnError !== false
      try {
        const res = await getWifiDevices()
        this.setData({ devices: res.devices || [] })
        this.persistState()
      } catch (err: any) {
        if (notifyOnError) {
          wx.showToast({ title: err.message || '加载设备列表失败', icon: 'none' })
        }
      }
    },

    async loadPayments(options?: { notifyOnError?: boolean }) {
      const notifyOnError = !options || options.notifyOnError !== false
      try {
        const res = await getWifiPayments()
        const payments = (res.payments || []).map((item: any) => ({
          ...item,
          amountDisplay: getPaymentAmountDisplay(item),
          detailDisplay: getPaymentDetailDisplay(item),
        }))
        this.setData({ payments })
        this.persistState()
      } catch (err: any) {
        if (notifyOnError) {
          wx.showToast({ title: err.message || '加载充值记录失败', icon: 'none' })
        }
      }
    },

    switchSection(e: any) {
      const section = e.currentTarget.dataset.section
      this.setData({ activeSection: section }, () => {
        this.persistState()
        if (section === 'devices' && this.data.devices.length === 0) {
          this.loadDevices({ notifyOnError: true })
        }
        if (section === 'payments' && this.data.payments.length === 0) {
          this.loadPayments({ notifyOnError: true })
        }
      })
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
        await this.loadFlowInfo({ notifyOnError: true })
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
        this.loadDevices({ notifyOnError: true })
      } catch (err: any) {
        wx.showToast({ title: err.message || '解绑失败', icon: 'none' })
      }
    },

    refreshFlow() {
      this.loadFlowInfo({ notifyOnError: true })
    },
  },
})

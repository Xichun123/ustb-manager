import { get, post } from '../../services/api'
import { formatFlow, formatMoney } from '../../utils/util'

const app = getApp<IAppOption>()

Component({
  data: {
    loading: true,
    loggedIn: false,
    // Login form
    showLoginForm: false,
    wifiPassword: '',
    loginLoading: false,
    // Flow info
    flow: null as any,
    flowDisplay: {
      balance: '--',
      usedFlow: '--',
      availableFlow: '--',
      status: '--',
      package: '--',
    },
    // Online devices
    onlineDevices: [] as any[],
    // Bound devices
    devices: [] as any[],
    // Payments
    payments: [] as any[],
    // Active section
    activeSection: 'overview' as string,
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
    async checkWifiStatus() {
      this.setData({ loading: true })
      try {
        const status = await get('/api/wifi/status', undefined, { isWifi: true })
        this.setData({ loggedIn: status.logged_in })
        if (status.logged_in) {
          await this.loadFlowInfo()
        }
      } catch (_e) {
        this.setData({ loggedIn: false })
      } finally {
        this.setData({ loading: false })
      }
    },

    async loadFlowInfo() {
      try {
        const flow = await get('/api/wifi/flow', undefined, { isWifi: true })
        this.setData({
          flow,
          flowDisplay: {
            balance: formatMoney(flow.balance || 0),
            usedFlow: formatFlow(flow.used_flow || 0),
            availableFlow: formatFlow(flow.available_flow || 0),
            status: flow.status || '--',
            package: flow.package || '--',
          },
          onlineDevices: flow.online_devices || [],
        })
      } catch (_e) {
        wx.showToast({ title: '加载流量信息失败', icon: 'none' })
      }
    },

    async loadDevices() {
      try {
        const res = await get('/api/wifi/devices', undefined, { isWifi: true })
        this.setData({ devices: res.devices || [] })
      } catch (_e) {
        wx.showToast({ title: '加载设备列表失败', icon: 'none' })
      }
    },

    async loadPayments() {
      try {
        const res = await get('/api/wifi/payments', undefined, { isWifi: true })
        this.setData({ payments: res.payments || [] })
      } catch (_e) {
        wx.showToast({ title: '加载充值记录失败', icon: 'none' })
      }
    },

    // Section switching
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

    // WiFi Login
    showLogin() {
      this.setData({ showLoginForm: true })
    },

    hideLogin() {
      this.setData({ showLoginForm: false })
    },

    onPasswordInput(e: any) {
      this.setData({ wifiPassword: e.detail.value })
    },

    async doWifiLogin() {
      const { wifiPassword } = this.data
      if (!wifiPassword) {
        wx.showToast({ title: '请输入密码', icon: 'none' })
        return
      }

      this.setData({ loginLoading: true })
      try {
        await post('/api/wifi/login', { password: wifiPassword }, { isWifi: true })
        wx.showToast({ title: '登录成功', icon: 'success' })
        this.setData({ showLoginForm: false, loggedIn: true })
        await this.loadFlowInfo()
      } catch (err: any) {
        wx.showToast({ title: err.message || '登录失败', icon: 'none' })
      } finally {
        this.setData({ loginLoading: false })
      }
    },

    // Prevent event propagation (used by modal)
    noop() {},

    // Unbind device
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
        await post('/api/wifi/unbind-mac', { mac_address: mac }, { isWifi: true })
        wx.showToast({ title: '解绑成功', icon: 'success' })
        this.loadDevices()
      } catch (_e) {
        wx.showToast({ title: '解绑失败', icon: 'none' })
      }
    },

    // Refresh
    refreshFlow() {
      this.loadFlowInfo()
    },
  },
})

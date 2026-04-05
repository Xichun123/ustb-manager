import { get } from '../../services/api'
import { getProgressPageState, setProgressPageState } from '../../utils/storage'

const app = getApp<IAppOption>()

const PROGRESS_REFRESH_TTL = 10 * 60 * 1000

function buildInitialData() {
  const persisted = getProgressPageState()

  return {
    loading: !persisted,
    refreshing: false,
    activeTab: persisted && persisted.activeTab ? persisted.activeTab : ('credits' as 'credits' | 'required' | 'plan'),
    creditCategories: persisted && Array.isArray(persisted.creditCategories) ? persisted.creditCategories : ([] as any[]),
    requiredStats: persisted ? persisted.requiredStats : null,
    planData: persisted && Array.isArray(persisted.planData) ? persisted.planData : ([] as any[]),
  }
}

Page({
  data: buildInitialData(),

  onLoad() {
    const persisted = getProgressPageState()
    ;(this as any)._progressLoaded = false
    ;(this as any)._progressHasCache = !!persisted
    ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
    ;(this as any)._tabUpdatedAt = persisted && persisted.tabUpdatedAt ? persisted.tabUpdatedAt : {
      credits: 0,
      required: 0,
      plan: 0,
    }
  },

  onShow() {
    const self = this as any
    const activeTab = this.data.activeTab
    const hasContent = this.hasTabContent(activeTab)

    if (!self._progressLoaded) {
      this.loadActiveTab({ showLoading: !self._progressHasCache && !hasContent })
      return
    }

    if (!hasContent) {
      this.loadActiveTab({ showLoading: true })
      return
    }

    if (Date.now() - this.getTabUpdatedAt(activeTab) > PROGRESS_REFRESH_TTL) {
      this.loadActiveTab({ showLoading: false })
    }
  },

  switchTab(e: any) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab }, () => {
      this.persistState()

      if (!this.hasTabContent(tab)) {
        this.loadActiveTab({ showLoading: true })
        return
      }

      if (Date.now() - this.getTabUpdatedAt(tab) > PROGRESS_REFRESH_TTL) {
        this.loadActiveTab({ showLoading: false })
      }
    })
  },

  hasTabContent(tab: 'credits' | 'required' | 'plan') {
    if (tab === 'credits') {
      return this.data.creditCategories.length > 0
    }
    if (tab === 'required') {
      return !!this.data.requiredStats
    }
    return this.data.planData.length > 0
  },

  getTabUpdatedAt(tab: 'credits' | 'required' | 'plan') {
    const cache = (this as any)._tabUpdatedAt || {}
    return cache[tab] || 0
  },

  markTabUpdated(tab: 'credits' | 'required' | 'plan') {
    const now = Date.now()
    const cache = (this as any)._tabUpdatedAt || {}
    cache[tab] = now
    ;(this as any)._tabUpdatedAt = cache
    ;(this as any)._lastLoadedAt = now
  },

  persistState() {
    setProgressPageState({
      activeTab: this.data.activeTab,
      creditCategories: this.data.creditCategories,
      requiredStats: this.data.requiredStats,
      planData: this.data.planData,
      tabUpdatedAt: (this as any)._tabUpdatedAt || {
        credits: 0,
        required: 0,
        plan: 0,
      },
      updatedAt: (this as any)._lastLoadedAt || Date.now(),
    })
  },

  loadActiveTab(options?: { showLoading?: boolean }) {
    const tab = this.data.activeTab
    if (tab === 'credits') {
      return this.loadCredits(options)
    }
    if (tab === 'required') {
      return this.loadRequired(options)
    }
    return this.loadPlan(options)
  },

  async loadCredits(options?: { showLoading?: boolean }) {
    if (!app.globalData.isAuthenticated) {
      if (!app.globalData.authBootstrapInProgress) {
        wx.redirectTo({ url: '/pages/login/login' })
      }
      return
    }

    const showLoading = !!(options && options.showLoading)
    if (showLoading) {
      this.setData({ loading: true })
    } else {
      this.setData({ refreshing: true })
    }
    try {
      const res = await get('/api/grades/credit-completion-status')
      // res is a dict with category info
      const categories: any[] = []
      if (res && typeof res === 'object') {
        // Parse the response - structure varies, try common patterns
        if (Array.isArray(res)) {
          res.forEach((item: any) => {
            categories.push({
              name: item.category_name || item.kclb || '--',
              required: item.required_credits || item.yqxf || 0,
              completed: item.completed_credits || item.yxxf || 0,
              remaining: item.remaining_credits || 0,
              percentage: item.required_credits > 0
                ? Math.min(100, Math.round((item.completed_credits / item.required_credits) * 100))
                : 0,
            })
          })
        } else {
          // Handle dict format
          Object.entries(res).forEach(([key, val]: [string, any]) => {
            if (val && typeof val === 'object') {
              const required = val.yqxf || val.required_credits || 0
              const completed = val.yxxf || val.completed_credits || 0
              categories.push({
                name: val.kclb || val.category_name || key,
                required,
                completed,
                remaining: Math.max(0, required - completed),
                percentage: required > 0 ? Math.min(100, Math.round((completed / required) * 100)) : 0,
              })
            }
          })
        }
      }
      this.setData({ creditCategories: categories })
      ;(this as any)._progressLoaded = true
      this.markTabUpdated('credits')
      this.persistState()
    } catch (_e) {
      if (showLoading) {
        wx.showToast({ title: '加载失败', icon: 'none' })
      }
    } finally {
      if (showLoading) {
        this.setData({ loading: false })
      } else {
        this.setData({ refreshing: false })
      }
    }
  },

  async loadRequired(options?: { showLoading?: boolean }) {
    if (!app.globalData.isAuthenticated) {
      if (!app.globalData.authBootstrapInProgress) {
        wx.redirectTo({ url: '/pages/login/login' })
      }
      return
    }

    const showLoading = !!(options && options.showLoading)
    if (showLoading) {
      this.setData({ loading: true })
    } else {
      this.setData({ refreshing: true })
    }
    try {
      const res = await get('/api/grades/required-course-status')
      this.setData({ requiredStats: res })
      ;(this as any)._progressLoaded = true
      this.markTabUpdated('required')
      this.persistState()
    } catch (_e) {
      if (showLoading) {
        wx.showToast({ title: '加载失败', icon: 'none' })
      }
    } finally {
      if (showLoading) {
        this.setData({ loading: false })
      } else {
        this.setData({ refreshing: false })
      }
    }
  },

  async loadPlan(options?: { showLoading?: boolean }) {
    if (!app.globalData.isAuthenticated) {
      if (!app.globalData.authBootstrapInProgress) {
        wx.redirectTo({ url: '/pages/login/login' })
      }
      return
    }

    const showLoading = !!(options && options.showLoading)
    if (showLoading) {
      this.setData({ loading: true })
    } else {
      this.setData({ refreshing: true })
    }
    try {
      const res = await get('/api/grades/student-plan')
      this.setData({ planData: Array.isArray(res) ? res : [res] })
      ;(this as any)._progressLoaded = true
      this.markTabUpdated('plan')
      this.persistState()
    } catch (_e) {
      if (showLoading) {
        wx.showToast({ title: '加载失败', icon: 'none' })
      }
    } finally {
      if (showLoading) {
        this.setData({ loading: false })
      } else {
        this.setData({ refreshing: false })
      }
    }
  },
})

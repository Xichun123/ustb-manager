import { get } from '../../services/api'

Page({
  data: {
    loading: true,
    activeTab: 'credits' as 'credits' | 'required' | 'plan',
    // Credit completion
    creditCategories: [] as any[],
    // Required courses
    requiredStats: null as any,
    // Student plan
    planData: [] as any[],
  },

  onLoad() {
    this.loadCredits()
  },

  switchTab(e: any) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })

    if (tab === 'credits' && this.data.creditCategories.length === 0) {
      this.loadCredits()
    } else if (tab === 'required' && !this.data.requiredStats) {
      this.loadRequired()
    } else if (tab === 'plan' && this.data.planData.length === 0) {
      this.loadPlan()
    }
  },

  async loadCredits() {
    this.setData({ loading: true })
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
    } catch (_e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadRequired() {
    this.setData({ loading: true })
    try {
      const res = await get('/api/grades/required-course-status')
      this.setData({ requiredStats: res })
    } catch (_e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadPlan() {
    this.setData({ loading: true })
    try {
      const res = await get('/api/grades/student-plan')
      this.setData({ planData: Array.isArray(res) ? res : [res] })
    } catch (_e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },
})

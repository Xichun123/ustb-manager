import { get } from '../../services/api'

const app = getApp<IAppOption>()

Component({
  data: {
    loading: true,
    viewMode: 'week' as 'week' | 'term',
    termList: [] as any[],
    selectedTermIdx: 0,
    weekList: [] as number[],
    selectedWeekIdx: 0,
    schedule: [] as any[],
    dates: {} as Record<string, string>,
    currentXn: '',
    currentXq: '',
    courseDetail: null as any,
    showDetail: false,
  },

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 1 })
      }
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 1 })
      }
      if (!this.data.currentXn) {
        this.init()
      }
    },
  },

  methods: {
    async init() {
      if (!app.globalData.isAuthenticated) {
        wx.redirectTo({ url: '/pages/login/login' })
        return
      }

      this.setData({ loading: true })
      try {
        const [currentTerm, termList] = await Promise.all([
          get('/api/schedule/current-term'),
          get('/api/schedule/term-list'),
        ])

        const xn = currentTerm.XN
        const xq = currentTerm.XQ
        this.setData({ currentXn: xn, currentXq: xq })

        // Format term list for picker
        const terms = Array.isArray(termList)
          ? termList.map((t: any) => ({ code: t.dm, name: t.mc }))
          : []
        this.setData({ termList: terms })

        // Find current term index
        const currentCode = `${xn}${xq}`
        const idx = terms.findIndex((t: any) => t.code === currentCode)
        if (idx >= 0) this.setData({ selectedTermIdx: idx })

        // Load weeks
        await this.loadWeeks(xn, xq)
      } catch (err: any) {
        wx.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.setData({ loading: false })
      }
    },

    async loadWeeks(xn: string, xq: string) {
      try {
        const weekList = await get('/api/schedule/week-list', { xn, xq })
        const weeks = Array.isArray(weekList) ? weekList.map((_: any, i: number) => i + 1) : []
        const currentWeekIdx = weeks.length > 0 ? weeks.length - 1 : 0
        this.setData({ weekList: weeks, selectedWeekIdx: currentWeekIdx })

        if (this.data.viewMode === 'week' && weeks.length > 0) {
          await this.loadWeekSchedule(xn, xq, weeks[currentWeekIdx])
        } else {
          await this.loadFullSchedule(xn, xq)
        }
      } catch (_e) {
        this.setData({ weekList: [], schedule: [] })
      }
    },

    async loadWeekSchedule(xn: string, xq: string, week: number) {
      this.setData({ loading: true })
      try {
        const res = await get('/api/schedule/week', { xn, xq, week })
        this.setData({
          schedule: res.schedule || [],
          dates: res.dates || {},
        })
      } catch (_e) {
        this.setData({ schedule: [] })
      } finally {
        this.setData({ loading: false })
      }
    },

    async loadFullSchedule(xn: string, xq: string) {
      this.setData({ loading: true })
      try {
        const res = await get('/api/schedule/full', { xn, xq })
        this.setData({
          schedule: res.schedule || [],
          dates: res.dates || {},
        })
      } catch (_e) {
        this.setData({ schedule: [] })
      } finally {
        this.setData({ loading: false })
      }
    },

    // View mode switch
    switchView(e: any) {
      const mode = e.currentTarget.dataset.mode
      this.setData({ viewMode: mode })
      const { currentXn, currentXq, weekList, selectedWeekIdx } = this.data
      if (mode === 'week' && weekList.length > 0) {
        this.loadWeekSchedule(currentXn, currentXq, weekList[selectedWeekIdx])
      } else {
        this.loadFullSchedule(currentXn, currentXq)
      }
    },

    // Term picker change
    onTermChange(e: any) {
      const idx = parseInt(e.detail.value)
      const term = this.data.termList[idx]
      if (!term) return

      // Parse xn and xq from term code
      const code = term.code as string
      const xq = code.slice(-1)
      const xn = code.slice(0, -1)
      this.setData({ selectedTermIdx: idx, currentXn: xn, currentXq: xq })
      this.loadWeeks(xn, xq)
    },

    // Week picker change
    onWeekChange(e: any) {
      const idx = parseInt(e.detail.value)
      this.setData({ selectedWeekIdx: idx })
      this.loadWeekSchedule(this.data.currentXn, this.data.currentXq, this.data.weekList[idx])
    },

    // Prevent event propagation (used by modal)
    noop() {},

    // Course click detail
    onCourseClick(e: any) {
      const { course } = e.detail
      this.setData({ courseDetail: course, showDetail: true })
    },

    closeDetail() {
      this.setData({ showDetail: false })
    },
  },
})

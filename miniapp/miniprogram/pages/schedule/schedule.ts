import { get } from '../../services/api'
import { hasSessionId } from '../../utils/storage'
import { calculateCurrentWeekFromDates, extractWeekNumbers } from '../../utils/util'

const app = getApp<IAppOption>()

Component({
  data: {
    loading: true,
    viewMode: 'week' as 'week' | 'term',
    termList: [] as any[],
    selectedTermIdx: 0,
    weekList: [] as number[],
    selectedWeekIdx: 0,
    currentWeek: 0,
    schedule: [] as any[],
    dates: {} as Record<string, string>,
    currentXn: '',
    currentXq: '',
    currentTermCode: '',
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
      if (!app.globalData.isAuthenticated && !hasSessionId()) {
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
        const currentTermCode = `${xn}${xq}`
        this.setData({ currentXn: xn, currentXq: xq, currentTermCode })

        // Format term list for picker
        const terms = Array.isArray(termList)
          ? termList.map((t: any) => ({ code: t.dm, name: t.mc }))
          : []
        this.setData({ termList: terms })

        // Find current term index
        const idx = terms.findIndex((t: any) => t.code === currentTermCode)
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
        const weeks = extractWeekNumbers(weekList)
        let selectedWeekIdx = 0
        let currentWeek = 0

        if (`${xn}${xq}` === this.data.currentTermCode && weeks.length > 0) {
          const firstWeekRes = await get('/api/schedule/week', { xn, xq, week: weeks[0] })
          const calculatedWeek = calculateCurrentWeekFromDates(firstWeekRes.dates, weeks)
          if (calculatedWeek) {
            currentWeek = calculatedWeek
            selectedWeekIdx = Math.max(0, weeks.findIndex((week: number) => week === calculatedWeek))
          }
        }

        this.setData({ weekList: weeks, selectedWeekIdx, currentWeek })

        if (this.data.viewMode === 'week' && weeks.length > 0) {
          await this.loadWeekSchedule(xn, xq, weeks[selectedWeekIdx])
        } else {
          await this.loadFullSchedule(xn, xq)
        }
      } catch (_e) {
        this.setData({ weekList: [], schedule: [], currentWeek: 0 })
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
      if (mode === 'week' && weekList.length > 0 && weekList[selectedWeekIdx]) {
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
      const week = this.data.weekList[idx]
      if (week) {
        this.loadWeekSchedule(this.data.currentXn, this.data.currentXq, week)
      }
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

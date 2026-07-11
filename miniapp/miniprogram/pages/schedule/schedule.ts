import { get } from '../../services/api'
import type { components } from '../../services/openapi'
import {
  getScheduleHideWeekend,
  getSchedulePageState,
  setScheduleHideWeekend,
  setSchedulePageState,
} from '../../utils/storage'

const app = getApp<IAppOption>()
const SCHEDULE_REFRESH_TTL = 5 * 60 * 1000
type ScheduleCourse = components['schemas']['ScheduleCourse']
type ScheduleView = components['schemas']['ScheduleView']
type AcademicContext = components['schemas']['AcademicContextResponse']
type AcademicTerm = components['schemas']['AcademicTermOption']
type DisplayCourse = Omit<ScheduleCourse, 'weeks'> & { weeks: string }
interface TermOption { code: string; name: string }

function findTermIndex(termList: TermOption[], termCode: string): number {
  for (let i = 0; i < termList.length; i += 1) {
    if (termList[i] && termList[i].code === termCode) {
      return i
    }
  }
  return 0
}

function findWeekIndex(weekList: number[], week: number): number {
  const idx = weekList.indexOf(week)
  return idx >= 0 ? idx : 0
}

function parseTermCode(termCode: string): { xn: string; xq: string } {
  const code = String(termCode || '')
  if (code.length <= 9) {
    return { xn: '', xq: '' }
  }
  return {
    xn: code.slice(0, 9),
    xq: code.slice(-1),
  }
}

function displayCourses(items?: ScheduleCourse[]): DisplayCourse[] {
  return (items || []).map(item => ({ ...item, weeks: item.week_text }))
}

function buildInitialData() {
  const persisted = getSchedulePageState()
  const termList = persisted && Array.isArray(persisted.termList) ? persisted.termList : []
  const weekList = persisted && Array.isArray(persisted.weekList) ? persisted.weekList : []
  const selectedTermCode = persisted ? persisted.selectedTermCode : ''
  const selectedWeek = persisted ? persisted.selectedWeek : 0

  return {
    loading: !(persisted && Array.isArray(persisted.schedule)),
    refreshing: false,
    viewMode: persisted && persisted.viewMode ? persisted.viewMode : ('week' as 'week' | 'term'),
    termList,
    selectedTermIdx: findTermIndex(termList, selectedTermCode),
    weekList,
    selectedWeekIdx: findWeekIndex(weekList, selectedWeek),
    currentWeek: persisted ? persisted.currentWeek : 0,
    hideWeekend: getScheduleHideWeekend(),
    schedule: persisted && Array.isArray(persisted.schedule) ? persisted.schedule : ([] as DisplayCourse[]),
    dates: persisted && persisted.dates ? persisted.dates : ({} as Record<string, string>),
    currentXn: persisted ? persisted.currentXn : '',
    currentXq: persisted ? persisted.currentXq : '',
    currentTermCode: persisted ? persisted.currentTermCode : '',
    courseDetail: null as DisplayCourse | null,
    showDetail: false,
  }
}

Component({
  data: buildInitialData(),

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 1 })
      }
      const persisted = getSchedulePageState()
      ;(this as any)._scheduleLoaded = false
      ;(this as any)._scheduleHasCache = !!persisted
      ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
      ;(this as any)._viewCaches = persisted && persisted.scheduleCaches ? persisted.scheduleCaches : {}
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 1 })
      }
      this.setData({ hideWeekend: getScheduleHideWeekend() })

      const self = this as any
      const hasContent = !!(this.data.termList.length > 0 && this.data.schedule)

      if (!self._scheduleLoaded) {
        this.init({ showLoading: !self._scheduleHasCache && !hasContent })
        return
      }

      if (!hasContent) {
        this.init({ showLoading: true })
        return
      }

      if (Date.now() - (self._lastLoadedAt || 0) > SCHEDULE_REFRESH_TTL) {
        this.init({ showLoading: false })
      }
    },
  },

  methods: {
    getSelectedTermCode() {
      const term = this.data.termList[this.data.selectedTermIdx]
      return term ? term.code : ''
    },

    getSelectedWeekValue() {
      const week = this.data.weekList[this.data.selectedWeekIdx]
      return week || 0
    },

    getViewCaches() {
      const self = this as any
      if (!self._viewCaches) {
        self._viewCaches = { week: {}, term: {} }
      }
      if (!self._viewCaches.week) {
        self._viewCaches.week = {}
      }
      if (!self._viewCaches.term) {
        self._viewCaches.term = {}
      }
      return self._viewCaches
    },

    getViewCache(mode: 'week' | 'term', termCode: string, week?: number) {
      const caches = this.getViewCaches()
      const key = mode === 'week' ? `${termCode}:${week || 0}` : termCode
      return caches[mode] && caches[mode][key] ? caches[mode][key] : null
    },

    setViewCache(mode: 'week' | 'term', termCode: string, schedule: DisplayCourse[], dates: Record<string, string>, week?: number) {
      const caches = this.getViewCaches()
      const key = mode === 'week' ? `${termCode}:${week || 0}` : termCode
      caches[mode][key] = {
        schedule: schedule || [],
        dates: dates || {},
        cachedAt: Date.now(),
      }
      ;(this as any)._viewCaches = caches
    },

    applyViewCache(mode: 'week' | 'term', termCode: string, week?: number) {
      const cached = this.getViewCache(mode, termCode, week)
      if (!cached) {
        return false
      }

      this.setData({
        schedule: cached.schedule || [],
        dates: cached.dates || {},
        loading: false,
      })
      return true
    },

    persistState() {
      const selectedTermCode = this.getSelectedTermCode()
      const selectedWeek = this.getSelectedWeekValue()
      const updatedAt = Date.now()
      setSchedulePageState({
        viewMode: this.data.viewMode,
        selectedTermCode,
        selectedWeek,
        currentWeek: this.data.currentWeek,
        currentXn: this.data.currentXn,
        currentXq: this.data.currentXq,
        currentTermCode: this.data.currentTermCode,
        termList: this.data.termList,
        weekList: this.data.weekList,
        schedule: this.data.schedule,
        dates: this.data.dates,
        scheduleCaches: this.getViewCaches(),
        updatedAt,
      })
      ;(this as any)._lastLoadedAt = updatedAt
    },

    async init(options?: { showLoading?: boolean }) {
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
        const [context, termRecords] = await Promise.all([
          get<AcademicContext>('/api/academic/context'),
          get<AcademicTerm[]>('/api/academic/terms'),
        ])
        const terms: TermOption[] = termRecords.map(term => ({
          code: term.code,
          name: term.name || term.code,
        }))

        const currentTermCode = context.teaching_term.code
        const currentWeek = context.week || 1

        let preferredTermCode = this.getSelectedTermCode()
        if (!preferredTermCode) {
          preferredTermCode = currentTermCode
        }
        if (findTermIndex(terms, preferredTermCode) === 0 && (!terms[0] || terms[0].code !== preferredTermCode)) {
          preferredTermCode = currentTermCode || (terms[0] ? terms[0].code : '')
        }

        const selectedTermIdx = findTermIndex(terms, preferredTermCode)
        const termCode = terms[selectedTermIdx] ? terms[selectedTermIdx].code : preferredTermCode
        const parsedTerm = parseTermCode(termCode)

        await new Promise<void>((resolve) => {
          this.setData(
            {
              termList: terms,
              selectedTermIdx,
              currentXn: parsedTerm.xn,
              currentXq: parsedTerm.xq,
              currentTermCode,
              currentWeek,
            },
            () => resolve()
          )
        })

        await this.loadWeeks(parsedTerm.xn, parsedTerm.xq, {
          showLoading: false,
          preferredWeek: this.getSelectedWeekValue() || currentWeek,
        })

        ;(this as any)._scheduleLoaded = true
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

    async loadWeeks(xn: string, xq: string, options?: { showLoading?: boolean; preferredWeek?: number }) {
      const showLoading = !!(options && options.showLoading)
      try {
        const currentWeek = `${xn}-${xq}` === this.data.currentTermCode
          ? this.data.currentWeek
          : 0
        const weeks = Array.from(
          { length: Math.max(24, currentWeek || 0) },
          (_, index) => index + 1,
        )
        const termCode = `${xn}-${xq}`
        let selectedWeek = options && options.preferredWeek ? options.preferredWeek : this.getSelectedWeekValue()

        if (!selectedWeek || weeks.indexOf(selectedWeek) === -1) {
          selectedWeek = currentWeek || 1
        }

        const selectedWeekIdx = findWeekIndex(weeks, selectedWeek)

        await new Promise<void>((resolve) => {
          this.setData(
            {
              weekList: weeks,
              selectedWeekIdx,
              currentWeek,
            },
            () => resolve()
          )
        })

        if (this.data.viewMode === 'week' && selectedWeek) {
          const hasCache = this.applyViewCache('week', termCode, selectedWeek)
          await this.loadWeekSchedule(xn, xq, selectedWeek, {
            showLoading: !!(options && options.showLoading && !hasCache),
          })
        } else {
          const hasCache = this.applyViewCache('term', termCode)
          await this.loadFullSchedule(xn, xq, {
            showLoading: !!(options && options.showLoading && !hasCache),
          })
        }

        this.persistState()
      } catch (_e) {
        if (showLoading) {
          this.setData({ weekList: [], schedule: [], currentWeek: 0, dates: {} })
          this.persistState()
        }
      }
    },

    async loadWeekSchedule(xn: string, xq: string, week: number, options?: { showLoading?: boolean }) {
      const showLoading = !!(options && options.showLoading)
      if (showLoading) {
        this.setData({ loading: true })
      }

      try {
        const termCode = `${xn}-${xq}`
        const res = await get<ScheduleView>('/api/schedule', { term: termCode, week })
        const schedule = displayCourses(res.items)
        const dates = res.dates || {}

        this.setData({
          schedule,
          dates,
        })
        this.setViewCache('week', termCode, schedule, dates, week)
        this.persistState()
      } catch (_e) {
        if (showLoading) {
          this.setData({ schedule: [], dates: {} })
        }
      } finally {
        if (showLoading) {
          this.setData({ loading: false })
        }
      }
    },

    async loadFullSchedule(xn: string, xq: string, options?: { showLoading?: boolean }) {
      const showLoading = !!(options && options.showLoading)
      if (showLoading) {
        this.setData({ loading: true })
      }

      try {
        const termCode = `${xn}-${xq}`
        const res = await get<ScheduleView>('/api/schedule', { term: termCode })
        const schedule = displayCourses(res.items)
        const dates = res.dates || {}

        this.setData({
          schedule,
          dates,
        })
        this.setViewCache('term', termCode, schedule, dates)
        this.persistState()
      } catch (_e) {
        if (showLoading) {
          this.setData({ schedule: [], dates: {} })
        }
      } finally {
        if (showLoading) {
          this.setData({ loading: false })
        }
      }
    },

    switchView(e: any) {
      const mode = e.currentTarget.dataset.mode
      if (mode === this.data.viewMode) {
        return
      }

      this.setData({ viewMode: mode }, () => {
        const termCode = this.getSelectedTermCode() || `${this.data.currentXn}-${this.data.currentXq}`
        this.persistState()

        if (mode === 'week') {
          const week = this.getSelectedWeekValue()
          const hasCache = week ? this.applyViewCache('week', termCode, week) : false
          if (week) {
            this.loadWeekSchedule(this.data.currentXn, this.data.currentXq, week, {
              showLoading: !hasCache,
            })
          }
        } else {
          const hasCache = this.applyViewCache('term', termCode)
          this.loadFullSchedule(this.data.currentXn, this.data.currentXq, {
            showLoading: !hasCache,
          })
        }
      })
    },

    onTermChange(e: any) {
      const idx = parseInt(e.detail.value, 10) || 0
      const term = this.data.termList[idx]
      if (!term) return

      const parsedTerm = parseTermCode(term.code)
      this.setData(
        {
          selectedTermIdx: idx,
          currentXn: parsedTerm.xn,
          currentXq: parsedTerm.xq,
        },
        () => {
          this.persistState()
          this.loadWeeks(parsedTerm.xn, parsedTerm.xq, { showLoading: true, preferredWeek: 0 })
        }
      )
    },

    onWeekChange(e: any) {
      const idx = parseInt(e.detail.value, 10) || 0
      const week = this.data.weekList[idx]
      if (!week) return

      this.setData({ selectedWeekIdx: idx }, () => {
        const termCode = this.getSelectedTermCode() || `${this.data.currentXn}-${this.data.currentXq}`
        this.persistState()
        const hasCache = this.applyViewCache('week', termCode, week)
        this.loadWeekSchedule(this.data.currentXn, this.data.currentXq, week, {
          showLoading: !hasCache,
        })
      })
    },

    onHideWeekendChange(e: any) {
      const hideWeekend = !!(e.detail && e.detail.value)
      setScheduleHideWeekend(hideWeekend)
      this.setData({ hideWeekend })
    },

    noop() {},

    onCourseClick(e: any) {
      const course = e.detail ? e.detail.course : null
      if (!course) return
      this.setData({ courseDetail: course, showDetail: true })
    },

    closeDetail() {
      this.setData({ showDetail: false })
    },
  },
})

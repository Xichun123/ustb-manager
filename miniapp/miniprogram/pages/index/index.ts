import { get } from '../../services/api'
import {
  getDashboardPageState,
  getScheduleHideWeekend,
  getUserInfo,
  setDashboardPageState,
  setUserInfo,
} from '../../utils/storage'
import { calculateCurrentWeekFromDates, extractWeekNumbers, formatFlow, formatMoney } from '../../utils/util'

const app = getApp<IAppOption>()
const DASHBOARD_REFRESH_TTL = 60 * 1000

function buildInitialData() {
  const persisted = getDashboardPageState()

  return {
    loading: !persisted,
    refreshing: false,
    studentInfo: persisted ? persisted.studentInfo : getUserInfo(),
    schedule: persisted && Array.isArray(persisted.schedule) ? persisted.schedule : ([] as any[]),
    scheduleDates: persisted && persisted.scheduleDates ? persisted.scheduleDates : ({} as Record<string, string>),
    currentWeek: persisted ? persisted.currentWeek : 0,
    hideWeekend: getScheduleHideWeekend(),
    wifiStatus: persisted ? persisted.wifiStatus : null,
    wifiFlow: persisted ? persisted.wifiFlow : null,
    wifiFlowDisplay: persisted ? persisted.wifiFlowDisplay : '',
    wifiBalanceDisplay: persisted ? persisted.wifiBalanceDisplay : '',
  }
}

Component({
  data: buildInitialData(),

  lifetimes: {
    attached() {
      // Set tabbar selected
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 0 })
      }
      const persisted = getDashboardPageState()
      ;(this as any)._dashboardLoaded = false
      ;(this as any)._dashboardHasCache = !!persisted
      ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 0 })
      }
      this.setData({ hideWeekend: getScheduleHideWeekend() })
      const self = this as any
      const hasContent = !!(
        this.data.studentInfo
        || this.data.schedule.length > 0
        || this.data.wifiStatus
        || this.data.wifiFlow
      )
      if (!self._dashboardLoaded) {
        this.loadData({ showLoading: !self._dashboardHasCache && !hasContent })
        return
      }
      if (!hasContent) {
        this.loadData({ showLoading: true })
        return
      }
      if (Date.now() - (self._lastLoadedAt || 0) > DASHBOARD_REFRESH_TTL) {
        this.loadData({ showLoading: false })
      }
    },
  },

  methods: {
    persistState() {
      const updatedAt = Date.now()
      setDashboardPageState({
        studentInfo: this.data.studentInfo,
        schedule: this.data.schedule,
        scheduleDates: this.data.scheduleDates,
        currentWeek: this.data.currentWeek,
        wifiStatus: this.data.wifiStatus,
        wifiFlow: this.data.wifiFlow,
        wifiFlowDisplay: this.data.wifiFlowDisplay,
        wifiBalanceDisplay: this.data.wifiBalanceDisplay,
        updatedAt,
      })
      ;(this as any)._lastLoadedAt = updatedAt
    },

    async loadStudentInfo() {
      const cached = getUserInfo()
      if (cached) {
        this.setData({ studentInfo: cached })
        app.globalData.userInfo = cached
      }

      const studentInfoRes = await get('/api/grades/student-info').catch(() => null)
      if (!studentInfoRes) {
        return
      }

      const info = {
        name: studentInfoRes.XM || '',
        student_id: studentInfoRes.XH || '',
        dept: studentInfoRes.YXMC || '',
        major: studentInfoRes.ZYMC || '',
        class_name: studentInfoRes.BJMC || '',
      }
      this.setData({ studentInfo: info })
      setUserInfo(info)
      app.globalData.userInfo = info
    },

    async loadScheduleSummary() {
      const termRes = await get('/api/schedule/current-term').catch(() => null)
      if (!termRes) {
        return
      }

      const xn = termRes.XN
      const xq = termRes.XQ
      const weekList = await get('/api/schedule/week-list', { xn, xq }).catch(() => [])
      const weeks = extractWeekNumbers(weekList)
      let currentWeek = weeks[0] || 1

      if (weeks.length > 0) {
        const firstWeekRes = await get('/api/schedule/week', { xn, xq, week: weeks[0] }).catch(() => null)
        if (firstWeekRes && firstWeekRes.dates) {
          const calculatedWeek = calculateCurrentWeekFromDates(firstWeekRes.dates, weeks)
          currentWeek = calculatedWeek || weeks[0]
        }
      }

      this.setData({ currentWeek })

      const scheduleRes = await get('/api/schedule/week', { xn, xq, week: currentWeek }).catch(() => null)
      if (!scheduleRes) {
        return
      }

      this.setData({
        schedule: scheduleRes.schedule || [],
        scheduleDates: scheduleRes.dates || {},
      })
    },

    async loadWifiSummary() {
      const wifiStatus = await get('/api/wifi/status', undefined, { isWifi: true }).catch(() => null)
      this.setData({ wifiStatus })
      if (!wifiStatus || !wifiStatus.logged_in) {
        this.setData({
          wifiFlow: null,
          wifiFlowDisplay: '',
          wifiBalanceDisplay: '',
        })
        return
      }

      const flow = await get('/api/wifi/flow', undefined, { isWifi: true }).catch(() => null)
      if (!flow) {
        return
      }

      this.setData({
        wifiFlow: flow,
        wifiFlowDisplay: formatFlow(flow.used_flow || 0),
        wifiBalanceDisplay: formatMoney(flow.balance || 0),
      })
    },

    async loadData(options?: { showLoading?: boolean }) {
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
        await Promise.all([
          this.loadStudentInfo(),
          this.loadScheduleSummary(),
          this.loadWifiSummary(),
        ])
        ;(this as any)._dashboardLoaded = true
        this.persistState()
      } finally {
        if (showLoading) {
          this.setData({ loading: false })
        } else {
          this.setData({ refreshing: false })
        }
      }
    },

    // Quick entries
    goToExams() {
      wx.navigateTo({ url: '/pages/exams/exams' })
    },
    goToCourses() {
      wx.navigateTo({ url: '/pages/courses/courses' })
    },
    goToProgress() {
      wx.navigateTo({ url: '/pages/progress/progress' })
    },

    onCourseClick(e: any) {
      const { course } = e.detail
      wx.showModal({
        title: course.course_name,
        content: `教师: ${course.teacher}\n地点: ${course.location}\n周次: ${course.weeks}\n时间: ${course.period_text || ''}`,
        showCancel: false,
      })
    },
  },
})

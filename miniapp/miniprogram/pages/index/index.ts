import { get } from '../../services/api'
import { getUserInfo, setUserInfo } from '../../utils/storage'
import { formatFlow, formatMoney } from '../../utils/util'

const app = getApp<IAppOption>()

Component({
  data: {
    loading: true,
    studentInfo: null as any,
    schedule: [] as any[],
    scheduleDates: {} as Record<string, string>,
    currentWeek: 0,
    wifiStatus: null as any,
    wifiFlow: null as any,
    wifiFlowDisplay: '',
    wifiBalanceDisplay: '',
  },

  lifetimes: {
    attached() {
      // Set tabbar selected
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 0 })
      }
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 0 })
      }
      this.loadData()
    },
  },

  methods: {
    async loadData() {
      if (!app.globalData.isAuthenticated) {
        wx.redirectTo({ url: '/pages/login/login' })
        return
      }

      this.setData({ loading: true })

      try {
        // Parallel fetch: student info, schedule, wifi
        const [studentInfoRes, termRes] = await Promise.all([
          get('/api/grades/student-info').catch(() => null),
          get('/api/schedule/current-term').catch(() => null),
        ])

        // Student info
        if (studentInfoRes) {
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
        } else {
          const cached = getUserInfo()
          if (cached) this.setData({ studentInfo: cached })
        }

        // Schedule - get current week and fetch
        if (termRes) {
          const xn = termRes.XN
          const xq = termRes.XQ
          try {
            const weekList = await get('/api/schedule/week-list', { xn, xq })
            const currentWeek = Array.isArray(weekList) ? weekList.length : 1
            this.setData({ currentWeek })

            const scheduleRes = await get('/api/schedule/week', { xn, xq, week: currentWeek })
            this.setData({
              schedule: scheduleRes.schedule || [],
              scheduleDates: scheduleRes.dates || {},
            })
          } catch (_e) {
            // Schedule fetch failed
          }
        }

        // WiFi status
        try {
          const wifiStatus = await get('/api/wifi/status', undefined, { isWifi: true })
          this.setData({ wifiStatus })
          if (wifiStatus && wifiStatus.logged_in) {
            const flow = await get('/api/wifi/flow', undefined, { isWifi: true })
            this.setData({
              wifiFlow: flow,
              wifiFlowDisplay: formatFlow(flow.used_flow || 0),
              wifiBalanceDisplay: formatMoney(flow.balance || 0),
            })
          }
        } catch (_e) {
          // WiFi not available
        }
      } finally {
        this.setData({ loading: false })
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

import { get } from '../../services/api'
import { logout } from '../../services/auth'
import { getUserInfo, hasSessionId, setUserInfo } from '../../utils/storage'

const app = getApp<IAppOption>()

Component({
  data: {
    loading: true,
    userInfo: null as any,
    studentInfo: null as any,
  },

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 4 })
      }
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 4 })
      }
      this.loadData()
    },
  },

  methods: {
    async loadData() {
      if (!app.globalData.isAuthenticated && !hasSessionId()) {
        wx.redirectTo({ url: '/pages/login/login' })
        return
      }

      this.setData({ loading: true })

      // Try cached first
      const cached = getUserInfo()
      if (cached) {
        this.setData({ studentInfo: cached })
      }

      try {
        const [userRes, studentRes] = await Promise.all([
          get('/api/grades/user-info').catch(() => null),
          get('/api/grades/student-info').catch(() => null),
        ])

        if (userRes) {
          this.setData({ userInfo: userRes })
        }

        if (studentRes) {
          const info = {
            name: studentRes.XM || '',
            student_id: studentRes.XH || '',
            dept: studentRes.YXMC || '',
            major: studentRes.ZYMC || '',
            class_name: studentRes.BJMC || '',
            grade: studentRes.NJMC || '',
            gender: studentRes.XB || '',
          }
          this.setData({ studentInfo: info })
          setUserInfo(info)
          app.globalData.userInfo = info
        }
      } catch (_e) {
        // Use cached data
      } finally {
        this.setData({ loading: false })
      }
    },

    // Navigation
    goToExams() {
      wx.navigateTo({ url: '/pages/exams/exams' })
    },
    goToCourses() {
      wx.navigateTo({ url: '/pages/courses/courses' })
    },
    goToProgress() {
      wx.navigateTo({ url: '/pages/progress/progress' })
    },

    // Logout
    async doLogout() {
      const res = await new Promise<boolean>((resolve) => {
        wx.showModal({
          title: '确认退出',
          content: '确定要退出登录吗？',
          success: (r) => resolve(r.confirm),
        })
      })

      if (!res) return

      try {
        await logout()
        wx.redirectTo({ url: '/pages/login/login' })
      } catch (_e) {
        wx.showToast({ title: '退出失败', icon: 'none' })
      }
    },
  },
})

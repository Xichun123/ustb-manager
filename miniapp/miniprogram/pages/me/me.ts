import { get } from '../../services/api'
import { logout } from '../../services/auth'
import { getMePageState, getUserInfo, hasSessionId, setMePageState, setUserInfo } from '../../utils/storage'

const app = getApp<IAppOption>()
const ME_REFRESH_TTL = 5 * 60 * 1000

function buildInitialData() {
  const persisted = getMePageState()
  const cachedStudentInfo = getUserInfo()
  const studentInfo = persisted && persisted.studentInfo ? persisted.studentInfo : cachedStudentInfo

  return {
    loading: !(persisted || studentInfo),
    refreshing: false,
    userInfo: persisted ? persisted.userInfo : null,
    studentInfo: studentInfo || null,
  }
}

Component({
  data: buildInitialData(),

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 4 })
      }
      const persisted = getMePageState()
      ;(this as any)._meLoaded = false
      ;(this as any)._meHasCache = !!(persisted || getUserInfo())
      ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 4 })
      }
      const self = this as any
      const hasContent = !!this.data.studentInfo

      if (!self._meLoaded) {
        this.loadData({ showLoading: !self._meHasCache && !hasContent })
        return
      }

      if (!hasContent) {
        this.loadData({ showLoading: true })
        return
      }

      if (Date.now() - (self._lastLoadedAt || 0) > ME_REFRESH_TTL) {
        this.loadData({ showLoading: false })
      }
    },
  },

  methods: {
    persistState() {
      const updatedAt = Date.now()
      setMePageState({
        userInfo: this.data.userInfo,
        studentInfo: this.data.studentInfo,
        updatedAt,
      })
      ;(this as any)._lastLoadedAt = updatedAt
    },

    async loadData(options?: { showLoading?: boolean }) {
      if (!app.globalData.isAuthenticated && !hasSessionId()) {
        wx.redirectTo({ url: '/pages/login/login' })
        return
      }

      const showLoading = !!(options && options.showLoading)
      if (showLoading) {
        this.setData({ loading: true })
      } else {
        this.setData({ refreshing: true })
      }

      // Try cached first
      const cached = getUserInfo()
      if (cached) {
        this.setData({ studentInfo: cached })
        app.globalData.userInfo = cached
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
        ;(this as any)._meLoaded = true
        this.persistState()
      } catch (_e) {
        // Use cached data
      } finally {
        if (showLoading) {
          this.setData({ loading: false })
        } else {
          this.setData({ refreshing: false })
        }
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

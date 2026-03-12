import { get } from '../../services/api'
import { getGradesPageState, hasSessionId, setGradesPageState } from '../../utils/storage'

const app = getApp<IAppOption>()
const GRADES_REFRESH_TTL = 5 * 60 * 1000

function buildInitialData() {
  const persisted = getGradesPageState()

  return {
    loading: !persisted,
    refreshing: false,
    grades: persisted && Array.isArray(persisted.grades) ? persisted.grades : ([] as any[]),
    gpaStats: persisted && persisted.gpaStats ? persisted.gpaStats : {
      gpa: 0,
      total_credits: 0,
      passed_credits: 0,
      failed_count: 0,
    },
  }
}

Component({
  data: buildInitialData(),

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 2 })
      }
      const persisted = getGradesPageState()
      ;(this as any)._gradesLoaded = false
      ;(this as any)._gradesHasCache = !!persisted
      ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 2 })
      }
      const self = this as any
      const hasContent = this.data.grades.length > 0

      if (!self._gradesLoaded) {
        this.loadGrades({ showLoading: !self._gradesHasCache && !hasContent })
        return
      }

      if (!hasContent) {
        this.loadGrades({ showLoading: true })
        return
      }

      if (Date.now() - (self._lastLoadedAt || 0) > GRADES_REFRESH_TTL) {
        this.loadGrades({ showLoading: false })
      }
    },
  },

  methods: {
    persistState() {
      const updatedAt = Date.now()
      setGradesPageState({
        grades: this.data.grades,
        gpaStats: this.data.gpaStats,
        updatedAt,
      })
      ;(this as any)._lastLoadedAt = updatedAt
    },

    async loadGrades(options?: { showLoading?: boolean }) {
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
      try {
        const res = await get('/api/grades/list', { page_size: 200 })
        const grades = (res.grades || []).map((g: any) => ({
          ...g,
          scoreColor: this.getScoreColor(g.xscj || g.score || ''),
        }))
        this.setData({
          grades,
          gpaStats: res.gpa_stats || this.data.gpaStats,
        })
        ;(this as any)._gradesLoaded = true
        this.persistState()
      } catch (err: any) {
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

    getScoreColor(score: string): string {
      const num = parseFloat(score)
      if (isNaN(num)) return ''
      if (num >= 90) return 'score-green'
      if (num >= 80) return 'score-blue'
      if (num >= 70) return 'score-orange'
      return 'score-red'
    },

    onGradeClick(e: any) {
      const idx = e.currentTarget.dataset.index
      const grade = this.data.grades[idx]
      if (!grade) return
      wx.showModal({
        title: grade.kcmc || grade.course_name || '',
        content: [
          `成绩: ${grade.xscj || grade.score || '--'}`,
          `学分: ${grade.xf || grade.credit || '--'}`,
          `学时: ${grade.xs || '--'}`,
          `性质: ${grade.kcxzmc || '--'}`,
          `类别: ${grade.kclbmc || '--'}`,
          `教师: ${grade.jsxm || '--'}`,
          `开课单位: ${grade.kkdw || '--'}`,
        ].join('\n'),
        showCancel: false,
      })
    },
  },
})

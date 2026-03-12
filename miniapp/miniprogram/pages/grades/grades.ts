import { get } from '../../services/api'
import { hasSessionId } from '../../utils/storage'

const app = getApp<IAppOption>()

Component({
  data: {
    loading: true,
    grades: [] as any[],
    gpaStats: {
      gpa: 0,
      total_credits: 0,
      passed_credits: 0,
      failed_count: 0,
    },
  },

  lifetimes: {
    attached() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 2 })
      }
    },
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function') {
        this.getTabBar().setData({ selected: 2 })
      }
      if (this.data.grades.length === 0) {
        this.loadGrades()
      }
    },
  },

  methods: {
    async loadGrades() {
      if (!app.globalData.isAuthenticated && !hasSessionId()) {
        wx.redirectTo({ url: '/pages/login/login' })
        return
      }

      this.setData({ loading: true })
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
      } catch (err: any) {
        wx.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.setData({ loading: false })
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

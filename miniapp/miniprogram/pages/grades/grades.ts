import { get } from '../../services/api'
import type { components } from '../../services/openapi'
import { getGradesPageState, setGradesPageState } from '../../utils/storage'

const app = getApp<IAppOption>()
const GRADES_REFRESH_TTL = 5 * 60 * 1000
type GradeRecord = components['schemas']['GradeRecord']
type GradePage = components['schemas']['GradePage']
type GradeSummary = components['schemas']['GradeSummary']
type GradeComponent = components['schemas']['GradeComponent']
type DisplayGrade = GradeRecord & { scoreColor: string; rankText: string }

function buildInitialData() {
  const persisted = getGradesPageState()

  return {
    loading: !persisted,
    refreshing: false,
    grades: persisted && Array.isArray(persisted.grades)
      ? persisted.grades.map(grade => ({
        ...grade,
        scoreColor: getScoreColor(grade.score, grade.score_numeric),
        rankText: formatRank(grade.rank, grade.rank_total),
      }))
      : ([] as DisplayGrade[]),
    gpaStats: persisted && persisted.gpaStats ? persisted.gpaStats : {
      gpa: 0,
      total_credits: 0,
      passed_credits: 0,
      failed_count: 0,
    },
    selectedGrade: null as DisplayGrade | null,
    gradeComponents: [] as GradeComponent[],
    detailLoading: false,
    detailError: '',
    showDetail: false,
  }
}

function getScoreColor(score: string, scoreNumeric?: number | null): string {
  const num = scoreNumeric === null || scoreNumeric === undefined
    ? parseFloat(score)
    : scoreNumeric
  if (isNaN(num)) return ''
  if (num >= 90) return 'score-green'
  if (num >= 80) return 'score-blue'
  if (num >= 70) return 'score-orange'
  return 'score-red'
}

function formatRank(rank?: number | null, total?: number | null): string {
  if (rank === null || rank === undefined) return ''
  return total ? `${rank}/${total}` : String(rank)
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
        const [page, summary] = await Promise.all([
          get<GradePage>('/api/grades', { page_size: 100 }),
          get<GradeSummary>('/api/grades/summary'),
        ])
        const grades = (page.items || []).map((grade): DisplayGrade => ({
          ...grade,
          scoreColor: getScoreColor(grade.score, grade.score_numeric),
          rankText: formatRank(grade.rank, grade.rank_total),
        }))
        this.setData({
          grades,
          gpaStats: {
            gpa: summary.official_gpa || 0,
            total_credits: summary.earned_credits,
            passed_credits: summary.passed_courses,
            failed_count: summary.failed_courses,
          },
        })
        ;(this as any)._gradesLoaded = true
        this.persistState()
      } catch (_error) {
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

    async onScoreClick(e: any) {
      const idx = Number(e.currentTarget.dataset.index)
      const grade = this.data.grades[idx]
      if (!grade) return

      this.setData({
        selectedGrade: grade,
        gradeComponents: [],
        detailError: '',
        detailLoading: !!grade.task_id,
        showDetail: true,
      })

      if (!grade.task_id) {
        this.setData({ detailError: '该课程不支持成绩明细查询' })
        return
      }

      try {
        const components = await get<GradeComponent[]>(
          `/api/grades/${encodeURIComponent(grade.id)}/components`,
          { task_id: grade.task_id },
        )
        this.setData({ gradeComponents: components || [] })
      } catch (error: any) {
        this.setData({ detailError: error && error.message ? error.message : '获取成绩明细失败' })
      } finally {
        this.setData({ detailLoading: false })
      }
    },

    closeDetail() {
      this.setData({ showDetail: false })
    },

    noop() {},
  },
})

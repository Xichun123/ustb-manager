import { get } from '../../services/api'
import { getExamsPageState, hasSessionId, setExamsPageState } from '../../utils/storage'

const EXAMS_REFRESH_TTL = 10 * 60 * 1000

function buildInitialData() {
  const persisted = getExamsPageState()

  return {
    loading: !persisted,
    refreshing: false,
    exams: persisted && Array.isArray(persisted.exams) ? persisted.exams : ([] as any[]),
  }
}

Page({
  data: buildInitialData(),

  onLoad() {
    const persisted = getExamsPageState()
    ;(this as any)._examsLoaded = false
    ;(this as any)._examsHasCache = !!persisted
    ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
  },

  onShow() {
    const self = this as any
    const hasContent = this.data.exams.length > 0

    if (!self._examsLoaded) {
      this.loadExams({ showLoading: !self._examsHasCache && !hasContent })
      return
    }

    if (!hasContent) {
      this.loadExams({ showLoading: true })
      return
    }

    if (Date.now() - (self._lastLoadedAt || 0) > EXAMS_REFRESH_TTL) {
      this.loadExams({ showLoading: false })
    }
  },

  persistState() {
    const updatedAt = Date.now()
    setExamsPageState({
      exams: this.data.exams,
      updatedAt,
    })
    ;(this as any)._lastLoadedAt = updatedAt
  },

  async loadExams(options?: { showLoading?: boolean }) {
    if (!hasSessionId()) {
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
      const res = await get('/api/schedule/exams')
      const now = new Date()
      const today = now.toISOString().split('T')[0]

      const exams = (Array.isArray(res) ? res : []).map((exam: any) => {
        const isPast = exam.exam_date < today
        const isToday = exam.exam_date === today
        return { ...exam, isPast, isToday }
      })

      this.setData({ exams })
      ;(this as any)._examsLoaded = true
      this.persistState()
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

  onExamClick(e: any) {
    const idx = e.currentTarget.dataset.index
    const exam = this.data.exams[idx]
    if (!exam) return
    wx.showModal({
      title: exam.course_name,
      content: [
        `类型: ${exam.exam_type || '--'}`,
        `日期: ${exam.exam_date || '--'} ${exam.weekday || ''}`,
        `时间: ${exam.exam_time || '--'}`,
        `地点: ${exam.building || ''}${exam.room || ''}`,
        `校区: ${exam.campus || '--'}`,
        `周次: 第${exam.week_number || '--'}周`,
        exam.remark ? `备注: ${exam.remark}` : '',
      ].filter(Boolean).join('\n'),
      showCancel: false,
    })
  },
})

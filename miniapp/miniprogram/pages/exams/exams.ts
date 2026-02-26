import { get } from '../../services/api'

Page({
  data: {
    loading: true,
    exams: [] as any[],
  },

  onLoad() {
    this.loadExams()
  },

  async loadExams() {
    this.setData({ loading: true })
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
    } catch (_e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
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

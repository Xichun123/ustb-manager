import { get } from '../../services/api'

Page({
  data: {
    loading: true,
    viewMode: 'selected' as 'selected' | 'available',
    courses: [] as any[],
    totalCredits: 0,
    courseCount: 0,
    // Term info
    currentXn: '',
    currentXq: '',
    // Available courses filters
    methods: [
      { value: 'bx-b-b', label: '必修' },
      { value: 'mooc-b-b', label: 'MOOC' },
      { value: 'sztzk', label: '素质拓展' },
      { value: 'zytzk', label: '专业拓展' },
    ],
    selectedMethodIdx: 0,
    searchText: '',
  },

  onLoad() {
    this.init()
  },

  async init() {
    this.setData({ loading: true })
    try {
      const termInfo = await get('/api/courses/term-info')
      this.setData({
        currentXn: termInfo.p_xn || termInfo.p_dqxn,
        currentXq: termInfo.p_xq || termInfo.p_dqxq,
      })
      await this.loadCourses()
    } catch (_e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadCourses() {
    this.setData({ loading: true })
    const { viewMode, currentXn, currentXq, methods, selectedMethodIdx } = this.data

    try {
      let res: any
      if (viewMode === 'selected') {
        res = await get('/api/courses/selected', { xn: currentXn, xq: currentXq })
      } else {
        const method = methods[selectedMethodIdx].value
        res = await get('/api/courses/available', { xn: currentXn, xq: currentXq, method })
      }

      const courses = res.courses || []
      const totalCredits = courses.reduce((sum: number, c: any) => sum + (parseFloat(c.credits) || 0), 0)
      this.setData({
        courses,
        totalCredits,
        courseCount: courses.length,
      })
    } catch (_e) {
      this.setData({ courses: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  // View mode switch
  switchView(e: any) {
    const mode = e.currentTarget.dataset.mode
    this.setData({ viewMode: mode, courses: [] })
    this.loadCourses()
  },

  // Method filter change
  onMethodChange(e: any) {
    const idx = parseInt(e.detail.value)
    this.setData({ selectedMethodIdx: idx })
    this.loadCourses()
  },

  // Search
  onSearchInput(e: any) {
    this.setData({ searchText: e.detail.value })
  },

  // Course detail
  onCourseClick(e: any) {
    const idx = e.currentTarget.dataset.index
    const course = this.data.courses[idx]
    if (!course) return

    const lines = [
      `课程代码: ${course.course_code || '--'}`,
      `类型: ${course.course_type || '--'}`,
      `学分: ${course.credits || '--'}`,
      `学时: ${course.hours || '--'}`,
      `教师: ${course.teacher || '--'}`,
      `学院: ${course.college || '--'}`,
      `校区: ${course.campus || '--'}`,
      `容量: ${course.selected_count || '0'}/${course.capacity || '0'}`,
    ]

    if (course.selection_time) {
      lines.push(`选课时间: ${course.selection_time}`)
    }

    wx.showModal({
      title: course.course_name,
      content: lines.join('\n'),
      showCancel: false,
    })
  },
})

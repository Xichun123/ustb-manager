import { get, post } from '../../services/api'
import { getCoursesPageState, setCoursesPageState } from '../../utils/storage'

const app = getApp<IAppOption>()

function buildDefaultCategoryOptions() {
  return [{ value: '', label: '全部类别' }]
}

const COURSES_REFRESH_TTL = 5 * 60 * 1000

function buildInitialData() {
  const persisted = getCoursesPageState()

  return {
    loading: !persisted,
    refreshing: false,
    viewMode: persisted && persisted.viewMode ? persisted.viewMode : ('selected' as 'selected' | 'available'),
    rawCourses: persisted && Array.isArray(persisted.rawCourses) ? persisted.rawCourses : ([] as any[]),
    displayCourses: persisted && Array.isArray(persisted.displayCourses) ? persisted.displayCourses : ([] as any[]),
    totalCredits: persisted ? persisted.totalCredits : 0,
    totalHours: persisted ? persisted.totalHours : 0,
    courseCount: persisted ? persisted.courseCount : 0,
    collegeCount: persisted ? persisted.collegeCount : 0,
    currentXn: persisted ? persisted.currentXn : '',
    currentXq: persisted ? persisted.currentXq : '',
    termList: persisted && Array.isArray(persisted.termList) ? persisted.termList : ([] as Array<{ value: string; label: string }>),
    selectedTermIdx: persisted ? persisted.selectedTermIdx : 0,
    methods: [
      { value: 'bx-b-b', label: '必修课' },
      { value: 'mooc-b-b', label: 'MOOC' },
      { value: 'sztzk-b-b', label: '素质拓展课' },
      { value: 'zytzk-b-b', label: '专业拓展课' },
    ],
    selectedMethodIdx: persisted ? persisted.selectedMethodIdx : 0,
    colleges: persisted && Array.isArray(persisted.colleges)
      ? persisted.colleges
      : ([{ value: '', label: '全部学院' }] as Array<{ value: string; label: string }>),
    selectedCollegeIdx: persisted ? persisted.selectedCollegeIdx : 0,
    campuses: persisted && Array.isArray(persisted.campuses)
      ? persisted.campuses
      : ([{ value: '', label: '全部校区' }] as Array<{ value: string; label: string }>),
    selectedCampusIdx: persisted ? persisted.selectedCampusIdx : 0,
    categoryOptions: persisted && Array.isArray(persisted.categoryOptions)
      ? persisted.categoryOptions
      : (buildDefaultCategoryOptions() as Array<{ value: string; label: string }>),
    selectedCategoryIdx: persisted ? persisted.selectedCategoryIdx : 0,
    searchText: persisted ? persisted.searchText : '',
    announcements: persisted && Array.isArray(persisted.announcements) ? persisted.announcements : ([] as any[]),
    showAnnouncements: persisted ? persisted.showAnnouncements : false,
    selectingCourseId: '',
    droppingCourseId: '',
    checkingConflictId: '',
  }
}

Page({
  data: buildInitialData(),

  onLoad() {
    const persisted = getCoursesPageState()
    ;(this as any)._coursesLoaded = false
    ;(this as any)._coursesHasCache = !!persisted
    ;(this as any)._lastLoadedAt = persisted && persisted.updatedAt ? persisted.updatedAt : 0
  },

  onShow() {
    const self = this as any
    const hasContent = !!(
      this.data.termList.length > 0
      || this.data.rawCourses.length > 0
      || this.data.announcements.length > 0
    )

    if (!self._coursesLoaded) {
      this.init({ showLoading: !self._coursesHasCache && !hasContent })
      return
    }

    if (!hasContent) {
      this.init({ showLoading: true })
      return
    }

    if (Date.now() - (self._lastLoadedAt || 0) > COURSES_REFRESH_TTL) {
      this.init({ showLoading: false })
    }
  },

  persistState() {
    const updatedAt = Date.now()
    setCoursesPageState({
      viewMode: this.data.viewMode,
      rawCourses: this.data.rawCourses,
      displayCourses: this.data.displayCourses,
      totalCredits: this.data.totalCredits,
      totalHours: this.data.totalHours,
      courseCount: this.data.courseCount,
      collegeCount: this.data.collegeCount,
      currentXn: this.data.currentXn,
      currentXq: this.data.currentXq,
      termList: this.data.termList,
      selectedTermIdx: this.data.selectedTermIdx,
      selectedMethodIdx: this.data.selectedMethodIdx,
      colleges: this.data.colleges,
      selectedCollegeIdx: this.data.selectedCollegeIdx,
      campuses: this.data.campuses,
      selectedCampusIdx: this.data.selectedCampusIdx,
      categoryOptions: this.data.categoryOptions,
      selectedCategoryIdx: this.data.selectedCategoryIdx,
      searchText: this.data.searchText,
      announcements: this.data.announcements,
      showAnnouncements: this.data.showAnnouncements,
      updatedAt,
    })
    ;(this as any)._lastLoadedAt = updatedAt
  },

  async init(options?: { showLoading?: boolean }) {
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
      const results = await Promise.all([
        get('/api/courses/term-info'),
        get('/api/courses/term-list'),
        get('/api/courses/colleges').catch(() => []),
        get('/api/courses/campuses').catch(() => []),
      ])

      const termInfo = results[0]
      const termListRes = Array.isArray(results[1]) ? results[1] : []
      const collegesRes = Array.isArray(results[2]) ? results[2] : []
      const campusesRes = Array.isArray(results[3]) ? results[3] : []

      const currentXn = termInfo.p_xn || termInfo.p_dqxn || ''
      const currentXq = termInfo.p_xq || termInfo.p_dqxq || ''
      const selectedTermValue = termInfo.p_xnxq || (termListRes[0] && termListRes[0].dm) || ''

      const termList = termListRes.map((item: any) => ({
        value: item.dm,
        label: item.mc + (item.dm === termInfo.p_xnxq ? ' (选课)' : ''),
      }))

      let selectedTermIdx = 0
      for (let i = 0; i < termList.length; i += 1) {
        if (termList[i].value === selectedTermValue) {
          selectedTermIdx = i
          break
        }
      }

      const colleges = [{ value: '', label: '全部学院' }].concat(
        collegesRes.map((item: any) => ({ value: item.code, label: item.name }))
      )
      const campuses = [{ value: '', label: '全部校区' }].concat(
        campusesRes.map((item: any) => ({ value: item.code, label: item.name }))
      )

      await new Promise<void>((resolve) => {
        this.setData(
          {
            currentXn,
            currentXq,
            termList,
            selectedTermIdx,
            colleges,
            campuses,
          },
          () => resolve()
        )
      })

      await Promise.all([
        this.loadCourses({ showLoading: false }),
        this.loadAnnouncements(currentXn, currentXq),
      ])
      ;(this as any)._coursesLoaded = true
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

  getSelectedTermValue() {
    const term = this.data.termList[this.data.selectedTermIdx]
    return term ? term.value : ''
  },

  getSelectedMethodValue() {
    const method = this.data.methods[this.data.selectedMethodIdx]
    return method ? method.value : 'bx-b-b'
  },

  getSelectedCollegeValue() {
    const college = this.data.colleges[this.data.selectedCollegeIdx]
    return college ? college.value : ''
  },

  getSelectedCampusValue() {
    const campus = this.data.campuses[this.data.selectedCampusIdx]
    return campus ? campus.value : ''
  },

  getSelectedCategoryValue() {
    const category = this.data.categoryOptions[this.data.selectedCategoryIdx]
    return category ? category.value : ''
  },

  applyCourseFilters(rawCourses?: any[]) {
    const source = rawCourses || this.data.rawCourses
    const viewMode = this.data.viewMode
    const searchText = String(this.data.searchText || '').trim().toLowerCase()
    const selectedCategory = this.getSelectedCategoryValue()

    let displayCourses = source.slice()

    if (viewMode === 'available') {
      displayCourses = displayCourses.filter((item: any) => !item.is_selected)
    }

    if (selectedCategory) {
      displayCourses = displayCourses.filter((item: any) => item.category === selectedCategory)
    }

    if (searchText) {
      displayCourses = displayCourses.filter((item: any) => {
        const courseName = String(item.course_name || '').toLowerCase()
        const courseCode = String(item.course_code || '').toLowerCase()
        const teacher = String(item.teacher || '').toLowerCase()
        const college = String(item.college || '').toLowerCase()
        return courseName.indexOf(searchText) !== -1
          || courseCode.indexOf(searchText) !== -1
          || teacher.indexOf(searchText) !== -1
          || college.indexOf(searchText) !== -1
      })
    }

    const totalCredits = displayCourses.reduce((sum: number, item: any) => sum + (parseFloat(item.credits || '0') || 0), 0)
    const totalHours = displayCourses.reduce((sum: number, item: any) => sum + (parseFloat(item.hours || '0') || 0), 0)
    const collegeMap: Record<string, boolean> = {}
    displayCourses.forEach((item: any) => {
      const college = String(item.college || '').trim()
      if (college) {
        collegeMap[college] = true
      }
    })

    this.setData(
      {
        displayCourses,
        totalCredits: Number(totalCredits.toFixed(1)),
        totalHours,
        courseCount: displayCourses.length,
        collegeCount: Object.keys(collegeMap).length,
      },
      () => {
        this.persistState()
      }
    )
  },

  buildCategoryOptions(rawCourses: any[]) {
    const labels: string[] = []
    rawCourses.forEach((item: any) => {
      const label = String(item.category || '').trim()
      if (label && labels.indexOf(label) === -1) {
        labels.push(label)
      }
    })
    labels.sort()
    return buildDefaultCategoryOptions().concat(
      labels.map(label => ({ value: label, label }))
    )
  },

  async loadCourses(options?: { showLoading?: boolean }) {
    const showLoading = !!(options && options.showLoading)
    if (showLoading) {
      this.setData({ loading: true })
    }
    const selectedTermValue = this.getSelectedTermValue()
    const viewMode = this.data.viewMode
    const method = this.getSelectedMethodValue()
    const college = this.getSelectedCollegeValue()
    const campus = this.getSelectedCampusValue()

    let currentXn = this.data.currentXn
    let currentXq = this.data.currentXq
    if (selectedTermValue && selectedTermValue.length > 9) {
      currentXn = selectedTermValue.slice(0, 9)
      currentXq = selectedTermValue.slice(9)
    }

    try {
      let res: any
      if (viewMode === 'selected') {
        res = await get('/api/courses/selected', { xn: currentXn, xq: currentXq })
      } else {
        res = await get('/api/courses/available', {
          xn: currentXn,
          xq: currentXq,
          method,
          college,
          campus,
        })
      }

      const rawCourses = res && Array.isArray(res.courses) ? res.courses : []
      const categoryOptions = this.buildCategoryOptions(rawCourses)
      let selectedCategoryIdx = this.data.selectedCategoryIdx
      if (selectedCategoryIdx >= categoryOptions.length) {
        selectedCategoryIdx = 0
      }
      const selectedCategoryValue = this.getSelectedCategoryValue()
      let stillExists = false
      for (let i = 0; i < categoryOptions.length; i += 1) {
        if (categoryOptions[i].value === selectedCategoryValue) {
          stillExists = true
          selectedCategoryIdx = i
          break
        }
      }
      if (!stillExists) {
        selectedCategoryIdx = 0
      }

      this.setData(
        {
          currentXn,
          currentXq,
          rawCourses,
          categoryOptions,
          selectedCategoryIdx,
        },
        () => {
          this.applyCourseFilters(rawCourses)
        }
      )
      ;(this as any)._coursesLoaded = true
    } catch (_e) {
      if (showLoading) {
        this.setData({
          rawCourses: [],
          displayCourses: [],
          totalCredits: 0,
          totalHours: 0,
          courseCount: 0,
          collegeCount: 0,
          categoryOptions: buildDefaultCategoryOptions(),
          selectedCategoryIdx: 0,
        })
        this.persistState()
      }
      if (showLoading) {
        wx.showToast({
          title: viewMode === 'selected' ? '获取已选课程失败' : '获取可选课程失败',
          icon: 'none',
        })
      }
    } finally {
      if (showLoading) {
        this.setData({ loading: false })
      }
    }
  },

  async loadAnnouncements(xn: string, xq: string) {
    try {
      const res = await get('/api/courses/announcements', { xn, xq })
      const announcements = Array.isArray(res) ? res : []
      this.setData({
        announcements,
        showAnnouncements: announcements.length > 0,
      })
      this.persistState()
    } catch (_e) {
      if (!this.data.announcements.length) {
        this.setData({
          announcements: [],
          showAnnouncements: false,
        })
        this.persistState()
      }
    }
  },

  switchView(e: any) {
    const mode = e.currentTarget.dataset.mode
    this.setData(
      {
        viewMode: mode,
        rawCourses: [],
        displayCourses: [],
        searchText: '',
        selectedCollegeIdx: 0,
        selectedCampusIdx: 0,
        selectedCategoryIdx: 0,
        categoryOptions: buildDefaultCategoryOptions(),
      },
      () => {
        this.persistState()
        this.loadCourses({ showLoading: true })
      }
    )
  },

  onTermChange(e: any) {
    const selectedTermIdx = parseInt(e.detail.value, 10) || 0
    const term = this.data.termList[selectedTermIdx]
    let currentXn = this.data.currentXn
    let currentXq = this.data.currentXq
    if (term && term.value && term.value.length > 9) {
      currentXn = term.value.slice(0, 9)
      currentXq = term.value.slice(9)
    }
    this.setData(
      {
        selectedTermIdx,
        currentXn,
        currentXq,
        selectedCategoryIdx: 0,
        categoryOptions: buildDefaultCategoryOptions(),
      },
      () => {
        this.persistState()
        this.loadCourses({ showLoading: true })
        this.loadAnnouncements(currentXn, currentXq)
      }
    )
  },

  onMethodChange(e: any) {
    const selectedMethodIdx = parseInt(e.detail.value, 10) || 0
    this.setData(
      {
        selectedMethodIdx,
        selectedCollegeIdx: 0,
        selectedCampusIdx: 0,
        selectedCategoryIdx: 0,
        categoryOptions: buildDefaultCategoryOptions(),
      },
      () => {
        this.persistState()
        this.loadCourses({ showLoading: true })
      }
    )
  },

  onCollegeChange(e: any) {
    const selectedCollegeIdx = parseInt(e.detail.value, 10) || 0
    this.setData({ selectedCollegeIdx }, () => {
      this.persistState()
      this.loadCourses({ showLoading: true })
    })
  },

  onCampusChange(e: any) {
    const selectedCampusIdx = parseInt(e.detail.value, 10) || 0
    this.setData({ selectedCampusIdx }, () => {
      this.persistState()
      this.loadCourses({ showLoading: true })
    })
  },

  onCategoryChange(e: any) {
    const selectedCategoryIdx = parseInt(e.detail.value, 10) || 0
    this.setData({ selectedCategoryIdx }, () => {
      this.applyCourseFilters()
    })
  },

  onSearchInput(e: any) {
    this.setData({ searchText: e.detail.value || '' }, () => {
      this.applyCourseFilters()
    })
  },

  onCourseClick(e: any) {
    const idx = e.currentTarget.dataset.index
    const course = this.data.displayCourses[idx]
    if (!course) return

    const lines = [
      `课程代码: ${course.course_code || '--'}`,
      `课序号: ${course.class_number || '--'}`,
      `课程性质: ${course.course_type || '--'}`,
      `课程类别: ${course.category || '--'}`,
      `学分/学时: ${course.credits || '--'} / ${course.hours || '--'}`,
      `选课方式: ${course.selection_method || '--'}`,
      `教师: ${course.teacher || '--'}`,
      `学院: ${course.college || '--'}`,
      `校区: ${course.campus || '--'}`,
      `容量: ${course.selected_count || '0'}/${course.capacity || '0'}`,
    ]

    if (course.selection_time) {
      lines.push(`选课时间: ${course.selection_time}`)
    }
    if (course.withdraw_start || course.withdraw_end) {
      lines.push(`退选时间: ${(course.withdraw_start || '--')} ~ ${(course.withdraw_end || '--')}`)
    }
    if (course.schedule_time || course.schedule_location) {
      lines.push(`上课安排: ${(course.schedule_time || '--')} ${(course.schedule_location || '')}`.trim())
    }
    if (course.task_name) {
      lines.push(`任务名称: ${course.task_name}`)
    }
    if (course.selection_status) {
      lines.push(`状态: ${course.selection_status}`)
    }
    if (course.lottery_status) {
      lines.push(`抽签状态: ${course.lottery_status}`)
    }
    if (course.needs_payment) {
      lines.push('提示: 该课程需要缴费')
    }
    if (course.needs_approval) {
      lines.push('提示: 该课程需要审核')
    }

    wx.showModal({
      title: course.course_name,
      content: lines.join('\n'),
      showCancel: false,
    })
  },

  toggleAnnouncements() {
    this.setData({ showAnnouncements: !this.data.showAnnouncements }, () => {
      this.persistState()
    })
  },

  async onCheckConflict(e: any) {
    const idx = e.currentTarget.dataset.index
    const course = this.data.displayCourses[idx]
    if (!course) return

    const courseId = course.task_id
    const method = this.getSelectedMethodValue()

    this.setData({ checkingConflictId: course.task_id })
    try {
      const res = await post('/api/courses/check-conflict', {
        course_id: courseId,
        method,
      })

      if (res.has_conflict) {
        wx.showModal({
          title: '存在时间冲突',
          content: res.message || '该课程与已选课程存在时间冲突，请重新选择。',
          showCancel: false,
        })
      } else {
        wx.showToast({ title: '无时间冲突', icon: 'success' })
      }
    } catch (_e) {
      wx.showToast({ title: '检测失败', icon: 'none' })
    } finally {
      this.setData({ checkingConflictId: '' })
    }
  },

  async onSelectCourse(e: any) {
    const idx = e.currentTarget.dataset.index
    const course = this.data.displayCourses[idx]
    if (!course) return
    if (course.is_selected) {
      wx.showToast({ title: '该课程已选', icon: 'none' })
      return
    }

    const confirmed = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '确认选课',
        content: `确定选择“${course.course_name}”吗？`,
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false),
      })
    })
    if (!confirmed) return

    this.setData({ selectingCourseId: course.task_id })
    try {
      const res = await post('/api/courses/select', {
        course_id: course.task_id,
        method: this.getSelectedMethodValue(),
      })
      if (res.success) {
        wx.showToast({ title: '选课成功', icon: 'success' })
        await this.loadCourses({ showLoading: false })
      } else {
        wx.showToast({ title: res.message || '选课失败', icon: 'none' })
      }
    } catch (err: any) {
      wx.showToast({ title: err.message || '选课失败', icon: 'none' })
    } finally {
      this.setData({ selectingCourseId: '' })
    }
  },

  async onDropCourse(e: any) {
    const idx = e.currentTarget.dataset.index
    const course = this.data.displayCourses[idx]
    if (!course) return

    const confirmed = await new Promise<boolean>((resolve) => {
      wx.showModal({
        title: '确认退课',
        content: `确定退选“${course.course_name}”吗？`,
        confirmText: '确认退课',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false),
      })
    })
    if (!confirmed) return

    this.setData({ droppingCourseId: course.task_id })
    try {
      const res = await post('/api/courses/drop', {
        course_id: course.internal_id || course.task_id,
        method: course.selection_method_code || this.getSelectedMethodValue(),
      })
      if (res.success) {
        wx.showToast({ title: '退课成功', icon: 'success' })
        await this.loadCourses({ showLoading: false })
      } else {
        wx.showToast({ title: res.message || '退课失败', icon: 'none' })
      }
    } catch (err: any) {
      wx.showToast({ title: err.message || '退课失败', icon: 'none' })
    } finally {
      this.setData({ droppingCourseId: '' })
    }
  },
})

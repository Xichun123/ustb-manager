import { del, get, post } from '../../services/api'
import type { components } from '../../services/openapi'
import { getCoursesPageState, setCoursesPageState } from '../../utils/storage'

const app = getApp<IAppOption>()

type CourseSelectionRecord = components['schemas']['CourseSelectionRecord']
type CourseSelectionContext = components['schemas']['app__models__courses__CourseSelectionContext']
type CoursePage =
  | components['schemas']['CourseSelectionPage']
  | components['schemas']['SelectedCoursePage']
type CourseWriteResponse = components['schemas']['CourseWriteResponse']
type PreflightResponse = components['schemas']['CoursePreflightResponse']
type CourseAnnouncement = components['schemas']['CourseAnnouncement']

function idempotencyKey() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

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
    rawCourses: persisted && Array.isArray(persisted.rawCourses) ? persisted.rawCourses : ([] as CourseSelectionRecord[]),
    displayCourses: persisted && Array.isArray(persisted.displayCourses) ? persisted.displayCourses : ([] as CourseSelectionRecord[]),
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
    announcements: persisted && Array.isArray(persisted.announcements) ? persisted.announcements : ([] as CourseAnnouncement[]),
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
      const context = await get<CourseSelectionContext>('/api/course-selection/context')
      const currentXn = context.term.year
      const currentXq = context.term.semester
      const termList = [{
        value: context.term.code,
        label: `${context.term.year} 第${context.term.semester}学期 (选课)`,
      }]
      const methods = (context.methods || []).map(item => ({ value: item.code, label: item.name }))
      const colleges = [{ value: '', label: '全部学院' }].concat(
        (context.colleges || []).map(item => ({ value: item.code, label: item.name }))
      )
      const campuses = [{ value: '', label: '全部校区' }].concat(
        (context.campuses || []).map(item => ({ value: item.code, label: item.name }))
      )
      const categoryOptions = buildDefaultCategoryOptions().concat(
        (context.categories || []).map(item => ({ value: item.code, label: item.name }))
      )

      await new Promise<void>((resolve) => {
        this.setData(
          {
            currentXn,
            currentXq,
            termList,
            selectedTermIdx: 0,
            methods,
            colleges,
            campuses,
            categoryOptions,
          },
          () => resolve()
        )
      })

      await Promise.all([
        this.loadCourses({ showLoading: false }),
        this.loadAnnouncements(),
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

  applyCourseFilters(rawCourses?: CourseSelectionRecord[]) {
    const source = rawCourses || this.data.rawCourses
    const viewMode = this.data.viewMode
    const searchText = String(this.data.searchText || '').trim().toLowerCase()
    let displayCourses = source.slice()

    if (viewMode === 'available') {
      displayCourses = displayCourses.filter((item: CourseSelectionRecord) => !item.is_selected)
    }

    if (searchText) {
      displayCourses = displayCourses.filter((item: CourseSelectionRecord) => {
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

    const totalCredits = displayCourses.reduce((sum: number, item: CourseSelectionRecord) => sum + item.credits, 0)
    const totalHours = displayCourses.reduce((sum: number, item: CourseSelectionRecord) => sum + (item.hours || 0), 0)
    const collegeMap: Record<string, boolean> = {}
    displayCourses.forEach((item: CourseSelectionRecord) => {
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
    const category = this.getSelectedCategoryValue()

    let currentXn = this.data.currentXn
    let currentXq = this.data.currentXq
    if (selectedTermValue && selectedTermValue.length > 9) {
      currentXn = selectedTermValue.slice(0, 9)
      currentXq = selectedTermValue.slice(-1)
    }

    try {
      let res: CoursePage
      if (viewMode === 'selected') {
        res = await get<CoursePage>('/api/course-selection/selected', {
          year: currentXn,
          semester: currentXq,
        })
      } else {
        res = await get<CoursePage>('/api/course-selection/courses', {
          year: currentXn,
          semester: currentXq,
          method,
          college,
          category,
          campus,
          page: 1,
          page_size: 100,
        })
      }

      const rawCourses = res && Array.isArray(res.items) ? res.items : []
      this.setData(
        {
          currentXn,
          currentXq,
          rawCourses,
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

  async loadAnnouncements() {
    try {
      const announcements = await get<CourseAnnouncement[]>('/api/course-selection/announcements')
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
      currentXq = term.value.slice(-1)
    }
    this.setData(
      {
        selectedTermIdx,
        currentXn,
        currentXq,
        selectedCategoryIdx: 0,
      },
      () => {
        this.persistState()
        this.loadCourses({ showLoading: true })
        this.loadAnnouncements()
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
      this.persistState()
      this.loadCourses({ showLoading: true })
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
      `课程性质: ${course.course_nature || '--'}`,
      `课程类别: ${course.course_category || '--'}`,
      `学分/学时: ${course.credits || '--'} / ${course.hours || '--'}`,
      `选课方式: ${course.method || '--'}`,
      `教师: ${course.teacher || '--'}`,
      `学院: ${course.college || '--'}`,
      `校区: ${course.campus || '--'}`,
      `容量: ${course.selected_count || '0'}/${course.capacity || '0'}`,
    ]

    if (course.schedule_time || course.schedule_location) {
      lines.push(`上课安排: ${(course.schedule_time || '--')} ${(course.schedule_location || '')}`.trim())
    }
    if (course.selection_status) {
      lines.push(`状态: ${course.selection_status}`)
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

    const courseId = course.course_id
    const method = this.getSelectedMethodValue()

    this.setData({ checkingConflictId: course.course_id })
    try {
      const res = await post<PreflightResponse>('/api/course-selection/preflight', {
        course_id: courseId,
        method,
      })

      if (!res.allowed) {
        wx.showModal({
          title: res.status === 'conflict' ? '存在时间冲突' : '暂不可选',
          content: res.message || '该课程当前不可选择。',
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

    this.setData({ selectingCourseId: course.course_id })
    try {
      const res = await post<CourseWriteResponse>(
        '/api/course-selection/selections',
        {
          course_id: course.course_id,
          method: this.getSelectedMethodValue(),
        },
        { header: { 'Idempotency-Key': idempotencyKey() } }
      )
      if (res.success) {
        wx.showToast({ title: '选课成功', icon: 'success' })
        await this.loadCourses({ showLoading: false })
      } else {
        wx.showToast({ title: res.message || '选课失败', icon: 'none' })
      }
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : '选课失败', icon: 'none' })
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

    this.setData({ droppingCourseId: course.course_id })
    try {
      const selectionId = course.selection_id || course.course_id
      const res = await del<CourseWriteResponse>(
        `/api/course-selection/selections/${encodeURIComponent(selectionId)}`,
        undefined,
        { header: { 'Idempotency-Key': idempotencyKey() } }
      )
      if (res.success) {
        wx.showToast({ title: '退课成功', icon: 'success' })
        await this.loadCourses({ showLoading: false })
      } else {
        wx.showToast({ title: res.message || '退课失败', icon: 'none' })
      }
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : '退课失败', icon: 'none' })
    } finally {
      this.setData({ droppingCourseId: '' })
    }
  },
})

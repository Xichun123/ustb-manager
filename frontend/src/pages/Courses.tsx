import { useEffect, useState, useMemo, useCallback } from 'react'
import { Card, Table, Select, Spin, Tag, Statistic, Row, Col, Modal, Descriptions, Input, Tooltip, message, Tabs, Alert, Button, Space } from 'antd'
import { BookOutlined, ClockCircleOutlined, TeamOutlined, BankOutlined, CheckCircleOutlined, NotificationOutlined, ThunderboltOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'
import AppLayout from '../components/AppLayout'

type Course = components['schemas']['CourseSelectionRecord']
type CourseContext = components['schemas']['app__models__courses__CourseSelectionContext']
type CoursePage = components['schemas']['CourseSelectionPage']
type SelectedCoursePage = components['schemas']['SelectedCoursePage']
type PreflightResponse = components['schemas']['CoursePreflightResponse']
type WriteResponse = components['schemas']['CourseWriteResponse']
type SnatchTask = components['schemas']['CourseSnatchTask']
type Announcement = components['schemas']['CourseAnnouncement']

interface TermListItem {
  dm: string
  mc: string
}

interface FilterOption {
  code: string
  name: string
}

// 课程性质颜色
const COURSE_TYPE_COLORS: Record<string, string> = {
  '必修': 'red',
  '任选': 'green',
  '限选': 'orange',
}

// 选课方式颜色
const SELECTION_METHOD_COLORS: Record<string, string> = {
  '必修': 'blue',
  'MOOC': 'purple',
  '体育': 'cyan',
  '选修': 'green',
  '素质拓展课': 'magenta',
  '专业拓展课': 'gold',
}

const idempotencyKey = () => crypto.randomUUID()

const quotaColor = (selected?: number | null, capacity?: number | null) => {
  if (selected == null || capacity == null || capacity <= 0) return 'default'
  const percent = selected / capacity
  return percent >= 1 ? 'red' : percent >= 0.8 ? 'orange' : 'green'
}

const quotaTag = (
  label: string,
  selected?: number | null,
  capacity?: number | null,
) => (
  <Tag color={quotaColor(selected, capacity)} style={{ marginInlineEnd: 0 }}>
    {label} {selected ?? '-'}/{capacity ?? '-'}
  </Tag>
)

const defaultSnatchStart = () => {
  const target = new Date()
  target.setHours(15, 0, 0, 0)
  const local = new Date(target.getTime() - target.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

const SNATCH_STATUS_LABELS: Record<SnatchTask['status'], string> = {
  scheduled: '等待开始',
  running: '抢课中',
  completed: '全部成功',
  completed_with_errors: '部分失败',
  stopped: '已停止',
  failed: '任务失败',
}

const SNATCH_ERROR_LABELS: Record<
  NonNullable<NonNullable<SnatchTask['items']>[number]['error_type']>,
  string
> = {
  conflict: '时间冲突',
  full: '容量已满',
  not_open: '尚未开放',
  not_eligible: '不符合选课条件',
  already_selected: '已选待确认',
  unknown: '未知失败',
}

export default function CoursesPage() {
  const [loading, setLoading] = useState(true)
  const [courses, setCourses] = useState<Course[]>([])
  const [courseContext, setCourseContext] = useState<CourseContext | null>(null)
  const [termList, setTermList] = useState<TermListItem[]>([])
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null)
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')

  // 新增：视图模式和筛选条件
  const [viewMode, setViewMode] = useState<'selected' | 'available'>('selected')
  const [courseMethod, setCourseMethod] = useState('bx-b-b')
  const [coursePage, setCoursePage] = useState(1)
  const [coursePageSize, setCoursePageSize] = useState(100)
  const [availableCourseTotal, setAvailableCourseTotal] = useState(0)
  const [colleges, setColleges] = useState<FilterOption[]>([])
  const [campuses, setCampuses] = useState<FilterOption[]>([])
  const [categories, setCategories] = useState<FilterOption[]>([])
  const [filterCollege, setFilterCollege] = useState<string | undefined>()
  const [filterCategory, setFilterCategory] = useState<string | undefined>()
  const [filterCampus, setFilterCampus] = useState<string | undefined>()
  const [filterFacing, setFilterFacing] = useState('0')

  // 公告
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [showAnnouncements, setShowAnnouncements] = useState(true)

  // 冲突检测
  const [checkingConflict, setCheckingConflict] = useState<string | null>(null)

  // 选课/退课操作中
  const [selectingCourse, setSelectingCourse] = useState<string | null>(null)
  const [droppingCourse, setDroppingCourse] = useState<string | null>(null)

  // 多选定时抢课
  const [selectedCourseKeys, setSelectedCourseKeys] = useState<string[]>([])
  const [selectedCourseMap, setSelectedCourseMap] = useState<Record<string, Course>>({})
  const [snatchModalOpen, setSnatchModalOpen] = useState(false)
  const [snatchStartAt, setSnatchStartAt] = useState(defaultSnatchStart)
  const [creatingSnatchTask, setCreatingSnatchTask] = useState(false)
  const [stoppingSnatchTask, setStoppingSnatchTask] = useState(false)
  const [snatchTask, setSnatchTask] = useState<SnatchTask | null>(null)

  const categoryOptions = useMemo(
    () => categories.map(category => ({ value: category.code, label: category.name })),
    [categories],
  )
  const isProfessionalDevelopment = courseMethod.startsWith('zytzk')

  // 筛选后的课程
  const filteredCourses = useMemo(() => {
    let result = courses

    // 在可选课程模式下，只显示未选的课程
    if (viewMode === 'available') {
      result = result.filter(c => !c.is_selected)
    }

    // 已选课程没有服务端分页，在本地搜索；可选课程由后端搜索全部结果。
    if (viewMode === 'selected' && searchText) {
      const lower = searchText.toLowerCase()
      result = result.filter(c =>
        c.course_name.toLowerCase().includes(lower) ||
        c.course_code.toLowerCase().includes(lower) ||
        c.teacher.toLowerCase().includes(lower) ||
        c.college.toLowerCase().includes(lower)
      )
    }

    return result
  }, [courses, searchText, viewMode])

  // 统计信息
  const stats = useMemo(() => {
    const types: Record<string, number> = {}
    const methods: Record<string, number> = {}
    filteredCourses.forEach(c => {
      types[c.course_nature] = (types[c.course_nature] || 0) + 1
      methods[c.method] = (methods[c.method] || 0) + 1
    })
    return { types, methods }
  }, [filteredCourses])

  // 初始化：由后端动态上下文提供学期、方式和筛选项
  useEffect(() => {
    const init = async () => {
      try {
        const contextRes = await api.get<CourseContext>('/course-selection/context')
        const context = contextRes.data
        setCourseContext(context)
        setColleges(context.colleges || [])
        setCategories(context.categories || [])
        setCampuses(context.campuses || [])
        setCourseMethod(context.methods?.[0]?.code || 'bx-b-b')
        setTermList([
          {
            dm: context.term.code,
            mc: `${context.term.year} 第${context.term.semester}学期`,
          },
        ])
        setSelectedTerm(context.term.code)

        try {
          const announcementsRes = await api.get<Announcement[]>(
            '/course-selection/announcements',
          )
          setAnnouncements(Array.isArray(announcementsRes.data) ? announcementsRes.data : [])
        } catch {
          // 公告加载失败不影响主功能
        }
      } catch (err) {
        console.error('Failed to init courses:', err)
        message.error('获取选课上下文失败')
      }
    }
    init()
  }, [])

  useEffect(() => {
    api.get<SnatchTask>('/course-selection/snatch-tasks/active')
      .then(res => setSnatchTask(res.data))
      .catch(() => {
        // 没有活动任务时接口返回 404，无需提示。
      })
  }, [])

  // 加载课程
  useEffect(() => {
    if (!selectedTerm) return

    const fetchCourses = async () => {
      setLoading(true)
      setCourses([])
      try {
        const year = selectedTerm.slice(0, 9)
        const semester = selectedTerm.slice(-1)
        if (viewMode === 'selected') {
          const res = await api.get<SelectedCoursePage>('/course-selection/selected', {
            params: { year, semester },
          })
          setCourses(res.data.items || [])
        } else {
          const res = await api.get<CoursePage>('/course-selection/courses', {
            params: {
              year,
              semester,
              method: courseMethod,
              college: filterCollege,
              category: filterCategory,
              campus: filterCampus,
              keyword: searchKeyword,
              facing: isProfessionalDevelopment ? filterFacing : '0',
              page: coursePage,
              page_size: coursePageSize,
            },
          })
          setCourses(res.data.items || [])
          setAvailableCourseTotal(res.data.total || 0)
        }
      } catch (err) {
        console.error('Failed to fetch courses:', err)
        message.error(viewMode === 'selected' ? '获取已选课程失败' : '获取可选课程失败')
      } finally {
        setLoading(false)
      }
    }
    fetchCourses()
  }, [selectedTerm, viewMode, courseMethod, isProfessionalDevelopment, filterCollege, filterCategory, filterCampus, filterFacing, searchKeyword, coursePage, coursePageSize])

  useEffect(() => {
    if (!snatchTask || !['scheduled', 'running'].includes(snatchTask.status)) return

    let disposed = false
    const refresh = async () => {
      try {
        const res = await api.get<SnatchTask>(
          `/course-selection/snatch-tasks/${snatchTask.task_id}`,
        )
        if (disposed) return
        setSnatchTask(res.data)
        const successfulIds = new Set(
          (res.data.items || []).filter(item => item.status === 'success').map(item => item.course_id),
        )
        if (successfulIds.size) {
          setCourses(prev => prev.map(course =>
            successfulIds.has(course.course_id) ? { ...course, is_selected: true } : course
          ))
          setSelectedCourseKeys(prev => prev.filter(key => !successfulIds.has(key)))
          setSelectedCourseMap(prev => {
            const next = { ...prev }
            successfulIds.forEach(id => delete next[id])
            return next
          })
        }
      } catch (err) {
        console.error('Failed to refresh snatch task:', err)
      }
    }

    const timer = window.setInterval(refresh, 1000)
    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [snatchTask?.task_id, snatchTask?.status])

  const selectedCourses = useMemo(
    () => selectedCourseKeys.map(key => selectedCourseMap[key]).filter(Boolean),
    [selectedCourseKeys, selectedCourseMap],
  )

  const clearSelectedCourses = () => {
    setSelectedCourseKeys([])
    setSelectedCourseMap({})
  }

  const handleCourseSelectionChange = (keys: React.Key[]) => {
    const nextKeys = keys.map(String).slice(0, 10)
    if (keys.length > 10) message.warning('单个抢课任务最多选择 10 门课程')
    setSelectedCourseKeys(nextKeys)
    setSelectedCourseMap(prev => {
      const next = { ...prev }
      courses.forEach(course => {
        if (nextKeys.includes(course.course_id)) next[course.course_id] = course
        else delete next[course.course_id]
      })
      return next
    })
  }

  const handleCreateSnatchTask = async () => {
    if (!selectedCourses.length) {
      message.warning('请先选择要抢的课程')
      return
    }
    const startAt = new Date(snatchStartAt)
    if (Number.isNaN(startAt.getTime())) {
      message.error('请选择有效的开始时间')
      return
    }

    setCreatingSnatchTask(true)
    try {
      const res = await api.post<SnatchTask>(
        '/course-selection/snatch-tasks',
        {
          start_at: startAt.toISOString(),
          retry_interval_seconds: 1,
          courses: selectedCourses.map(course => ({
            course_id: course.course_id,
            selection_id: course.selection_id,
            course_code: course.course_code,
            course_name: course.course_name,
            method: courseMethod,
          })),
        },
        { headers: { 'Idempotency-Key': idempotencyKey() } },
      )
      setSnatchTask(res.data)
      setSnatchModalOpen(false)
      message.success('定时抢课任务已创建')
    } catch (err: unknown) {
      message.error(getApiErrorMessage(err, '创建抢课任务失败'))
    } finally {
      setCreatingSnatchTask(false)
    }
  }

  const handleStopSnatchTask = async () => {
    if (!snatchTask) return
    setStoppingSnatchTask(true)
    try {
      const res = await api.delete<SnatchTask>(
        `/course-selection/snatch-tasks/${snatchTask.task_id}`,
      )
      setSnatchTask(res.data)
      message.success('抢课任务已停止')
    } catch (err: unknown) {
      message.error(getApiErrorMessage(err, '停止抢课任务失败'))
    } finally {
      setStoppingSnatchTask(false)
    }
  }

  // 显示课程详情
  const handleCourseClick = (course: Course) => {
    setSelectedCourse(course)
    setModalVisible(true)
  }

  // 切换视图模式时重置筛选
  const handleViewModeChange = (mode: string) => {
    setViewMode(mode as 'selected' | 'available')
    setSearchText('')
    setSearchKeyword('')
    setCoursePage(1)
    setFilterCollege(undefined)
    setFilterCategory(undefined)
    setFilterCampus(undefined)
    setFilterFacing('0')
    clearSelectedCourses()
  }

  const handleAvailablePageChange = (page: number, pageSize: number) => {
    setCoursePage(pageSize === coursePageSize ? page : 1)
    setCoursePageSize(pageSize)
  }

  const handleAvailableSearch = (value: string) => {
    setSearchText(value)
    setSearchKeyword(value.trim())
    setCoursePage(1)
  }

  // 冲突检测
  const handleCheckConflict = useCallback(async (course: Course) => {
    setCheckingConflict(course.course_id)
    try {
      const res = await api.post<PreflightResponse>('/course-selection/preflight', {
        course_id: course.course_id,
        selection_id: course.selection_id,
        method: courseMethod,
      })
      if (!res.data.allowed) {
        Modal.warning({
          title: res.data.status === 'conflict' ? '存在时间冲突' : '暂不可选',
          content: res.data.message || `"${course.course_name}" 当前不可选择`,
        })
      } else {
        message.success(`"${course.course_name}" 无时间冲突`)
      }
    } catch {
      message.error('冲突检测失败')
    } finally {
      setCheckingConflict(null)
    }
  }, [courseMethod])

  // 选课
  const handleSelectCourse = useCallback(async (course: Course) => {
    setSelectingCourse(course.course_id)
    try {
      const res = await api.post<WriteResponse>(
        '/course-selection/selections',
        {
          course_id: course.course_id,
          selection_id: course.selection_id,
          method: courseMethod,
        },
        { headers: { 'Idempotency-Key': idempotencyKey() } },
      )
      message.success(res.data.message || `"${course.course_name}" 选课成功`)
      setCourses(prev => prev.map(c =>
        c.course_id === course.course_id ? { ...c, is_selected: true } : c
      ))
    } catch (err: unknown) {
      message.error(getApiErrorMessage(err, '选课失败'))
    } finally {
      setSelectingCourse(null)
    }
  }, [courseMethod])

  // 退课
  const handleDropCourse = useCallback(async (course: Course) => {
    Modal.confirm({
      title: '确认退课',
      content: `确定要退选 "${course.course_name}" 吗？`,
      okText: '确认退课',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setDroppingCourse(course.course_id)
        try {
          const selectionId = course.selection_id || course.course_id
          const res = await api.delete<WriteResponse>(
            `/course-selection/selections/${encodeURIComponent(selectionId)}`,
            { headers: { 'Idempotency-Key': idempotencyKey() } },
          )
          message.success(res.data.message || `"${course.course_name}" 退课成功`)
          setCourses(prev => prev.filter(c => c.course_id !== course.course_id))
        } catch (err: unknown) {
          message.error(getApiErrorMessage(err, '退课失败'))
        } finally {
          setDroppingCourse(null)
        }
      },
    })
  }, [])

  // 表格列定义
  const columns: ColumnsType<Course> = [
    {
      title: '课程代码',
      dataIndex: 'course_code',
      key: 'course_code',
      width: 100,
      fixed: 'left',
    },
    {
      title: '课程名称',
      dataIndex: 'course_name',
      key: 'course_name',
      width: 200,
      fixed: 'left',
      render: (text, record) => (
        <a onClick={() => handleCourseClick(record)}>{text}</a>
      ),
    },
    {
      title: '课程性质',
      dataIndex: 'course_nature',
      key: 'course_nature',
      width: 80,
      render: (text) => (
        <Tag color={COURSE_TYPE_COLORS[text] || 'default'}>{text}</Tag>
      ),
      filters: Object.keys(stats.types).map(t => ({ text: t, value: t })),
      onFilter: (value, record) => record.course_nature === value,
    },
    {
      title: '课程类别',
      dataIndex: 'course_category',
      key: 'course_category',
      width: 120,
      ellipsis: true,
    },
    {
      title: '学分',
      dataIndex: 'credits',
      key: 'credits',
      width: 60,
      align: 'center',
      sorter: (a, b) => a.credits - b.credits,
    },
    {
      title: '学时',
      dataIndex: 'hours',
      key: 'hours',
      width: 60,
      align: 'center',
    },
    {
      title: '选课方式',
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (text) => (
        <Tag color={SELECTION_METHOD_COLORS[text] || 'default'}>{text}</Tag>
      ),
      filters: Object.keys(stats.methods).map(m => ({ text: m, value: m })),
      onFilter: (value, record) => record.method === value,
    },
    {
      title: '教师',
      dataIndex: 'teacher',
      key: 'teacher',
      width: 100,
      ellipsis: true,
    },
    {
      title: '开课学院',
      dataIndex: 'college',
      key: 'college',
      width: 120,
      ellipsis: true,
    },
    {
      title: '校区',
      dataIndex: 'campus',
      key: 'campus',
      width: 80,
    },
    {
      title: (
        <Tooltip title="实时已占人数 / 容量上限">
          <span>实时容量</span>
        </Tooltip>
      ),
      key: 'capacity',
      width: 190,
      render: (_, record) => {
        const hasInternal = record.internal_capacity != null
          || record.internal_selected_count != null
        const hasExternal = record.external_capacity != null
          || record.external_selected_count != null
        return (
          <Space direction="vertical" size={4}>
            {quotaTag('总', record.selected_count, record.capacity)}
            {(hasInternal || hasExternal) && (
              <Space size={4}>
                {hasInternal && quotaTag(
                  '对内',
                  record.internal_selected_count,
                  record.internal_capacity,
                )}
                {hasExternal && quotaTag(
                  '对外',
                  record.external_selected_count,
                  record.external_capacity,
                )}
              </Space>
            )}
          </Space>
        )
      },
    },
    ...(viewMode === 'selected' ? [{
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right' as const,
      render: (_: unknown, record: Course) => (
        <Button
          type="link"
          size="small"
          danger
          loading={droppingCourse === record.course_id}
          onClick={(e) => { e.stopPropagation(); handleDropCourse(record) }}
        >
          退课
        </Button>
      ),
    }] : [{
      title: '操作',
      key: 'action',
      width: 160,
      fixed: 'right' as const,
      render: (_: unknown, record: Course) => (
        <Space>
          <Button
            type="link"
            size="small"
            loading={selectingCourse === record.course_id}
            disabled={record.is_selected}
            onClick={(e) => { e.stopPropagation(); handleSelectCourse(record) }}
          >
            {record.is_selected ? '已选' : '选课'}
          </Button>
          <Button
            type="link"
            size="small"
            icon={<ThunderboltOutlined />}
            loading={checkingConflict === record.course_id}
            onClick={(e) => { e.stopPropagation(); handleCheckConflict(record) }}
          >
            冲突检测
          </Button>
        </Space>
      ),
    }]),
  ]

  return (
    <AppLayout>
      {announcements.length > 0 && (
        <Alert
          message={
            <Space>
              <NotificationOutlined />
              <span>选课公告 ({announcements.length})</span>
              <Button type="link" size="small" onClick={() => setShowAnnouncements(!showAnnouncements)}>
                {showAnnouncements ? '收起' : '展开'}
              </Button>
            </Space>
          }
          description={showAnnouncements && (
            <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
              {announcements.map((item, idx) => (
                <li key={idx} style={{ marginBottom: 4 }}>
                  {item.title}{item.content ? `：${item.content}` : ''}
                </li>
              ))}
            </ul>
          )}
          type="info"
          showIcon={false}
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        activeKey={viewMode}
        onChange={handleViewModeChange}
        items={[
          { key: 'selected', label: '已选课程', icon: <CheckCircleOutlined /> },
          { key: 'available', label: '可选课程', icon: <BookOutlined /> },
        ]}
      />

      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <Select
          value={selectedTerm}
          onChange={(value) => { setSelectedTerm(value); setCoursePage(1) }}
          style={{ width: 180 }}
          placeholder="选择学期"
          options={termList.map(t => ({
            value: t.dm,
            label: t.mc + (t.dm === courseContext?.term.code ? ' (选课)' : ''),
          }))}
        />

        {viewMode === 'available' && (
          <>
            <Select
              value={courseMethod}
              onChange={(value) => {
                setCourseMethod(value)
                setFilterFacing('0')
                setCoursePage(1)
                clearSelectedCourses()
              }}
              style={{ width: 140 }}
              options={(courseContext?.methods || []).map(method => ({
                value: method.code,
                label: method.name,
              }))}
            />
            <Select
              value={filterCollege}
              onChange={(value) => { setFilterCollege(value); setCoursePage(1) }}
              style={{ width: 150 }}
              placeholder="开课学院"
              allowClear
              showSearch
              optionFilterProp="label"
              options={colleges.map(c => ({ value: c.code, label: c.name }))}
            />
            <Select
              value={filterCategory}
              onChange={(value) => { setFilterCategory(value); setCoursePage(1) }}
              style={{ width: 200 }}
              placeholder="课程类别"
              allowClear
              showSearch
              optionFilterProp="label"
              options={categoryOptions}
            />
            <Select
              value={filterCampus}
              onChange={(value) => { setFilterCampus(value); setCoursePage(1) }}
              style={{ width: 120 }}
              placeholder="校区"
              allowClear
              options={campuses.map(c => ({ value: c.code, label: c.name }))}
            />
            {isProfessionalDevelopment && (
              <Select
                aria-label="是否面向自己"
                value={filterFacing}
                onChange={(value) => { setFilterFacing(value); setCoursePage(1) }}
                style={{ width: 130 }}
                options={[
                  { value: '0', label: '全部' },
                  { value: '1', label: '面向自己' },
                  { value: '-1', label: '不面向自己' },
                ]}
              />
            )}
          </>
        )}

        <Input.Search
          placeholder="搜索课程名称/代码/教师/学院"
          allowClear
          style={{ width: 280 }}
          value={searchText}
          onChange={e => {
            setSearchText(e.target.value)
            if (!e.target.value) handleAvailableSearch('')
          }}
          onSearch={viewMode === 'available' ? handleAvailableSearch : undefined}
        />
        {viewMode === 'available' && (
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            disabled={!selectedCourseKeys.length || !!snatchTask && ['scheduled', 'running'].includes(snatchTask.status)}
            onClick={() => setSnatchModalOpen(true)}
          >
            定时抢课 ({selectedCourseKeys.length})
          </Button>
        )}
      </div>

      {snatchTask && (
        <Card
          size="small"
          title={
            <Space>
              <ThunderboltOutlined />
              <span>多选抢课任务</span>
              <Tag color={snatchTask.status === 'completed' ? 'success' : snatchTask.status === 'running' ? 'processing' : snatchTask.status === 'failed' || snatchTask.status === 'completed_with_errors' ? 'error' : 'default'}>
                {SNATCH_STATUS_LABELS[snatchTask.status]}
              </Tag>
            </Space>
          }
          extra={['scheduled', 'running'].includes(snatchTask.status) && (
            <Button danger loading={stoppingSnatchTask} onClick={handleStopSnatchTask}>
              停止任务
            </Button>
          )}
          style={{ marginBottom: 16 }}
        >
          <Alert
            type="warning"
            showIcon
            message="任务由当前后端进程执行；请勿重启后端或让电脑休眠。关闭网页不会停止任务。"
            style={{ marginBottom: 12 }}
          />
          <div style={{ marginBottom: 12 }}>
            计划开始：{new Date(snatchTask.start_at).toLocaleString()}
            {snatchTask.message ? ` · ${snatchTask.message}` : ''}
          </div>
          <Space wrap>
            {(snatchTask.items || []).map(item => (
              <Tag
                key={item.course_id}
                color={item.status === 'success' ? 'success' : item.status === 'failed' ? 'error' : item.status === 'retrying' ? 'processing' : 'default'}
              >
                {item.course_name || item.course_code || item.course_id} · {
                  item.status === 'success' ? '成功' : item.status === 'failed' ? '失败' : item.status === 'retrying' ? `重试中 (${item.attempts})` : '等待'
                }
                {item.error_type ? ` · ${SNATCH_ERROR_LABELS[item.error_type]}` : ''}
                {item.message ? ` · ${item.message}` : ''}
              </Tag>
            ))}
          </Space>
        </Card>
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={viewMode === 'selected' ? '已选课程' : '可选课程'}
              value={viewMode === 'available' ? availableCourseTotal : filteredCourses.length}
              prefix={<BookOutlined />}
              suffix="门"
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总学分"
              value={filteredCourses.reduce((sum, c) => sum + c.credits, 0)}
              prefix={<TeamOutlined />}
              precision={1}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总学时"
              value={filteredCourses.reduce((sum, c) => sum + (c.hours || 0), 0)}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="开课学院"
              value={new Set(filteredCourses.map(c => c.college)).size}
              prefix={<BankOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>

      <Card title={viewMode === 'selected' ? '已选课程列表' : '可选课程列表'}>
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={filteredCourses}
            rowKey="course_id"
            rowSelection={viewMode === 'available' ? {
              selectedRowKeys: selectedCourseKeys,
              preserveSelectedRowKeys: true,
              onChange: handleCourseSelectionChange,
              getCheckboxProps: (record) => ({
                disabled: record.is_selected || (
                  selectedCourseKeys.length >= 10 && !selectedCourseKeys.includes(record.course_id)
                ),
              }),
            } : undefined}
            scroll={{ x: 1400 }}
            pagination={viewMode === 'available' ? {
              current: coursePage,
              pageSize: coursePageSize,
              total: availableCourseTotal,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 门课程`,
              onChange: handleAvailablePageChange,
            } : {
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 门课程`,
              defaultPageSize: 20,
            }}
            size="small"
          />
        </Spin>
      </Card>

      <Modal
        title={`创建定时抢课任务（${selectedCourses.length} 门）`}
        open={snatchModalOpen}
        onCancel={() => setSnatchModalOpen(false)}
        onOk={handleCreateSnatchTask}
        okText="确认定时抢课"
        cancelText="取消"
        confirmLoading={creatingSnatchTask}
        width={640}
      >
        <Alert
          type="info"
          showIcon
          message="到达设定时间后自动开始；未成功课程会持续重试，全部成功后停止。"
          description="同一会话只运行一个任务。时间冲突的课程会标记失败，其余课程继续。"
          style={{ marginBottom: 16 }}
        />
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>开始时间</div>
          <Input
            type="datetime-local"
            aria-label="抢课开始时间"
            value={snatchStartAt}
            onChange={event => setSnatchStartAt(event.target.value)}
          />
        </div>
        <div style={{ marginBottom: 8, fontWeight: 500 }}>已选课程</div>
        <Space wrap>
          {selectedCourses.map(course => (
            <Tag key={course.course_id} closable onClose={() => {
              setSelectedCourseKeys(prev => prev.filter(key => key !== course.course_id))
              setSelectedCourseMap(prev => {
                const next = { ...prev }
                delete next[course.course_id]
                return next
              })
            }}>
              {course.course_name} · {course.teacher || '教师待定'}
            </Tag>
          ))}
        </Space>
      </Modal>

      <Modal
        title="课程详情"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={700}
      >
        {selectedCourse && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="课程代码">{selectedCourse.course_code}</Descriptions.Item>
            <Descriptions.Item label="课程名称">{selectedCourse.course_name}</Descriptions.Item>
            {selectedCourse.course_name_en && (
              <Descriptions.Item label="英文名称" span={2}>{selectedCourse.course_name_en}</Descriptions.Item>
            )}
            <Descriptions.Item label="课程性质">
              <Tag color={COURSE_TYPE_COLORS[selectedCourse.course_nature] || 'default'}>
                {selectedCourse.course_nature}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="课程类别">{selectedCourse.course_category}</Descriptions.Item>
            <Descriptions.Item label="学分">{selectedCourse.credits}</Descriptions.Item>
            <Descriptions.Item label="学时">{selectedCourse.hours ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="选课方式">{selectedCourse.method}</Descriptions.Item>
            <Descriptions.Item label="教师">{selectedCourse.teacher}</Descriptions.Item>
            <Descriptions.Item label="开课学院">{selectedCourse.college}</Descriptions.Item>
            <Descriptions.Item label="校区">{selectedCourse.campus}</Descriptions.Item>
            <Descriptions.Item label="实时容量（已占/上限）">
              <Space wrap size={4}>
                {quotaTag('总', selectedCourse.selected_count, selectedCourse.capacity)}
                {selectedCourse.internal_capacity != null && quotaTag(
                  '对内',
                  selectedCourse.internal_selected_count,
                  selectedCourse.internal_capacity,
                )}
                {selectedCourse.external_capacity != null && quotaTag(
                  '对外',
                  selectedCourse.external_selected_count,
                  selectedCourse.external_capacity,
                )}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="上课时间" span={2}>
              {selectedCourse.schedule_time || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="上课地点" span={2}>
              {selectedCourse.schedule_location || '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </AppLayout>
  )
}

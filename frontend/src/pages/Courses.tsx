import { useEffect, useState, useMemo, useCallback } from 'react'
import { Card, Table, Select, Spin, Tag, Statistic, Row, Col, Modal, Descriptions, Input, Tooltip, message, Tabs, Alert, Button, Space } from 'antd'
import { BookOutlined, ClockCircleOutlined, TeamOutlined, BankOutlined, CheckCircleOutlined, NotificationOutlined, ThunderboltOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'
import type { components } from '../services/openapi'
import AppLayout from '../components/AppLayout'

type Course = components['schemas']['CourseSelectionRecord']
type CourseContext = components['schemas']['app__models__courses__CourseSelectionContext']
type CoursePage = components['schemas']['CourseSelectionPage']
type SelectedCoursePage = components['schemas']['SelectedCoursePage']
type PreflightResponse = components['schemas']['CoursePreflightResponse']
type WriteResponse = components['schemas']['CourseWriteResponse']

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

export default function CoursesPage() {
  const [loading, setLoading] = useState(true)
  const [courses, setCourses] = useState<Course[]>([])
  const [courseContext, setCourseContext] = useState<CourseContext | null>(null)
  const [termList, setTermList] = useState<TermListItem[]>([])
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null)
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [searchText, setSearchText] = useState('')

  // 新增：视图模式和筛选条件
  const [viewMode, setViewMode] = useState<'selected' | 'available'>('selected')
  const [courseMethod, setCourseMethod] = useState('bx-b-b')
  const [colleges, setColleges] = useState<FilterOption[]>([])
  const [campuses, setCampuses] = useState<FilterOption[]>([])
  const [categories, setCategories] = useState<FilterOption[]>([])
  const [filterCollege, setFilterCollege] = useState<string | undefined>()
  const [filterCategory, setFilterCategory] = useState<string | undefined>()
  const [filterCampus, setFilterCampus] = useState<string | undefined>()

  // 公告
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [showAnnouncements, setShowAnnouncements] = useState(true)

  // 冲突检测
  const [checkingConflict, setCheckingConflict] = useState<string | null>(null)

  // 选课/退课操作中
  const [selectingCourse, setSelectingCourse] = useState<string | null>(null)
  const [droppingCourse, setDroppingCourse] = useState<string | null>(null)

  const categoryOptions = useMemo(
    () => categories.map(category => ({ value: category.code, label: category.name })),
    [categories],
  )

  // 筛选后的课程
  const filteredCourses = useMemo(() => {
    let result = courses

    // 在可选课程模式下，只显示未选的课程
    if (viewMode === 'available') {
      result = result.filter(c => !c.is_selected)
    }

    // 搜索筛选
    if (searchText) {
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
          const announcementsRes = await api.get('/courses/announcements', {
            params: { xn: context.term.year, xq: context.term.semester },
          })
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
              page: 1,
              page_size: 100,
            },
          })
          setCourses(res.data.items || [])
        }
      } catch (err) {
        console.error('Failed to fetch courses:', err)
        message.error(viewMode === 'selected' ? '获取已选课程失败' : '获取可选课程失败')
      } finally {
        setLoading(false)
      }
    }
    fetchCourses()
  }, [selectedTerm, viewMode, courseMethod, filterCollege, filterCategory, filterCampus])

  // 显示课程详情
  const handleCourseClick = (course: Course) => {
    setSelectedCourse(course)
    setModalVisible(true)
  }

  // 切换视图模式时重置筛选
  const handleViewModeChange = (mode: string) => {
    setViewMode(mode as 'selected' | 'available')
    setSearchText('')
    setFilterCollege(undefined)
    setFilterCategory(undefined)
    setFilterCampus(undefined)
  }

  // 冲突检测
  const handleCheckConflict = useCallback(async (course: Course) => {
    setCheckingConflict(course.course_id)
    try {
      const res = await api.post<PreflightResponse>('/course-selection/preflight', {
        course_id: course.course_id,
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
        { course_id: course.course_id, method: courseMethod },
        { headers: { 'Idempotency-Key': idempotencyKey() } },
      )
      message.success(res.data.message || `"${course.course_name}" 选课成功`)
      setCourses(prev => prev.map(c =>
        c.course_id === course.course_id ? { ...c, is_selected: true } : c
      ))
    } catch (err: any) {
      message.error(err.response?.data?.error?.message || '选课失败')
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
        } catch (err: any) {
          message.error(err.response?.data?.error?.message || '退课失败')
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
      title: '容量',
      key: 'capacity',
      width: 100,
      render: (_, record) => {
        const selected = record.selected_count || 0
        const total = record.capacity || 0
        const percent = total > 0 ? (selected / total) * 100 : 0
        const color = percent >= 100 ? 'red' : percent >= 80 ? 'orange' : 'green'
        return (
          <Tooltip title={`${selected}/${total}`}>
            <Tag color={color}>{selected}/{total}</Tag>
          </Tooltip>
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
                  {item.ggmc || item.ggbt || item.title || item.mc || item.content || JSON.stringify(item)}
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
          onChange={setSelectedTerm}
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
              onChange={setCourseMethod}
              style={{ width: 140 }}
              options={(courseContext?.methods || []).map(method => ({
                value: method.code,
                label: method.name,
              }))}
            />
            <Select
              value={filterCollege}
              onChange={setFilterCollege}
              style={{ width: 150 }}
              placeholder="开课学院"
              allowClear
              showSearch
              optionFilterProp="label"
              options={colleges.map(c => ({ value: c.code, label: c.name }))}
            />
            <Select
              value={filterCategory}
              onChange={setFilterCategory}
              style={{ width: 200 }}
              placeholder="课程类别"
              allowClear
              showSearch
              optionFilterProp="label"
              options={categoryOptions}
            />
            <Select
              value={filterCampus}
              onChange={setFilterCampus}
              style={{ width: 120 }}
              placeholder="校区"
              allowClear
              options={campuses.map(c => ({ value: c.code, label: c.name }))}
            />
          </>
        )}

        <Input.Search
          placeholder="搜索课程名称/代码/教师/学院"
          allowClear
          style={{ width: 280 }}
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
        />
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={viewMode === 'selected' ? '已选课程' : '可选课程'}
              value={filteredCourses.length}
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
            scroll={{ x: 1400 }}
            pagination={{
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
            <Descriptions.Item label="容量/已选">
              {selectedCourse.selected_count ?? '-'}/{selectedCourse.capacity ?? '-'}
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

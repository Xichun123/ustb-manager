import { useEffect, useState, useMemo, useCallback } from 'react'
import { Card, Table, Select, Spin, Tag, Statistic, Row, Col, Modal, Descriptions, Input, Tooltip, message, Tabs, Alert, Button, Space } from 'antd'
import { BookOutlined, ClockCircleOutlined, TeamOutlined, BankOutlined, CheckCircleOutlined, NotificationOutlined, ThunderboltOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'

interface Course {
  task_id: string
  internal_id?: string  // BYYT 内部 ID（退课用）
  course_code: string
  course_name: string
  course_name_en: string
  course_type: string
  course_type_code: string
  category: string
  category_code: string
  credits: string
  hours: string
  selection_method: string
  selection_method_code: string
  college: string
  college_code: string
  campus: string
  campus_code: string
  teacher: string
  task_name: string
  capacity: string
  selected_count: string
  selection_time: string
  withdraw_start: string
  withdraw_end: string
  selection_status: string
  lottery_status: string
  needs_payment: boolean
  needs_approval: boolean
  schedule_html: string
  course_info: string
  class_number: string
  is_selected?: boolean  // 是否已选（可选课程列表中使用）
}

interface TermInfo {
  p_xn: string
  p_xq: string
  p_xnxq: string
  p_dqxn: string
  p_dqxq: string
  p_dqxnxq: string
}

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

// 选课方式选项
const COURSE_METHODS = [
  { value: 'bx-b-b', label: '必修课' },
  { value: 'mooc-b-b', label: 'MOOC' },
  { value: 'sztzk-b-b', label: '素质拓展课' },
  { value: 'zytzk-b-b', label: '专业拓展课' },
]

export default function CoursesPage() {
  const [loading, setLoading] = useState(true)
  const [courses, setCourses] = useState<Course[]>([])
  const [termInfo, setTermInfo] = useState<TermInfo | null>(null)
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

  // 从当前课程数据中提取唯一的课程类别
  const categoryOptions = useMemo(() => {
    const categorySet = new Set<string>()
    courses.forEach(c => {
      if (c.category) categorySet.add(c.category)
    })
    return Array.from(categorySet).sort().map(cat => ({
      value: cat,
      label: cat,
    }))
  }, [courses])

  // 筛选后的课程
  const filteredCourses = useMemo(() => {
    let result = courses

    // 在可选课程模式下，只显示未选的课程
    if (viewMode === 'available') {
      result = result.filter(c => !c.is_selected)
    }

    // 课程类别筛选（本地筛选）
    if (filterCategory) {
      result = result.filter(c => c.category === filterCategory)
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
  }, [courses, searchText, viewMode, filterCategory])

  // 统计信息
  const stats = useMemo(() => {
    const types: Record<string, number> = {}
    const methods: Record<string, number> = {}
    filteredCourses.forEach(c => {
      types[c.course_type] = (types[c.course_type] || 0) + 1
      methods[c.selection_method] = (methods[c.selection_method] || 0) + 1
    })
    return { types, methods }
  }, [filteredCourses])

  // 初始化：获取学期信息和筛选选项
  useEffect(() => {
    const init = async () => {
      try {
        const [termInfoRes, termListRes, collegesRes, campusesRes] = await Promise.all([
          api.get('/courses/term-info'),
          api.get('/courses/term-list'),
          api.get('/courses/colleges'),
          api.get('/courses/campuses'),
        ])
        setTermInfo(termInfoRes.data)
        setTermList(termListRes.data)
        setColleges(collegesRes.data)
        setCampuses(campusesRes.data)
        // 默认选择选课学期
        if (termInfoRes.data.p_xnxq) {
          setSelectedTerm(termInfoRes.data.p_xnxq)
        } else if (termListRes.data.length > 0) {
          setSelectedTerm(termListRes.data[0].dm)
        }
        // 加载公告
        try {
          const xn = termInfoRes.data.p_xn || termInfoRes.data.p_dqxn
          const xq = termInfoRes.data.p_xq || termInfoRes.data.p_dqxq
          const announcementsRes = await api.get('/courses/announcements', { params: { xn, xq } })
          const list = Array.isArray(announcementsRes.data) ? announcementsRes.data : []
          setAnnouncements(list)
        } catch {
          // 公告加载失败不影响主功能
        }
      } catch (err) {
        console.error('Failed to init courses:', err)
        message.error('获取学期信息失败')
      }
    }
    init()
  }, [])

  // 加载课程
  useEffect(() => {
    if (!selectedTerm) return

    const fetchCourses = async () => {
      setLoading(true)
      // 清空旧数据，避免显示混合内容
      setCourses([])
      // 重置本地筛选
      setFilterCategory(undefined)
      try {
        // 解析学期代码
        const xn = selectedTerm.slice(0, 9) // 2025-2026
        const xq = selectedTerm.slice(9) // 2

        let url: string
        if (viewMode === 'selected') {
          url = `/courses/selected?xn=${xn}&xq=${xq}`
        } else {
          const params = new URLSearchParams({ xn, xq, method: courseMethod })
          if (filterCollege) params.append('college', filterCollege)
          if (filterCampus) params.append('campus', filterCampus)
          url = `/courses/available?${params}`
        }

        const res = await api.get(url)
        setCourses(res.data.courses)
      } catch (err) {
        console.error('Failed to fetch courses:', err)
        message.error(viewMode === 'selected' ? '获取已选课程失败' : '获取可选课程失败')
      } finally {
        setLoading(false)
      }
    }
    fetchCourses()
  }, [selectedTerm, viewMode, courseMethod, filterCollege, filterCampus])

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
    setCheckingConflict(course.task_id)
    try {
      const res = await api.post('/courses/check-conflict', {
        course_id: course.task_id,
        method: courseMethod,
      })
      if (res.data.has_conflict) {
        Modal.warning({
          title: '存在时间冲突',
          content: res.data.message || `"${course.course_name}" 与已选课程存在时间冲突`,
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
    setSelectingCourse(course.task_id)
    try {
      const res = await api.post('/courses/select', {
        course_id: course.task_id,
        method: courseMethod,
      })
      if (res.data.success) {
        message.success(res.data.message || `"${course.course_name}" 选课成功`)
        // 刷新课程列表
        setCourses(prev => prev.map(c =>
          c.task_id === course.task_id ? { ...c, is_selected: true } : c
        ))
      } else {
        message.error(res.data.message || '选课失败')
      }
    } catch (err: any) {
      message.error(err.response?.data?.detail || '选课失败')
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
        setDroppingCourse(course.task_id)
        try {
          const res = await api.post('/courses/drop', {
            course_id: course.internal_id || course.task_id,
            method: course.selection_method_code || 'bx-b-b',
          })
          if (res.data.success) {
            message.success(res.data.message || `"${course.course_name}" 退课成功`)
            setCourses(prev => prev.filter(c => c.task_id !== course.task_id))
          } else {
            message.error(res.data.message || '退课失败')
          }
        } catch (err: any) {
          message.error(err.response?.data?.detail || '退课失败')
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
      dataIndex: 'course_type',
      key: 'course_type',
      width: 80,
      render: (text) => (
        <Tag color={COURSE_TYPE_COLORS[text] || 'default'}>{text}</Tag>
      ),
      filters: Object.keys(stats.types).map(t => ({ text: t, value: t })),
      onFilter: (value, record) => record.course_type === value,
    },
    {
      title: '课程类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      ellipsis: true,
    },
    {
      title: '学分',
      dataIndex: 'credits',
      key: 'credits',
      width: 60,
      align: 'center',
      sorter: (a, b) => parseFloat(a.credits) - parseFloat(b.credits),
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
      dataIndex: 'selection_method',
      key: 'selection_method',
      width: 100,
      render: (text) => (
        <Tag color={SELECTION_METHOD_COLORS[text] || 'default'}>{text}</Tag>
      ),
      filters: Object.keys(stats.methods).map(m => ({ text: m, value: m })),
      onFilter: (value, record) => record.selection_method === value,
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
        const selected = parseInt(record.selected_count) || 0
        const total = parseInt(record.capacity) || 0
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
      title: '选课时间',
      dataIndex: 'selection_time',
      key: 'selection_time',
      width: 160,
      sorter: (a: Course, b: Course) => new Date(a.selection_time).getTime() - new Date(b.selection_time).getTime(),
    }, {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right' as const,
      render: (_: unknown, record: Course) => (
        <Button
          type="link"
          size="small"
          danger
          loading={droppingCourse === record.task_id}
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
            loading={selectingCourse === record.task_id}
            disabled={record.is_selected}
            onClick={(e) => { e.stopPropagation(); handleSelectCourse(record) }}
          >
            {record.is_selected ? '已选' : '选课'}
          </Button>
          <Button
            type="link"
            size="small"
            icon={<ThunderboltOutlined />}
            loading={checkingConflict === record.task_id}
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
            label: t.mc + (t.dm === termInfo?.p_xnxq ? ' (选课)' : ''),
          }))}
        />

        {viewMode === 'available' && (
          <>
            <Select
              value={courseMethod}
              onChange={setCourseMethod}
              style={{ width: 140 }}
              options={COURSE_METHODS}
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
              value={filteredCourses.reduce((sum, c) => sum + parseFloat(c.credits || '0'), 0)}
              prefix={<TeamOutlined />}
              precision={1}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总学时"
              value={filteredCourses.reduce((sum, c) => sum + parseFloat(c.hours || '0'), 0)}
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
            rowKey="task_id"
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
            <Descriptions.Item label="课序号">{selectedCourse.class_number}</Descriptions.Item>
            <Descriptions.Item label="课程名称" span={2}>{selectedCourse.course_name}</Descriptions.Item>
            {selectedCourse.course_name_en && (
              <Descriptions.Item label="英文名称" span={2}>{selectedCourse.course_name_en}</Descriptions.Item>
            )}
            <Descriptions.Item label="课程性质">
              <Tag color={COURSE_TYPE_COLORS[selectedCourse.course_type] || 'default'}>
                {selectedCourse.course_type}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="课程类别">{selectedCourse.category}</Descriptions.Item>
            <Descriptions.Item label="学分">{selectedCourse.credits}</Descriptions.Item>
            <Descriptions.Item label="学时">{selectedCourse.hours}</Descriptions.Item>
            <Descriptions.Item label="选课方式">
              <Tag color={SELECTION_METHOD_COLORS[selectedCourse.selection_method] || 'default'}>
                {selectedCourse.selection_method}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="教师">{selectedCourse.teacher}</Descriptions.Item>
            <Descriptions.Item label="开课学院">{selectedCourse.college}</Descriptions.Item>
            <Descriptions.Item label="校区">{selectedCourse.campus}</Descriptions.Item>
            <Descriptions.Item label="容量/已选">
              {selectedCourse.selected_count}/{selectedCourse.capacity}
            </Descriptions.Item>
            {selectedCourse.selection_time && (
              <Descriptions.Item label="选课时间">{selectedCourse.selection_time}</Descriptions.Item>
            )}
            {selectedCourse.withdraw_start && (
              <Descriptions.Item label="退选时间" span={2}>
                {selectedCourse.withdraw_start} ~ {selectedCourse.withdraw_end}
              </Descriptions.Item>
            )}
            {selectedCourse.task_name && (
              <Descriptions.Item label="任务名称" span={2}>{selectedCourse.task_name}</Descriptions.Item>
            )}
            {selectedCourse.schedule_html && (
              <Descriptions.Item label="上课安排" span={2}>
                <div dangerouslySetInnerHTML={{ __html: selectedCourse.schedule_html }} />
              </Descriptions.Item>
            )}
            {selectedCourse.needs_payment && (
              <Descriptions.Item label="状态" span={2}>
                <Tag color="warning">需要缴费</Tag>
              </Descriptions.Item>
            )}
            {selectedCourse.needs_approval && (
              <Descriptions.Item label="审核" span={2}>
                <Tag color="processing">需要审核</Tag>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </AppLayout>
  )
}

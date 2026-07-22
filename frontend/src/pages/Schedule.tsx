import { useEffect, useState, useMemo, useRef } from 'react'
import { Card, Tabs, Select, Spin, Modal, Descriptions, Tag, Tooltip, Button, message, Dropdown } from 'antd'
import type { MenuProps } from 'antd'
import { DownloadOutlined, FileImageOutlined, CalendarOutlined } from '@ant-design/icons'
import html2canvas from 'html2canvas'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'
import { useTheme } from '../contexts/ThemeContext'
import AppLayout from '../components/AppLayout'
import { buildScheduleGrid } from '../services/scheduleGrid'
import { formatAcademicTermLabel } from '../services/academicTerms'

type CourseItem = components['schemas']['ScheduleCourse']
type ScheduleData = components['schemas']['ScheduleView']
type AcademicContext = components['schemas']['AcademicContextResponse']
type TermListItem = components['schemas']['AcademicTermOption']

const PERIOD_TIMES = [
  { label: '1-2节', time: '08:00-09:35' },
  { label: '3-4节', time: '09:55-11:30' },
  { label: '5-6节', time: '13:30-15:05' },
  { label: '7-8节', time: '15:20-16:55' },
  { label: '9-10节', time: '17:10-18:45' },
  { label: '11-12节', time: '19:30-21:05' },
]

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const COURSE_COLORS = [
  '#e6f7ff', '#fff7e6', '#f6ffed', '#fff1f0', '#f9f0ff',
  '#e6fffb', '#fcffe6', '#fff0f6', '#f0f5ff', '#fffbe6',
]

// 暗色主题下的课程底色
const COURSE_COLORS_DARK = [
  '#13293d', '#3d2e13', '#1e3d13', '#3d1a1a', '#2d1a3d',
  '#133d3d', '#333d13', '#3d1330', '#1a2440', '#3d3613',
]

export default function SchedulePage() {
  const { resolvedTheme } = useTheme()
  const coursePalette = resolvedTheme === 'dark' ? COURSE_COLORS_DARK : COURSE_COLORS
  const [loading, setLoading] = useState(true)
  const [scheduleData, setScheduleData] = useState<ScheduleData | null>(null)
  const [currentTerm, setCurrentTerm] = useState<string | null>(null)
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null)
  const [termList, setTermList] = useState<TermListItem[]>([])
  const [weekList, setWeekList] = useState<number[]>([])
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const [currentWeek, setCurrentWeek] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<'week' | 'full'>('week')
  const [selectedCourse, setSelectedCourse] = useState<CourseItem | null>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const scheduleRef = useRef<HTMLDivElement>(null)

  // 课程颜色映射
  const courseColorMap = useMemo(() => {
    const map: Record<string, string> = {}
    const courseNames = new Set<string>()
    scheduleData?.items?.forEach(c => courseNames.add(c.course_name))
    Array.from(courseNames).forEach((name, idx) => {
      map[name] = coursePalette[idx % coursePalette.length]
    })
    return map
  }, [scheduleData, coursePalette])

  // 课程网格数据；跨双节时段的课程需要出现在覆盖的每一行
  const scheduleGrid = useMemo(
    () => buildScheduleGrid(scheduleData?.items || [], PERIOD_TIMES.length, WEEKDAYS.length),
    [scheduleData]
  )

  // 点击课程显示详情
  const handleCourseClick = (course: CourseItem) => {
    setSelectedCourse(course)
    setModalVisible(true)
  }

  // 初始化：按今天获取教学学期与当前周
  useEffect(() => {
    const init = async () => {
      try {
        const [contextRes, termsRes] = await Promise.all([
          api.get<AcademicContext>('/academic/context'),
          api.get<TermListItem[]>('/academic/terms'),
        ])
        const term = contextRes.data.teaching_term.code
        const week = contextRes.data.week || 1
        setCurrentTerm(term)
        setCurrentWeek(week)
        setSelectedTerm(term)
        setSelectedWeek(week)
        setTermList(termsRes.data)
        setWeekList(Array.from({ length: Math.max(24, week) }, (_, index) => index + 1))
      } catch (error: unknown) {
        message.error(getApiErrorMessage(error, '获取学期信息失败'))
      }
    }
    init()
  }, [])

  // 加载统一课表数据；week 为空即总课表
  useEffect(() => {
    if (!selectedTerm) return
    if (viewMode === 'week' && !selectedWeek) return

    const fetchSchedule = async () => {
      setLoading(true)
      try {
        const res = await api.get<ScheduleData>('/schedule', {
          params: {
            term: selectedTerm,
            week: viewMode === 'week' ? selectedWeek : undefined,
          },
        })
        setScheduleData(res.data)
      } catch (error: unknown) {
        message.error(getApiErrorMessage(error, '获取课表失败'))
      } finally {
        setLoading(false)
      }
    }
    fetchSchedule()
  }, [selectedTerm, selectedWeek, viewMode])

  // 导出课表为ICS格式
  const handleExport = () => {
    if (!scheduleData || !scheduleData.items?.length) {
      message.warning('没有课程数据可导出')
      return
    }

    // 节次对应的开始和结束时间
    const periodTimes: Record<number, { start: string; end: string }> = {
      1: { start: '08:00', end: '08:45' },
      2: { start: '08:50', end: '09:35' },
      3: { start: '09:55', end: '10:40' },
      4: { start: '10:45', end: '11:30' },
      5: { start: '13:30', end: '14:15' },
      6: { start: '14:20', end: '15:05' },
      7: { start: '15:20', end: '16:05' },
      8: { start: '16:10', end: '16:55' },
      9: { start: '17:10', end: '17:55' },
      10: { start: '18:00', end: '18:45' },
      11: { start: '19:30', end: '20:15' },
      12: { start: '20:20', end: '21:05' },
    }

    // 生成ICS内容
    let icsContent = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//USTB Manager//Schedule Export//CN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
    ]

    const formatDate = (date: Date, time: string) => {
      const [hours, minutes] = time.split(':')
      const d = new Date(date)
      d.setHours(parseInt(hours), parseInt(minutes), 0, 0)
      return d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
    }

    // 如果是周课表且有日期信息
    const dates = scheduleData.dates
    if (viewMode === 'week' && dates && Object.keys(dates).length > 0) {
      scheduleData.items?.forEach((course, idx) => {
        const dateStr = dates[course.weekday]
        if (!dateStr) return

        const baseDate = new Date(dateStr)
        const startTime = periodTimes[course.start_period]?.start || '08:00'
        const endTime = periodTimes[course.end_period]?.end || '09:35'

        icsContent.push(
          'BEGIN:VEVENT',
          `UID:${course.task_code}-${idx}@ustb-manager`,
          `DTSTAMP:${formatDate(new Date(), '00:00')}`,
          `DTSTART:${formatDate(baseDate, startTime)}`,
          `DTEND:${formatDate(baseDate, endTime)}`,
          `SUMMARY:${course.course_name}`,
          `DESCRIPTION:教师: ${course.teacher}\\n周次: ${course.week_text}`,
          `LOCATION:${course.location}`,
          'END:VEVENT'
        )
      })
    } else {
      // 总课表导出提示
      message.info('总课表导出请先切换到周课表视图')
      return
    }

    icsContent.push('END:VCALENDAR')

    // 下载文件
    const blob = new Blob([icsContent.join('\r\n')], { type: 'text/calendar;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `课表_第${selectedWeek}周.ics`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    message.success('课表已导出为ICS格式')
  }

  // 导出课表为图片
  const handleExportImage = async () => {
    if (!scheduleRef.current) {
      message.error('无法获取课表内容')
      return
    }

    try {
      message.loading({ content: '正在生成图片...', key: 'exportImage' })

      const canvas = await html2canvas(scheduleRef.current, {
        backgroundColor: '#ffffff',
        scale: 2, // 高清输出
        useCORS: true,
        logging: false,
      })

      const url = canvas.toDataURL('image/png')
      const a = document.createElement('a')
      a.href = url
      const selectedTermOption = termList.find(t => t.code === selectedTerm)
      const termName = selectedTermOption
        ? formatAcademicTermLabel(selectedTermOption)
        : selectedTerm
      a.download = viewMode === 'week'
        ? `课表_${termName}_第${selectedWeek}周.png`
        : `课表_${termName}_总课表.png`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)

      message.success({ content: '课表已导出为图片', key: 'exportImage' })
    } catch (err) {
      console.error('Failed to export image:', err)
      message.error({ content: '导出图片失败', key: 'exportImage' })
    }
  }

  // 导出菜单选项
  const exportMenuItems: MenuProps['items'] = [
    {
      key: 'image',
      icon: <FileImageOutlined />,
      label: '导出为图片',
      onClick: handleExportImage,
    },
    {
      key: 'ics',
      icon: <CalendarOutlined />,
      label: '导出为日历 (ICS)',
      onClick: handleExport,
    },
  ]

  // 渲染课程单元格
  const renderCourseCell = (courses: CourseItem[], periodIdx: number, weekdayIdx: number) => {
    if (!courses || courses.length === 0) {
      return (
        <div
          key={`${periodIdx}-${weekdayIdx}`}
          className="schedule-grid-line schedule-grid-bg"
          style={{
            minHeight: 80,
            border: '1px solid var(--app-grid-line)',
          }}
        />
      )
    }

    return (
      <div
        key={`${periodIdx}-${weekdayIdx}`}
        style={{
          minHeight: 80,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {courses.map((course, idx) => (
          <Tooltip
            key={`${periodIdx}-${weekdayIdx}-${idx}`}
            title={`${course.course_name} - ${course.teacher} - ${course.week_text}`}
          >
            <div
              onClick={() => handleCourseClick(course)}
              className="schedule-grid-line"
              style={{
                flex: 1,
                minHeight: courses.length > 1 ? 60 : 80,
                padding: 4,
                border: '1px solid var(--app-grid-line)',
                background: courseColorMap[course.course_name] || coursePalette[0],
                borderRadius: 6,
                cursor: 'pointer',
                overflow: 'hidden',
                fontSize: 11,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                textAlign: 'center',
              }}
            >
              <div style={{ fontWeight: 'bold', marginBottom: 1, lineHeight: 1.2, fontSize: 11 }}>
                {course.course_name.length > 6
                  ? course.course_name.slice(0, 6) + '...'
                  : course.course_name}
              </div>
              <div style={{ color: 'var(--app-text-secondary)', fontSize: 10 }}>{course.teacher}</div>
              <div style={{ color: 'var(--ant-color-primary)', fontSize: 9, fontWeight: 500 }}>
                {course.week_text}
              </div>
              <div style={{ color: 'var(--app-text-secondary)', fontSize: 9, opacity: 0.85 }}>
                {course.location.replace('【校本部】', '')}
              </div>
            </div>
          </Tooltip>
        ))}
      </div>
    )
  }

  return (
    <AppLayout>
      <Tabs
        activeKey={viewMode}
        onChange={(key) => setViewMode(key as 'week' | 'full')}
        items={[
          { key: 'week', label: '周课表' },
          { key: 'full', label: '总课表' },
        ]}
      />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', marginBottom: 16 }}>
        <Select
          value={selectedTerm}
          onChange={setSelectedTerm}
          style={{ width: 280, maxWidth: '100%' }}
          placeholder="选择学期"
          options={termList.map(t => ({
            value: t.code,
            label: formatAcademicTermLabel(t) + (t.code === currentTerm ? ' (当前)' : ''),
          }))}
        />
        {viewMode === 'week' && (
          <>
            <Select
              value={selectedWeek}
              onChange={setSelectedWeek}
              style={{ width: 140 }}
              options={weekList.map(w => ({
                value: w,
                label: w === currentWeek ? `第${w}周 (当前)` : `第${w}周`,
              }))}
            />
            {currentWeek && selectedWeek !== currentWeek && (
              <Button size="small" onClick={() => setSelectedWeek(currentWeek)}>
                回到当前周
              </Button>
            )}
          </>
        )}
        <Dropdown menu={{ items: exportMenuItems }} placement="bottomRight">
          <Button icon={<DownloadOutlined />}>
            导出
          </Button>
        </Dropdown>
      </div>

      <Spin spinning={loading}>
        <Card>
          <div
            ref={scheduleRef}
            style={{
              display: 'grid',
              gridTemplateColumns: '60px repeat(7, 1fr)',
              gap: 1,
              background: 'var(--app-grid-line)',
            }}
          >
            {/* 表头 */}
            <div className="schedule-grid-bg" style={{ padding: 8, textAlign: 'center', fontWeight: 'bold' }}>
              节次
            </div>
            {WEEKDAYS.map((day, idx) => (
              <div
                key={day}
                className="schedule-grid-bg"
                style={{
                  padding: 8,
                  textAlign: 'center',
                  fontWeight: 'bold',
                }}
              >
                <div>{day}</div>
                {scheduleData?.dates && scheduleData.dates[idx + 1] && (
                  <div style={{ fontSize: 11, color: 'var(--app-text-secondary)' }}>
                    {scheduleData.dates[idx + 1].slice(5)}
                  </div>
                )}
              </div>
            ))}

            {/* 课程网格 */}
            {PERIOD_TIMES.map((period, periodIdx) => (
              <>
                <div
                  key={`period-${periodIdx}`}
                  className="schedule-grid-bg"
                  style={{
                    padding: 8,
                    textAlign: 'center',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                  }}
                >
                  <div style={{ fontWeight: 'bold', fontSize: 12 }}>{period.label}</div>
                  <div style={{ fontSize: 10, color: 'var(--app-text-secondary)' }}>{period.time}</div>
                </div>
                {WEEKDAYS.map((_, weekdayIdx) =>
                  renderCourseCell(
                    scheduleGrid[periodIdx]?.[weekdayIdx] || [],
                    periodIdx,
                    weekdayIdx
                  )
                )}
              </>
            ))}
          </div>
        </Card>
      </Spin>

      <Modal
        title="课程详情"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={500}
      >
        {selectedCourse && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="课程名称">{selectedCourse.course_name}</Descriptions.Item>
            <Descriptions.Item label="教师">{selectedCourse.teacher}</Descriptions.Item>
            <Descriptions.Item label="上课周次">
              <Tag color="blue">{selectedCourse.week_text}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="上课地点">{selectedCourse.location}</Descriptions.Item>
            <Descriptions.Item label="节次">
              第{selectedCourse.start_period}-{selectedCourse.end_period}节
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </AppLayout>
  )
}
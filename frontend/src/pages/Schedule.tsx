import { useEffect, useState, useMemo, useRef } from 'react'
import { Card, Tabs, Select, Spin, Modal, Descriptions, Tag, Tooltip, Button, message, Dropdown } from 'antd'
import type { MenuProps } from 'antd'
import { DownloadOutlined, FileImageOutlined, CalendarOutlined } from '@ant-design/icons'
import html2canvas from 'html2canvas'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'

interface CourseItem {
  key: string
  weekday: number
  period: number
  start_period: number
  end_period: number
  course_name: string
  teacher: string
  weeks: string
  location: string
  task_code: string
}

interface ScheduleData {
  schedule: CourseItem[]
  dates: Record<string, string>
  week: number | null
  term: string
}

interface TermInfo {
  XNXQ: string
  XN: string
  XQ: string
}

interface TermListItem {
  dm: string
  mc: string
}

interface WeekItem {
  ZC: number
  ZCMC: string
}

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

export default function SchedulePage() {
  const [loading, setLoading] = useState(true)
  const [scheduleData, setScheduleData] = useState<ScheduleData | null>(null)
  const [currentTerm, setCurrentTerm] = useState<TermInfo | null>(null)
  const [selectedTerm, setSelectedTerm] = useState<string | null>(null)
  const [termList, setTermList] = useState<TermListItem[]>([])
  const [weekList, setWeekList] = useState<WeekItem[]>([])
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
    scheduleData?.schedule.forEach(c => courseNames.add(c.course_name))
    Array.from(courseNames).forEach((name, idx) => {
      map[name] = COURSE_COLORS[idx % COURSE_COLORS.length]
    })
    return map
  }, [scheduleData])

  // 课程网格数据
  const scheduleGrid = useMemo(() => {
    if (!scheduleData?.schedule) return []
    const grid: CourseItem[][][] = PERIOD_TIMES.map(() =>
      WEEKDAYS.map(() => [])
    )
    scheduleData.schedule.forEach(course => {
      const periodIdx = Math.floor((course.start_period - 1) / 2)
      const weekdayIdx = course.weekday - 1
      if (periodIdx >= 0 && periodIdx < PERIOD_TIMES.length && weekdayIdx >= 0 && weekdayIdx < WEEKDAYS.length) {
        grid[periodIdx][weekdayIdx].push(course)
      }
    })
    return grid
  }, [scheduleData])

  // 点击课程显示详情
  const handleCourseClick = (course: CourseItem) => {
    setSelectedCourse(course)
    setModalVisible(true)
  }

  // 初始化：获取当前学期和学期列表
  useEffect(() => {
    const init = async () => {
      try {
        const [termRes, termListRes] = await Promise.all([
          api.get('/schedule/current-term'),
          api.get('/schedule/term-list'),
        ])
        setCurrentTerm(termRes.data)
        setTermList(termListRes.data)
        setSelectedTerm(termRes.data.XNXQ)
      } catch (err) {
        console.error('Failed to init schedule:', err)
        message.error('获取学期信息失败')
      }
    }
    init()
  }, [])

  // 当选择的学期变化时，获取周次列表
  useEffect(() => {
    if (!selectedTerm) return

    const fetchWeekList = async () => {
      try {
        const [xn, xq] = parseTermCode(selectedTerm)
        const weekRes = await api.get(`/schedule/week-list?xn=${xn}&xq=${xq}`)
        const weeks = weekRes.data.filter((w: WeekItem) => w.ZC !== 99)
        setWeekList(weeks)

        // 如果是当前学期，计算当前周
        if (selectedTerm === currentTerm?.XNXQ && weeks.length > 0) {
          try {
            const datesRes = await api.get(`/schedule/week?xn=${xn}&xq=${xq}&week=1`)
            const firstWeekDates = datesRes.data.dates
            if (firstWeekDates && firstWeekDates['1']) {
              const firstDate = new Date(firstWeekDates['1'])
              const today = new Date()
              const diffDays = Math.floor((today.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24))
              const calculatedWeek = Math.floor(diffDays / 7) + 1
              const validWeek = Math.max(1, Math.min(calculatedWeek, weeks[weeks.length - 1].ZC))
              setCurrentWeek(validWeek)
              setSelectedWeek(validWeek)
            } else {
              setSelectedWeek(weeks[0]?.ZC || 1)
            }
          } catch {
            setSelectedWeek(weeks[0]?.ZC || 1)
          }
        } else if (weeks.length > 0) {
          setCurrentWeek(null)
          setSelectedWeek(weeks[0].ZC)
        }
      } catch (err) {
        console.error('Failed to fetch week list:', err)
        message.error('获取周次列表失败')
      }
    }
    fetchWeekList()
  }, [selectedTerm, currentTerm])

  // 解析学期代码为学年和学期
  // 支持两种格式: "2025-2026-1" 或 "2025-20261"
  const parseTermCode = (termCode: string): [string, string] => {
    const parts = termCode.split('-')
    if (parts.length >= 3) {
      // 格式: "2025-2026-1"
      return [`${parts[0]}-${parts[1]}`, parts[2]]
    } else if (parts.length === 2 && parts[1].length === 5) {
      // 格式: "2025-20261" (第二部分是4位年份+1位学期)
      return [`${parts[0]}-${parts[1].slice(0, 4)}`, parts[1].slice(4)]
    }
    return ['', '']
  }

  // 加载课表数据
  useEffect(() => {
    if (!selectedTerm) return

    const fetchSchedule = async () => {
      setLoading(true)
      try {
        const [xn, xq] = parseTermCode(selectedTerm)
        const params = new URLSearchParams({ xn, xq })

        let url = viewMode === 'full'
          ? `/schedule/full?${params}`
          : `/schedule/week?${params}&week=${selectedWeek}`

        const res = await api.get(url)
        setScheduleData(res.data)
      } catch (err) {
        console.error('Failed to fetch schedule:', err)
        message.error('获取课表失败')
      } finally {
        setLoading(false)
      }
    }

    if (viewMode === 'week' && selectedWeek) {
      fetchSchedule()
    } else if (viewMode === 'full') {
      fetchSchedule()
    }
  }, [selectedTerm, selectedWeek, viewMode])

  // 导出课表为ICS格式
  const handleExport = () => {
    if (!scheduleData || scheduleData.schedule.length === 0) {
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
    if (viewMode === 'week' && scheduleData.dates && Object.keys(scheduleData.dates).length > 0) {
      scheduleData.schedule.forEach((course, idx) => {
        const dateStr = scheduleData.dates[course.weekday]
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
          `DESCRIPTION:教师: ${course.teacher}\\n周次: ${course.weeks}`,
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
      const termName = termList.find(t => t.dm === selectedTerm)?.mc || selectedTerm
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
          style={{
            minHeight: 80,
            border: '1px solid #f0f0f0',
            background: '#fafafa',
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
            title={`${course.course_name} - ${course.teacher} - ${course.weeks}`}
          >
            <div
              onClick={() => handleCourseClick(course)}
              style={{
                flex: 1,
                minHeight: courses.length > 1 ? 60 : 80,
                padding: 4,
                border: '1px solid #d9d9d9',
                background: courseColorMap[course.course_name] || '#e6f7ff',
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
              <div style={{ color: '#666', fontSize: 10 }}>{course.teacher}</div>
              <div style={{ color: '#1890ff', fontSize: 9, fontWeight: 500 }}>
                {course.weeks}
              </div>
              <div style={{ color: '#999', fontSize: 9 }}>
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
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
        <Select
          value={selectedTerm}
          onChange={setSelectedTerm}
          style={{ width: 180 }}
          placeholder="选择学期"
          options={termList.map(t => ({
            value: t.dm,
            label: t.mc + (t.dm === currentTerm?.XNXQ ? ' (当前)' : ''),
          }))}
        />
        {viewMode === 'week' && (
          <>
            <Select
              value={selectedWeek}
              onChange={setSelectedWeek}
              style={{ width: 140 }}
              options={weekList.map(w => ({
                value: w.ZC,
                label: w.ZC === currentWeek ? `第${w.ZC}周 (当前)` : `第${w.ZC}周`,
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
              background: '#e8e8e8',
            }}
          >
            {/* 表头 */}
            <div style={{ background: '#fafafa', padding: 8, textAlign: 'center', fontWeight: 'bold' }}>
              节次
            </div>
            {WEEKDAYS.map((day, idx) => (
              <div
                key={day}
                style={{
                  background: '#fafafa',
                  padding: 8,
                  textAlign: 'center',
                  fontWeight: 'bold',
                }}
              >
                <div>{day}</div>
                {scheduleData?.dates && scheduleData.dates[idx + 1] && (
                  <div style={{ fontSize: 11, color: '#999' }}>
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
                  style={{
                    background: '#fafafa',
                    padding: 8,
                    textAlign: 'center',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                  }}
                >
                  <div style={{ fontWeight: 'bold', fontSize: 12 }}>{period.label}</div>
                  <div style={{ fontSize: 10, color: '#999' }}>{period.time}</div>
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
              <Tag color="blue">{selectedCourse.weeks}</Tag>
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
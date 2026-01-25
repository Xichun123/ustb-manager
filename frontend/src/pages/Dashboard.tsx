import { useEffect, useState, useMemo } from 'react'
import { Card, Row, Col, Avatar, Descriptions, Spin, Tooltip, Button, Statistic } from 'antd'
import { UserOutlined, CalendarOutlined, WifiOutlined, LoginOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'
import WifiLoginModal from '../components/WifiLoginModal'

interface StudentInfo {
  XM?: string
  XH?: string
  ZYMC?: string
  YXMC?: string
  BJMC?: string
  NJMC?: string
  XB?: string
}

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
}

interface ScheduleData {
  schedule: CourseItem[]
  dates: Record<string, string>
  week: number | null
  term: string
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

interface WifiStatus {
  logged_in: boolean
  has_credential: boolean
}

interface WifiFlow {
  balance: number
  used_flow: number
  update_time: string
}

export function Dashboard() {
  const navigate = useNavigate()
  const [studentInfo, setStudentInfo] = useState<StudentInfo | null>(null)
  const [scheduleData, setScheduleData] = useState<ScheduleData | null>(null)
  const [currentWeek, setCurrentWeek] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  // 校园网相关状态
  const [, setWifiStatus] = useState<WifiStatus | null>(null)
  const [wifiFlow, setWifiFlow] = useState<WifiFlow | null>(null)
  const [wifiLoading, setWifiLoading] = useState(false)
  const [wifiLoginOpen, setWifiLoginOpen] = useState(false)

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

  // 构建课表网格数据
  const scheduleGrid = useMemo(() => {
    if (!scheduleData) return []

    const grid: CourseItem[][][] = Array(6).fill(null).map(() =>
      Array(7).fill(null).map(() => [])
    )

    scheduleData.schedule.forEach(course => {
      const periodIdx = course.period - 1
      const weekdayIdx = course.weekday - 1
      if (periodIdx >= 0 && periodIdx < 6 && weekdayIdx >= 0 && weekdayIdx < 7) {
        grid[periodIdx][weekdayIdx].push(course)
      }
    })

    return grid
  }, [scheduleData])

  // 加载校园网状态和流量信息
  const fetchWifiData = async () => {
    setWifiLoading(true)
    try {
      // 先检查登录状态
      const statusRes = await api.get('/wifi/status')
      setWifiStatus(statusRes.data)

      // 如果已登录或有保存的凭据，尝试获取流量信息
      if (statusRes.data.logged_in || statusRes.data.has_credential) {
        try {
          const flowRes = await api.get('/wifi/flow')
          setWifiFlow(flowRes.data)
          // 如果能获取到流量，说明已登录
          setWifiStatus({ logged_in: true, has_credential: true })
        } catch {
          // 获取流量失败，可能需要重新登录
          setWifiFlow(null)
          setWifiStatus({ logged_in: false, has_credential: statusRes.data.has_credential })
        }
      }
    } catch {
      // 状态查询失败
      setWifiStatus({ logged_in: false, has_credential: false })
    } finally {
      setWifiLoading(false)
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        // 获取学生信息
        const studentRes = await api.get('/grades/student-info')
        setStudentInfo(studentRes.data)

        // 获取当前学期信息
        const termRes = await api.get('/schedule/current-term')
        const { XN, XQ } = termRes.data

        // 获取周次列表并计算当前周
        const weekRes = await api.get(`/schedule/week-list?xn=${XN}&xq=${XQ}`)
        const weeks = weekRes.data.filter((w: { ZC: number }) => w.ZC !== 99)

        if (weeks.length > 0) {
          // 获取第一周的日期来计算当前周
          const datesRes = await api.get(`/schedule/week?xn=${XN}&xq=${XQ}&week=1`)
          const firstWeekDates = datesRes.data.dates
          if (firstWeekDates && firstWeekDates['1']) {
            const firstDate = new Date(firstWeekDates['1'])
            const today = new Date()
            const diffDays = Math.floor((today.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24))
            const calculatedWeek = Math.floor(diffDays / 7) + 1
            const validWeek = Math.max(1, Math.min(calculatedWeek, weeks[weeks.length - 1].ZC))
            setCurrentWeek(validWeek)

            // 获取当前周的课表
            const scheduleRes = await api.get(`/schedule/week?xn=${XN}&xq=${XQ}&week=${validWeek}`)
            setScheduleData(scheduleRes.data)
          }
        }
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    fetchWifiData()
  }, [])

  return (
    <AppLayout>
      <Spin spinning={loading}>
        <Row gutter={[24, 24]}>
          {/* 学生信息卡片 */}
          <Col xs={24} lg={12}>
            <Card
              title={
                <span>
                  <UserOutlined style={{ marginRight: 8 }} />
                  学生信息
                </span>
              }
              style={{ height: '100%' }}
            >
              {studentInfo && (
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 24 }}>
                  <Avatar
                    size={80}
                    icon={<UserOutlined />}
                    style={{ backgroundColor: '#003366', flexShrink: 0 }}
                  />
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="姓名">
                      <strong style={{ fontSize: 16 }}>{studentInfo.XM || '-'}</strong>
                    </Descriptions.Item>
                    <Descriptions.Item label="学号">{studentInfo.XH || '-'}</Descriptions.Item>
                    <Descriptions.Item label="院系">{studentInfo.YXMC || '-'}</Descriptions.Item>
                    <Descriptions.Item label="专业">{studentInfo.ZYMC || '-'}</Descriptions.Item>
                    <Descriptions.Item label="班级">{studentInfo.BJMC || '-'}</Descriptions.Item>
                    <Descriptions.Item label="年级">{studentInfo.NJMC || '-'}</Descriptions.Item>
                  </Descriptions>
                </div>
              )}
            </Card>
          </Col>

          {/* 校园网信息卡片 */}
          <Col xs={24} lg={12}>
            <Card
              title={
                <span>
                  <WifiOutlined style={{ marginRight: 8 }} />
                  校园网
                </span>
              }
              style={{ height: '100%' }}
              extra={
                wifiFlow && (
                  <Button
                    type="text"
                    icon={<ReloadOutlined />}
                    onClick={fetchWifiData}
                    loading={wifiLoading}
                  />
                )
              }
            >
              <Spin spinning={wifiLoading}>
                {wifiFlow ? (
                  // 已登录，显示流量信息
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic
                        title="账户余额"
                        value={wifiFlow.balance}
                        precision={2}
                        suffix="元"
                        valueStyle={{ color: wifiFlow.balance < 5 ? '#cf1322' : '#3f8600' }}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="已用流量"
                        value={wifiFlow.used_flow >= 1024 ? (wifiFlow.used_flow / 1024).toFixed(2) : wifiFlow.used_flow.toFixed(2)}
                        suffix={wifiFlow.used_flow >= 1024 ? 'GB' : 'MB'}
                      />
                    </Col>
                  </Row>
                ) : (
                  // 未登录，显示登录提示
                  <div style={{ textAlign: 'center', padding: '20px 0' }}>
                    <WifiOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
                    <div style={{ color: '#999', marginBottom: 16 }}>
                      登录校园网账号查看余额和流量
                    </div>
                    <Button
                      type="primary"
                      icon={<LoginOutlined />}
                      onClick={() => setWifiLoginOpen(true)}
                    >
                      登录校园网
                    </Button>
                  </div>
                )}
              </Spin>
            </Card>
          </Col>

          {/* 本周课表卡片 */}
          <Col xs={24}>
            <Card
              title={
                <span>
                  <CalendarOutlined style={{ marginRight: 8 }} />
                  本周课表 {currentWeek && `(第${currentWeek}周)`}
                </span>
              }
              extra={<Button type="link" onClick={() => navigate('/schedule')}>查看完整课表</Button>}
            >
              {/* 课表表头 */}
              <div style={{ display: 'grid', gridTemplateColumns: '50px repeat(7, 1fr)', gap: 1 }}>
                <div style={{ background: '#fafafa', padding: 6, textAlign: 'center', fontWeight: 'bold', fontSize: 12 }}>
                  节次
                </div>
                {WEEKDAYS.map((day, idx) => (
                  <div
                    key={day}
                    style={{
                      background: '#fafafa',
                      padding: 6,
                      textAlign: 'center',
                      fontWeight: 'bold',
                      fontSize: 12,
                    }}
                  >
                    <div>{day}</div>
                    {scheduleData?.dates[idx + 1] && (
                      <div style={{ fontSize: 10, color: '#999' }}>
                        {scheduleData.dates[idx + 1]}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* 课表内容 */}
              {PERIOD_TIMES.map((period, periodIdx) => (
                <div
                  key={periodIdx}
                  style={{ display: 'grid', gridTemplateColumns: '50px repeat(7, 1fr)', gap: 1 }}
                >
                  <div
                    style={{
                      background: '#fafafa',
                      padding: 6,
                      textAlign: 'center',
                      fontSize: 11,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                    }}
                  >
                    <div style={{ fontWeight: 'bold' }}>{period.label}</div>
                    <div style={{ color: '#999', fontSize: 9 }}>{period.time}</div>
                  </div>
                  {WEEKDAYS.map((_, weekdayIdx) => {
                    const courses = scheduleGrid[periodIdx]?.[weekdayIdx] || []
                    if (courses.length === 0) {
                      return (
                        <div
                          key={`${periodIdx}-${weekdayIdx}`}
                          style={{
                            minHeight: 60,
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
                          minHeight: 60,
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
                              style={{
                                flex: 1,
                                minHeight: courses.length > 1 ? 40 : 60,
                                padding: 4,
                                border: '1px solid #d9d9d9',
                                background: courseColorMap[course.course_name] || '#e6f7ff',
                                cursor: 'pointer',
                                overflow: 'hidden',
                                fontSize: 10,
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'center',
                                textAlign: 'center',
                              }}
                              onClick={() => navigate('/schedule')}
                            >
                              <div style={{ fontWeight: 'bold', marginBottom: 1, lineHeight: 1.2 }}>
                                {course.course_name.length > 5
                                  ? course.course_name.slice(0, 5) + '...'
                                  : course.course_name}
                              </div>
                              <div style={{ color: '#666', fontSize: 9 }}>{course.teacher}</div>
                              <div style={{ color: '#999', fontSize: 8 }}>
                                {course.location.replace('【校本部】', '')}
                              </div>
                            </div>
                          </Tooltip>
                        ))}
                      </div>
                    )
                  })}
                </div>
              ))}
            </Card>
          </Col>
        </Row>
      </Spin>

      {/* 校园网登录弹窗 */}
      <WifiLoginModal
        open={wifiLoginOpen}
        onClose={() => setWifiLoginOpen(false)}
        onSuccess={fetchWifiData}
      />
    </AppLayout>
  )
}
import { useCallback, useEffect, useState } from 'react'
import { Card, Col, Empty, Row, Select, Statistic, Tag, message } from 'antd'
import AppLayout from '../components/AppLayout'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'

type AcademicContext = components['schemas']['AcademicContextResponse']
type AcademicCalendar = components['schemas']['AcademicCalendar']

const MONTHS = Array.from({ length: 12 }, (_, index) => ({
  value: index + 1,
  label: `${index + 1}月`,
}))

export default function CalendarPage() {
  const [term, setTerm] = useState('')
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [calendar, setCalendar] = useState<AcademicCalendar | null>(null)
  const [loading, setLoading] = useState(true)

  const loadMonth = useCallback(async (termCode: string, selectedMonth: number) => {
    try {
      setLoading(true)
      const { data } = await api.get<AcademicCalendar>('/academic/calendar', {
        params: { term: termCode, month: selectedMonth },
      })
      setCalendar(data)
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '获取校历失败'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      try {
        const { data } = await api.get<AcademicContext>('/academic/context')
        setTerm(data.teaching_term.code)
        await loadMonth(data.teaching_term.code, month)
      } catch (error: unknown) {
        setLoading(false)
        message.error(getApiErrorMessage(error, '获取教学学期失败'))
      }
    }
    init()
  }, [loadMonth])

  const changeMonth = (value: number) => {
    setMonth(value)
    if (term) loadMonth(term, value)
  }

  const weekGroups = new Map<number | null, string[]>()
  for (const item of calendar?.dates || []) {
    const key = item.week ?? null
    weekGroups.set(key, [...(weekGroups.get(key) || []), item.date])
  }

  return (
    <AppLayout>
      <Card
        title={`校历 ${term}`}
        loading={loading}
        extra={<Select value={month} options={MONTHS} onChange={changeMonth} style={{ width: 100 }} />}
      >
        {weekGroups.size ? (
          <Row gutter={[16, 16]}>
            {Array.from(weekGroups.entries()).map(([week, dates]) => (
              <Col xs={24} md={12} lg={8} key={`${week}-${dates[0]}`}>
                <Card size="small">
                  <Statistic
                    title={week ? `第 ${week} 教学周` : '非教学周'}
                    value={dates.length}
                    suffix="天"
                  />
                  <div style={{ marginTop: 12 }}>
                    {dates.map(date => <Tag key={date}>{date}</Tag>)}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        ) : <Empty description="该月暂无校历数据" />}
      </Card>
    </AppLayout>
  )
}

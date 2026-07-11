import { useCallback, useEffect, useState } from 'react'
import { Card, Empty, Spin, Table, Tag, message } from 'antd'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import AppLayout from '../components/AppLayout'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'

type Exam = components['schemas']['ExamRecord']
type ExamPage = components['schemas']['ExamPage']

const PAGE_SIZE = 20

export default function ExamsPage() {
  const [loading, setLoading] = useState(true)
  const [exams, setExams] = useState<Exam[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchExams = useCallback(async (nextPage: number) => {
    try {
      setLoading(true)
      const { data } = await api.get<ExamPage>('/exams', {
        params: { page: nextPage, page_size: PAGE_SIZE },
      })
      setExams(data.items || [])
      setTotal(data.total)
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '获取考试安排失败'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchExams(page)
  }, [fetchExams, page])

  const columns: ColumnsType<Exam> = [
    { title: '课程名称', dataIndex: 'course_name', key: 'course_name', width: 200, fixed: 'left' },
    {
      title: '考试类型',
      dataIndex: 'exam_type',
      key: 'exam_type',
      width: 90,
      render: (type: string) => <Tag color={type === '期末' ? 'red' : type === '期中' ? 'orange' : 'blue'}>{type || '-'}</Tag>,
    },
    {
      title: '考试日期',
      key: 'date',
      width: 180,
      render: (_, record) => [
        record.week ? `第${record.week}周` : '',
        record.weekday_name,
        record.date_display || record.date,
      ].filter(Boolean).join(' ') || '-',
    },
    { title: '考试时间', dataIndex: 'time', key: 'time', width: 120, render: value => value || '-' },
    {
      title: '考试地点',
      key: 'location',
      width: 180,
      render: (_, record) => `${record.building} ${record.room}`.trim() || '-',
    },
    { title: '座位号', dataIndex: 'seat_number', key: 'seat_number', width: 90, render: value => value || '-' },
    { title: '课程代码', dataIndex: 'course_code', key: 'course_code', width: 110 },
    { title: '备注', dataIndex: 'remark', key: 'remark', width: 150, render: value => value || '-' },
  ]

  const getExamStatus = (examDate: string) => {
    if (!examDate) return 'upcoming'
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const exam = new Date(examDate)
    exam.setHours(0, 0, 0, 0)
    if (exam < today) return 'past'
    if (exam.getTime() === today.getTime()) return 'today'
    return 'upcoming'
  }

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setPage(pagination.current || 1)
  }

  return (
    <AppLayout>
      <Spin spinning={loading}>
        {exams.length > 0 ? (
          <Card title="考试安排">
            <Table
              columns={columns}
              dataSource={exams}
              rowKey="id"
              scroll={{ x: 1100 }}
              onChange={handleTableChange}
              pagination={{
                current: page,
                pageSize: PAGE_SIZE,
                total,
                showSizeChanger: false,
                showTotal: count => `共 ${count} 场考试`,
              }}
              rowClassName={record => {
                const status = getExamStatus(record.date)
                if (status === 'past') return 'exam-row-past'
                if (status === 'today') return 'exam-row-today'
                return ''
              }}
            />
            <style>{`
              .exam-row-past { opacity: 0.5; }
              .exam-row-today, .exam-row-today td { background-color: #fff7e6 !important; }
            `}</style>
          </Card>
        ) : (
          <Card><Empty description="暂无考试安排" /></Card>
        )}
      </Spin>
    </AppLayout>
  )
}

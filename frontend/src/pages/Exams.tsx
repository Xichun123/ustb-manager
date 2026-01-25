import { useEffect, useState } from 'react'
import { Table, Card, Tag, message, Spin, Empty } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'

interface ExamItem {
  course_code: string
  course_name: string
  course_name_en: string
  exam_type: string
  exam_date: string
  exam_date_display: string
  exam_time: string
  weekday: string
  week_number: number
  start_period: number
  end_period: number
  building: string
  room: string
  campus: string
  term: string
  remark: string
}

export default function ExamsPage() {
  const [loading, setLoading] = useState(true)
  const [exams, setExams] = useState<ExamItem[]>([])

  useEffect(() => {
    fetchExams()
  }, [])

  const fetchExams = async () => {
    try {
      setLoading(true)
      const { data } = await api.get('/schedule/exams')
      setExams(data)
    } catch (error) {
      message.error('获取考试安排失败')
    } finally {
      setLoading(false)
    }
  }

  const columns: ColumnsType<ExamItem> = [
    {
      title: '课程名称',
      dataIndex: 'course_name',
      key: 'course_name',
      width: 180,
      fixed: 'left',
    },
    {
      title: '考试类型',
      dataIndex: 'exam_type',
      key: 'exam_type',
      width: 80,
      render: (type: string) => (
        <Tag color={type === '期末' ? 'red' : type === '期中' ? 'orange' : 'blue'}>
          {type}
        </Tag>
      ),
    },
    {
      title: '考试日期',
      key: 'exam_date_full',
      width: 160,
      render: (_, record) => (
        <span>
          第{record.week_number}周 {record.weekday} {record.exam_date_display}
        </span>
      ),
    },
    {
      title: '考试时间',
      dataIndex: 'exam_time',
      key: 'exam_time',
      width: 120,
    },
    {
      title: '考试地点',
      key: 'location',
      width: 180,
      render: (_, record) => {
        if (!record.building && record.room) {
          return record.room
        }
        return `${record.building || ''} ${record.room || ''}`.trim() || '-'
      },
    },
    {
      title: '校区',
      dataIndex: 'campus',
      key: 'campus',
      width: 80,
    },
    {
      title: '课程代码',
      dataIndex: 'course_code',
      key: 'course_code',
      width: 100,
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
      width: 120,
      render: (text: string) => text || '-',
    },
  ]

  // 根据考试日期判断状态
  const getExamStatus = (examDate: string) => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const exam = new Date(examDate)
    exam.setHours(0, 0, 0, 0)

    if (exam < today) return 'past'
    if (exam.getTime() === today.getTime()) return 'today'
    return 'upcoming'
  }

  return (
    <AppLayout>
      <Spin spinning={loading}>
        {exams.length > 0 ? (
          <Card title="考试安排">
            <Table
              columns={columns}
              dataSource={exams}
              rowKey={(record) => `${record.course_code}-${record.exam_date}`}
              scroll={{ x: 1100 }}
              pagination={false}
              rowClassName={(record) => {
                const status = getExamStatus(record.exam_date)
                if (status === 'past') return 'exam-row-past'
                if (status === 'today') return 'exam-row-today'
                return ''
              }}
            />
            <style>{`
              .exam-row-past {
                opacity: 0.5;
              }
              .exam-row-today {
                background-color: #fff7e6 !important;
              }
              .exam-row-today td {
                background-color: #fff7e6 !important;
              }
            `}</style>
          </Card>
        ) : (
          <Card>
            <Empty description="暂无考试安排" />
          </Card>
        )}
      </Spin>
    </AppLayout>
  )
}

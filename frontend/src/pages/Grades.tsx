import { useEffect, useState } from 'react'
import { Table, Card, Statistic, Row, Col, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'

interface Grade {
  xnxq: string
  kcdm: string
  kcmc: string
  kcmc_en: string
  xf: string
  xs: string
  xscj: string
  zpcj: string
  kcxzmc: string
  kclbmc: string
  jsxm: string
  kkdw: string
  bkcxbj: string
}

interface GPAStats {
  gpa: number
  total_credits: number
  passed_credits: number
  failed_count: number
}

export default function Grades() {
  const [grades, setGrades] = useState<Grade[]>([])
  const [gpaStats, setGpaStats] = useState<GPAStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    fetchGrades()
  }, [])

  const fetchGrades = async () => {
    try {
      setLoading(true)
      const { data } = await api.get('/grades/list', {
        params: { page_size: 200 }
      })
      setGrades(data.grades)
      setGpaStats(data.gpa_stats)
      setTotal(data.total)
    } catch (error) {
      message.error('获取成绩失败')
    } finally {
      setLoading(false)
    }
  }

  const columns: ColumnsType<Grade> = [
    {
      title: '学年学期',
      dataIndex: 'xnxq',
      key: 'xnxq',
      width: 120,
      fixed: 'left',
    },
    {
      title: '课程名称',
      dataIndex: 'kcmc',
      key: 'kcmc',
      width: 200,
      fixed: 'left',
    },
    {
      title: '成绩',
      dataIndex: 'xscj',
      key: 'xscj',
      width: 80,
      render: (score: string) => {
        const numScore = parseFloat(score)
        let color = 'inherit'
        if (!isNaN(numScore)) {
          if (numScore >= 90) color = '#52c41a'
          else if (numScore >= 80) color = '#1890ff'
          else if (numScore >= 70) color = '#faad14'
          else if (numScore >= 60) color = '#ff7a45'
          else color = '#f5222d'
        }
        return <span style={{ color, fontWeight: 'bold' }}>{score}</span>
      },
    },
    {
      title: '学分',
      dataIndex: 'xf',
      key: 'xf',
      width: 80,
    },
    {
      title: '学时',
      dataIndex: 'xs',
      key: 'xs',
      width: 80,
    },
    {
      title: '课程性质',
      dataIndex: 'kcxzmc',
      key: 'kcxzmc',
      width: 100,
      render: (text: string) => text || '-',
    },
    {
      title: '课程类别',
      dataIndex: 'kclbmc',
      key: 'kclbmc',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '教师',
      dataIndex: 'jsxm',
      key: 'jsxm',
      width: 100,
    },
    {
      title: '开课单位',
      dataIndex: 'kkdw',
      key: 'kkdw',
      width: 180,
    },
    {
      title: '标记',
      dataIndex: 'bkcxbj',
      key: 'bkcxbj',
      width: 100,
    },
  ]

  return (
    <AppLayout>
      {gpaStats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic
                title="GPA"
                value={gpaStats.gpa}
                precision={2}
                valueStyle={{ color: gpaStats.gpa >= 3.5 ? '#3f8600' : gpaStats.gpa >= 3.0 ? '#1890ff' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic
                title="总学分"
                value={gpaStats.total_credits}
                precision={1}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic
                title="已获学分"
                value={gpaStats.passed_credits}
                precision={1}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic
                title="不及格课程"
                value={gpaStats.failed_count}
                valueStyle={{ color: gpaStats.failed_count > 0 ? '#cf1322' : '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <Table
          columns={columns}
          dataSource={grades}
          rowKey={(record) => `${record.xnxq}-${record.kcdm}-${record.bkcxbj}`}
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            total,
            pageSize: 200,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>
    </AppLayout>
  )
}
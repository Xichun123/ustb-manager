import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Modal, Row, Statistic, Table, message } from 'antd'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import AppLayout from '../components/AppLayout'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'

type Grade = components['schemas']['GradeRecord']
type GradePage = components['schemas']['GradePage']
type GradeSummary = components['schemas']['GradeSummary']
type GradeComponent = components['schemas']['GradeComponent']

const PAGE_SIZE = 50

export default function Grades() {
  const [grades, setGrades] = useState<Grade[]>([])
  const [summary, setSummary] = useState<GradeSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [selectedGrade, setSelectedGrade] = useState<Grade | null>(null)
  const [gradeComponents, setGradeComponents] = useState<GradeComponent[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const fetchGrades = useCallback(async (nextPage: number) => {
    try {
      setLoading(true)
      const [gradesRes, summaryRes] = await Promise.all([
        api.get<GradePage>('/grades', { params: { page: nextPage, page_size: PAGE_SIZE } }),
        api.get<GradeSummary>('/grades/summary'),
      ])
      setGrades(gradesRes.data.items || [])
      setTotal(gradesRes.data.total)
      setSummary(summaryRes.data)
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '获取成绩失败'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGrades(page)
  }, [fetchGrades, page])

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setPage(pagination.current || 1)
  }

  const handleScoreClick = async (grade: Grade) => {
    setSelectedGrade(grade)
    setGradeComponents([])
    setDetailError(null)
    setDetailOpen(true)

    if (!grade.task_id) return

    try {
      setDetailLoading(true)
      const { data } = await api.get<GradeComponent[]>(
        `/grades/${encodeURIComponent(grade.id)}/components`,
        { params: { task_id: grade.task_id } }
      )
      setGradeComponents(data)
    } catch (error: unknown) {
      const errorMessage = getApiErrorMessage(error, '获取成绩明细失败')
      setDetailError(errorMessage)
      message.error(errorMessage)
    } finally {
      setDetailLoading(false)
    }
  }

  const columns: ColumnsType<Grade> = [
    {
      title: '学年学期',
      dataIndex: 'term',
      key: 'term',
      width: 130,
      fixed: 'left',
    },
    {
      title: '课程名称',
      dataIndex: 'course_name',
      key: 'course_name',
      width: 220,
      fixed: 'left',
    },
    {
      title: '成绩',
      dataIndex: 'score',
      key: 'score',
      width: 80,
      render: (score: string, record) => {
        const numeric = record.score_numeric
        let color = 'inherit'
        if (numeric !== null && numeric !== undefined) {
          if (numeric >= 90) color = '#52c41a'
          else if (numeric >= 80) color = '#1890ff'
          else if (numeric >= 70) color = '#faad14'
          else if (numeric >= 60) color = '#ff7a45'
          else color = '#f5222d'
        }
        return (
          <Button
            type="link"
            size="small"
            style={{ color, fontWeight: 'bold', padding: 0 }}
            onClick={() => handleScoreClick(record)}
          >
            {score}
          </Button>
        )
      },
    },
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 90,
      render: (value, record) => {
        if (value === null || value === undefined) return '-'
        return record.rank_total ? `${value}/${record.rank_total}` : value
      },
    },
    { title: '学分', dataIndex: 'credit', key: 'credit', width: 80 },
    { title: '学时', dataIndex: 'hours', key: 'hours', width: 80, render: value => value ?? '-' },
    { title: '课程性质', dataIndex: 'course_nature', key: 'course_nature', width: 110, render: value => value || '-' },
    { title: '课程类别', dataIndex: 'course_category', key: 'course_category', width: 130, render: value => value || '-' },
    { title: '开课单位', dataIndex: 'college', key: 'college', width: 180, render: value => value || '-' },
    { title: '考试次数', dataIndex: 'exam_attempt', key: 'exam_attempt', width: 100, render: value => value || '-' },
  ]

  return (
    <AppLayout>
      {summary && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic title="官方 GPA" value={summary.official_gpa ?? '-'} precision={2} />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic title="已获学分" value={summary.earned_credits} precision={1} />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic title="已通过课程" value={summary.passed_courses} suffix="门" />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card>
              <Statistic
                title="不及格课程"
                value={summary.failed_courses}
                valueStyle={{ color: summary.failed_courses > 0 ? '#cf1322' : '#3f8600' }}
                suffix="门"
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <Table
          columns={columns}
          dataSource={grades}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1280 }}
          onChange={handleTableChange}
          pagination={{
            current: page,
            total,
            pageSize: PAGE_SIZE,
            showSizeChanger: false,
            showTotal: count => `共 ${count} 条`,
          }}
        />
      </Card>

      <Modal
        title={selectedGrade ? `${selectedGrade.course_name} · 成绩明细` : '成绩明细'}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={640}
      >
        {detailError ? (
          <Alert
            type="warning"
            showIcon
            message="暂时无法获取成绩明细"
            description={detailError}
          />
        ) : (
          <Table<GradeComponent>
            rowKey={(item, index) => `${item.name}-${index}`}
            loading={detailLoading}
            dataSource={gradeComponents}
            pagination={false}
            size="small"
            locale={{ emptyText: selectedGrade?.task_id ? '暂无成绩明细' : '该课程不支持成绩明细查询' }}
            columns={[
              { title: '分项', dataIndex: 'name', key: 'name' },
              { title: '得分', dataIndex: 'score', key: 'score', width: 100, render: value => value ?? '-' },
              { title: '满分', dataIndex: 'max_score', key: 'max_score', width: 100, render: value => value ?? '-' },
              {
                title: '比重',
                dataIndex: 'weight',
                key: 'weight',
                width: 100,
                render: value => value === null || value === undefined ? '-' : `${value}%`,
              },
            ]}
          />
        )}
      </Modal>
    </AppLayout>
  )
}

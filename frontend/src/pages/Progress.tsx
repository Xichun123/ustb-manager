import { useEffect, useState } from 'react'
import { Alert, Card, Col, Empty, Progress, Row, Spin, Statistic, Table, Tabs, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import AppLayout from '../components/AppLayout'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'

type ProgressSummary = components['schemas']['AcademicProgress']
type ProgressModule = components['schemas']['AcademicProgressModule']
type ProgressModules = components['schemas']['AcademicProgressModules']
type ProgressCategory = components['schemas']['AcademicProgressCategory']
type ProgressCourse = components['schemas']['AcademicProgressCourse']
type ProgressCourses = components['schemas']['AcademicProgressCourses']
type AcademicWarning = components['schemas']['AcademicWarning']

const completion = (done?: number | null, required?: number | null) => {
  if (!required) return 0
  return Math.min(100, Math.round(((done || 0) / required) * 100))
}

export default function ProgressPage() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<ProgressSummary | null>(null)
  const [modules, setModules] = useState<ProgressModule[]>([])
  const [categories, setCategories] = useState<ProgressCategory[]>([])
  const [courses, setCourses] = useState<ProgressCourse[]>([])
  const [warning, setWarning] = useState<AcademicWarning | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [summaryRes, modulesRes, coursesRes, warningRes] = await Promise.all([
          api.get<ProgressSummary>('/academic/progress'),
          api.get<ProgressModules>('/academic/progress/modules'),
          api.get<ProgressCourses>('/academic/progress/courses'),
          api.get<AcademicWarning>('/academic/warnings'),
        ])
        setSummary(summaryRes.data)
        setModules(modulesRes.data.items || [])
        setCategories(coursesRes.data.categories || [])
        setCourses(coursesRes.data.courses || [])
        setWarning(warningRes.data)
      } catch (error: unknown) {
        message.error(getApiErrorMessage(error, '获取学业进度失败'))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const moduleColumns: ColumnsType<ProgressModule> = [
    { title: '模块', dataIndex: 'name', key: 'name' },
    { title: '要求学分', dataIndex: 'required_credits', key: 'required_credits', render: value => value ?? '-' },
    { title: '完成学分', dataIndex: 'completed_credits', key: 'completed_credits', render: value => value ?? '-' },
    { title: '要求课程', dataIndex: 'required_courses', key: 'required_courses', render: value => value ?? '-' },
    { title: '完成课程', dataIndex: 'completed_courses', key: 'completed_courses', render: value => value ?? '-' },
    {
      title: '完成度',
      key: 'completion',
      width: 180,
      render: (_, record) => (
        <Progress
          percent={completion(record.completed_credits, record.required_credits)}
          size="small"
        />
      ),
    },
  ]

  const courseColumns: ColumnsType<ProgressCourse> = [
    { title: '课程代码', dataIndex: 'course_code', key: 'course_code', width: 110 },
    { title: '课程名称', dataIndex: 'course_name', key: 'course_name', width: 200 },
    { title: '模块', dataIndex: 'module_name', key: 'module_name', width: 140, render: value => value || '-' },
    { title: '学分', dataIndex: 'credits', key: 'credits', width: 70, render: value => value ?? '-' },
    { title: '成绩', dataIndex: 'score', key: 'score', width: 80, render: value => value || '-' },
    { title: '学期', dataIndex: 'term', key: 'term', width: 130, render: value => value || '-' },
  ]

  const items = [
    {
      key: 'summary',
      label: '进度概览',
      children: summary ? (
        <Row gutter={[16, 16]}>
          <Col xs={12} md={6}><Card><Statistic title="要求学分" value={summary.required_credits ?? '-'} /></Card></Col>
          <Col xs={12} md={6}><Card><Statistic title="完成学分" value={summary.completed_credits ?? '-'} /></Card></Col>
          <Col xs={12} md={6}><Card><Statistic title="剩余学分" value={summary.remaining_credits ?? '-'} /></Card></Col>
          <Col xs={12} md={6}><Card><Statistic title="专业排名" value={summary.major_rank ?? '-'} suffix={summary.major_student_count ? `/ ${summary.major_student_count}` : undefined} /></Card></Col>
          <Col span={24}>
            <Card title="总完成度">
              <Progress percent={completion(summary.completed_credits, summary.required_credits)} />
            </Card>
          </Col>
        </Row>
      ) : <Empty description="暂无进度汇总" />,
    },
    {
      key: 'modules',
      label: '培养模块',
      children: modules.length ? (
        <Table
          dataSource={modules}
          columns={moduleColumns}
          rowKey="id"
          pagination={false}
          expandable={{ childrenColumnName: 'children' }}
        />
      ) : <Empty description="暂无模块要求" />,
    },
    {
      key: 'courses',
      label: '课程与分类',
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {categories.length > 0 && (
            <Row gutter={[16, 16]}>
              {categories.map(category => (
                <Col xs={24} md={12} key={category.code}>
                  <Card title={category.name}>
                    <Statistic title="完成 / 要求学分" value={category.completed_credits ?? 0} suffix={`/ ${category.required_credits ?? '-'}`} />
                    <Progress percent={completion(category.completed_credits, category.required_credits)} />
                  </Card>
                </Col>
              ))}
            </Row>
          )}
          {courses.length ? (
            <Table dataSource={courses} columns={courseColumns} rowKey="id" scroll={{ x: 900 }} />
          ) : <Empty description="暂无课程要求" />}
        </div>
      ),
    },
  ]

  return (
    <AppLayout>
      <Spin spinning={loading}>
        {warning?.has_warning && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message={`学业警示（${warning.term}）`}
            description={`未获学分课程 ${warning.unearned_courses?.length || 0} 门`}
          />
        )}
        <Tabs items={items} />
      </Spin>
    </AppLayout>
  )
}

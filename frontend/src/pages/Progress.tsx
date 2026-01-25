import { useEffect, useState } from 'react'
import { Table, Card, Tabs, message, Spin, Statistic, Row, Col, Descriptions, Empty, Collapse, Progress } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'

export default function ProgressPage() {
  const [loading, setLoading] = useState(true)
  const [requiredStatus, setRequiredStatus] = useState<any>(null)
  const [plan, setPlan] = useState<any[]>([])
  const [studentInfo, setStudentInfo] = useState<any>(null)
  const [creditStatus, setCreditStatus] = useState<any>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [requiredRes, planRes, studentInfoRes, creditRes] = await Promise.all([
        api.get('/grades/required-course-status'),
        api.get('/grades/student-plan'),
        api.get('/grades/student-info'),
        api.get('/grades/credit-completion-status')
      ])
      setRequiredStatus(requiredRes.data)
      setPlan(Array.isArray(planRes.data) ? planRes.data : [])
      setStudentInfo(studentInfoRes.data)
      setCreditStatus(creditRes.data)
    } catch (error) {
      message.error('获取学业进度失败')
    } finally {
      setLoading(false)
    }
  }

  const planColumns: ColumnsType<any> = [
    { title: '课程类别', dataIndex: 'kclbmc', key: 'kclbmc', render: (text) => text || '-' },
    { title: '课程性质', dataIndex: 'kcxzmc', key: 'kcxzmc', render: (text) => text || '-' },
    { title: '要求学分', dataIndex: 'yqxdxf', key: 'yqxdxf' },
    { title: '已完成学分', dataIndex: 'wcxf', key: 'wcxf' },
    { title: '未完成学分', dataIndex: 'wwcxf', key: 'wwcxf' },
  ]

  const courseColumns: ColumnsType<any> = [
    { title: '课程代码', dataIndex: 'course_code', key: 'course_code' },
    { title: '课程名称', dataIndex: 'course_name', key: 'course_name' },
    { title: '学分', dataIndex: 'credits', key: 'credits' },
    { title: '学时', dataIndex: 'hours', key: 'hours' },
    { title: '成绩', dataIndex: 'score', key: 'score' },
    { title: '学期', dataIndex: 'term', key: 'term' },
  ]

  const items = [
    {
      key: 'credit-completion',
      label: '学分完成情况',
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {creditStatus?.categories?.length > 0 ? (
            creditStatus.categories.map((category: any, idx: number) => {
              const percentage = category.required_credits > 0
                ? Math.round((category.completed_credits / category.required_credits) * 100)
                : 0

              return (
                <Card key={idx} title={category.category_name}>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Statistic
                        title="要求学分"
                        value={category.required_credits}
                        precision={1}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="已完成学分"
                        value={category.completed_credits}
                        precision={1}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="未完成学分"
                        value={category.remaining_credits || 0}
                        precision={1}
                        valueStyle={{ color: category.remaining_credits > 0 ? '#cf1322' : '#3f8600' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="完成度"
                        value={percentage}
                        suffix="%"
                        valueStyle={{ color: percentage >= 100 ? '#3f8600' : '#1890ff' }}
                      />
                    </Col>
                  </Row>

                  <Progress
                    percent={percentage}
                    status={percentage >= 100 ? 'success' : 'active'}
                    style={{ marginBottom: 16 }}
                  />

                  {category.courses?.length > 0 && (
                    <Collapse
                      ghost
                      items={[{
                        key: 'courses',
                        label: `已修课程 (${category.courses.length}门)`,
                        children: (
                          <Table
                            dataSource={category.courses}
                            columns={courseColumns}
                            rowKey={(record, index) => `${record.course_name}-${index}`}
                            pagination={false}
                            size="small"
                          />
                        )
                      }]}
                    />
                  )}
                </Card>
              )
            })
          ) : (
            <Card><Empty description="暂无学分完成情况数据" /></Card>
          )}
        </div>
      )
    },
    {
      key: 'required',
      label: '必修课完成情况',
      children: (
        <Card>
          {requiredStatus && (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="要求学分"
                      value={requiredStatus.yqmsxf?.YQXF || 0}
                      precision={1}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="已完成学分"
                      value={requiredStatus.ywcxf || 0}
                      precision={1}
                      valueStyle={{ color: '#3f8600' }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="未完成学分"
                      value={requiredStatus.wwcxf || 0}
                      precision={1}
                      valueStyle={{ color: parseFloat(requiredStatus.wwcxf || 0) > 0 ? '#cf1322' : '#3f8600' }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="要求门数"
                      value={requiredStatus.yqmsxf?.YQMS || 0}
                    />
                  </Card>
                </Col>
              </Row>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={12}>
                  <Card>
                    <Statistic
                      title="已完成门数"
                      value={requiredStatus.ywcms || 0}
                      valueStyle={{ color: '#3f8600' }}
                    />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card>
                    <Statistic
                      title="未完成门数"
                      value={requiredStatus.wwcms || 0}
                      valueStyle={{ color: parseFloat(requiredStatus.wwcms || 0) > 0 ? '#cf1322' : '#3f8600' }}
                    />
                  </Card>
                </Col>
              </Row>
            </>
          )}
        </Card>
      )
    },
    {
      key: 'plan',
      label: '培养方案',
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {plan.length > 0 ? (
            plan.map((p, idx) => (
              <Card
                key={idx}
                title={p.zymc || `培养方案 ${idx + 1}`}
                extra={p.nj ? `${p.nj}级` : null}
              >
                <Descriptions column={3} size="small" bordered style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="姓名">{studentInfo?.XM || '-'}</Descriptions.Item>
                  <Descriptions.Item label="院系">{studentInfo?.YXMC || '-'}</Descriptions.Item>
                  <Descriptions.Item label="专业">{studentInfo?.ZYMC || '-'}</Descriptions.Item>
                </Descriptions>

                {p.kclb_list && p.kclb_list.length > 0 ? (
                  <Table
                    dataSource={p.kclb_list}
                    columns={planColumns}
                    rowKey={(record, index) => `${record.kclbmc}-${record.kcxzmc}-${index}`}
                    pagination={false}
                    bordered
                    size="small"
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无课程类别数据" />
                )}

              </Card>
            ))
          ) : (
            <Card><Empty description="暂无培养方案数据" /></Card>
          )}
        </div>
      )
    }
  ]

  return (
    <AppLayout>
      <Spin spinning={loading}>
        <Tabs items={items} />
      </Spin>
    </AppLayout>
  )
}
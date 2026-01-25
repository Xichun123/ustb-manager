import { useState, useEffect, useMemo, useRef } from 'react'
import { Table, Select, Card, Statistic, Row, Col, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../services/api'

interface Grade {
  id: string
  semester: string
  name: string
  credit: number
  score: string
  gpa: number
}

interface RawGradeRow {
  XNXQDM?: string
  KCMC?: string
  XF?: string
  ZCJ?: string
  XFJD?: string
}

export function GradeTable() {
  const [grades, setGrades] = useState<Grade[]>([])
  const [selectedSemester, setSelectedSemester] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    const fetchData = async () => {
      setLoading(true)
      try {
        const { data } = await api.get('/byyt/grades')
        if (!mounted.current) return
        const rows: RawGradeRow[] = data.datas?.xscjcx?.rows || []
        const list = rows.map((row, i) => ({
          id: String(i),
          semester: row.XNXQDM || '',
          name: row.KCMC || '',
          credit: parseFloat(row.XF || '0') || 0,
          score: row.ZCJ || '',
          gpa: parseFloat(row.XFJD || '0') || 0,
        }))
        setGrades(list)
      } catch {
        if (mounted.current) message.error('获取成绩失败')
      } finally {
        if (mounted.current) setLoading(false)
      }
    }
    fetchData()
    return () => { mounted.current = false }
  }, [])

  const semesters = useMemo(() => {
    const set = new Set(grades.map((g) => g.semester))
    return ['all', ...Array.from(set).sort().reverse()]
  }, [grades])

  const filtered = useMemo(() => {
    if (selectedSemester === 'all') return grades
    return grades.filter((g) => g.semester === selectedSemester)
  }, [grades, selectedSemester])

  const gpa = useMemo(() => {
    if (!filtered.length) return 0
    const total = filtered.reduce((sum, g) => sum + g.credit * g.gpa, 0)
    const credits = filtered.reduce((sum, g) => sum + g.credit, 0)
    return credits ? total / credits : 0
  }, [filtered])

  const totalCredits = useMemo(() => filtered.reduce((sum, g) => sum + g.credit, 0), [filtered])

  const columns: ColumnsType<Grade> = [
    { title: '学期', dataIndex: 'semester', width: 120 },
    { title: '课程名称', dataIndex: 'name' },
    { title: '学分', dataIndex: 'credit', width: 80 },
    { title: '成绩', dataIndex: 'score', width: 80 },
    { title: '绩点', dataIndex: 'gpa', width: 80 },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card><Statistic title="平均绩点" value={gpa} precision={3} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="总学分" value={totalCredits} precision={1} /></Card>
        </Col>
      </Row>
      <div style={{ marginBottom: 16 }}>
        <Select
          value={selectedSemester}
          style={{ width: 200 }}
          onChange={setSelectedSemester}
          options={semesters.map((s) => ({ value: s, label: s === 'all' ? '全部学期' : s }))}
        />
      </div>
      <Table dataSource={filtered} columns={columns} loading={loading} rowKey="id" pagination={{ pageSize: 20 }} />
    </div>
  )
}

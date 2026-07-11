import { useCallback, useEffect, useState } from 'react'
import { Badge, Card, Modal, Table, Tag, message } from 'antd'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import AppLayout from '../components/AppLayout'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'

type Notice = components['schemas']['NoticeRecord']
type NoticePage = components['schemas']['NoticePage']

const PAGE_SIZE = 20

export default function NoticesPage() {
  const [items, setItems] = useState<Notice[]>([])
  const [selected, setSelected] = useState<Notice | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const load = useCallback(async (nextPage: number) => {
    try {
      setLoading(true)
      const { data } = await api.get<NoticePage>('/notices', {
        params: { page: nextPage, page_size: PAGE_SIZE },
      })
      setItems(data.items || [])
      setTotal(data.total)
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '获取通知失败'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(page)
  }, [load, page])

  const columns: ColumnsType<Notice> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (title, record) => (
        <a onClick={() => setSelected(record)}>
          {record.is_pinned && <Tag color="red">置顶</Tag>}
          {!record.is_read && <Badge status="processing" />}
          {title}
        </a>
      ),
    },
    { title: '发布者', dataIndex: 'sender', key: 'sender', width: 180, render: value => value || '-' },
    { title: '发布时间', dataIndex: 'sent_at', key: 'sent_at', width: 180, render: value => value || '-' },
    {
      title: '附件',
      dataIndex: 'has_attachment',
      key: 'has_attachment',
      width: 80,
      render: value => value ? <Tag color="blue">有</Tag> : '-',
    },
  ]

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setPage(pagination.current || 1)
  }

  return (
    <AppLayout>
      <Card title="通知公告">
        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showSizeChanger: false,
            showTotal: count => `共 ${count} 条通知`,
          }}
        />
      </Card>
      <Modal
        title={selected?.title}
        open={!!selected}
        onCancel={() => setSelected(null)}
        footer={null}
        width={720}
      >
        <div style={{ color: '#999', marginBottom: 16 }}>
          {[selected?.sender, selected?.sent_at].filter(Boolean).join(' · ')}
        </div>
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{selected?.content || '暂无正文'}</div>
        {selected?.external_url && (
          <p><a href={selected.external_url} target="_blank" rel="noreferrer">查看原文</a></p>
        )}
      </Modal>
    </AppLayout>
  )
}

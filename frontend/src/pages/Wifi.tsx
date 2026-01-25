import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Table, Button, Spin, message, Tag, Popconfirm, Empty, Select, DatePicker } from 'antd'
import dayjs from 'dayjs'
import { WifiOutlined, ReloadOutlined, DeleteOutlined, LoginOutlined, DesktopOutlined, MobileOutlined, QuestionCircleOutlined, ClockCircleOutlined, HistoryOutlined, AccountBookOutlined, PayCircleOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'
import WifiLoginModal from '../components/WifiLoginModal'

interface OnlineDevice {
  login_time: string
  ip_address: string
  mac_address: string
  duration_minutes: number
  used_flow_mb: number
  device_type: string
}

interface LoginHistory {
  login_time: string
  logout_time: string | null
  ip_address: string
  mac_address: string
  duration_minutes: number
  used_flow_mb: number
  cost: number
  device_type: string
}

interface WifiFlow {
  account: string
  balance: number
  used_flow: number
  available_flow: number
  status: string
  package: string
  expire_date: string
  update_time: string
  online_devices: OnlineDevice[]
  recent_history: LoginHistory[]
}

interface Device {
  online: boolean
  mac_address: string
  terminal_info: string
  last_login_time: string
  last_login_ip: string
  is_dumb_terminal: boolean
  terminal_name: string
}

interface DevicesResponse {
  total: number
  devices: Device[]
}

interface Bill {
  start_time: string
  end_time: string
  package: string
  base_fee: number
  usage_fee: number
  duration_minutes: number
  used_flow_mb: number
  bill_time: string
}

interface BillsResponse {
  year: number
  summary: {
    total_time: number
    total_flow: number
    base_fee: number
    usage_fee: number
  }
  bills: Bill[]
}

interface Payment {
  pay_time: string
  amount: number
  pay_type: string
  terminal: string
  remark: string
}

interface PaymentsResponse {
  start_date: string
  end_date: string
  total_amount: number
  payments: Payment[]
}

export default function Wifi() {
  const [loading, setLoading] = useState(true)
  const [flowData, setFlowData] = useState<WifiFlow | null>(null)
  const [devices, setDevices] = useState<Device[]>([])
  const [devicesLoading, setDevicesLoading] = useState(false)
  const [unbindingMac, setUnbindingMac] = useState<string | null>(null)
  const [loginModalOpen, setLoginModalOpen] = useState(false)
  const [needLogin, setNeedLogin] = useState(false)
  const [vendors, setVendors] = useState<Record<string, string>>({})
  const [bills, setBills] = useState<BillsResponse | null>(null)
  const [billsLoading, setBillsLoading] = useState(false)
  const [billYear, setBillYear] = useState(new Date().getFullYear())
  const [payments, setPayments] = useState<PaymentsResponse | null>(null)
  const [paymentsLoading, setPaymentsLoading] = useState(false)
  const [paymentDates, setPaymentDates] = useState<[string, string]>(() => {
    const today = new Date()
    const yearAgo = new Date(today)
    yearAgo.setFullYear(yearAgo.getFullYear() - 1)
    return [yearAgo.toISOString().split('T')[0], today.toISOString().split('T')[0]]
  })

  const fetchFlowData = async () => {
    try {
      const res = await api.get('/wifi/flow')
      setFlowData(res.data)
      setNeedLogin(false)
      return true
    } catch (err: any) {
      if (err.response?.status === 401) {
        setNeedLogin(true)
        setFlowData(null)
      }
      return false
    }
  }

  const fetchDevices = async () => {
    setDevicesLoading(true)
    try {
      const res = await api.get<DevicesResponse>('/wifi/devices')
      setDevices(res.data.devices || [])
    } catch (err: any) {
      if (err.response?.status === 401) {
        setNeedLogin(true)
      } else {
        message.error('获取设备列表失败')
      }
    } finally {
      setDevicesLoading(false)
    }
  }

  const fetchAllData = async () => {
    setLoading(true)
    const success = await fetchFlowData()
    if (success) {
      await fetchDevices()
      await fetchBills(billYear)
      await fetchPayments()
    }
    setLoading(false)
  }

  const fetchBills = async (year: number) => {
    setBillsLoading(true)
    try {
      const res = await api.get<BillsResponse>(`/wifi/bills?year=${year}`)
      setBills(res.data)
    } catch (err: any) {
      if (err.response?.status !== 401) {
        message.error('获取账单失败')
      }
    } finally {
      setBillsLoading(false)
    }
  }

  const fetchPayments = async (startDate?: string, endDate?: string) => {
    setPaymentsLoading(true)
    const start = startDate || paymentDates[0]
    const end = endDate || paymentDates[1]
    try {
      const res = await api.get<PaymentsResponse>(`/wifi/payments?start_date=${start}&end_date=${end}`)
      setPayments(res.data)
    } catch (err: any) {
      if (err.response?.status !== 401) {
        message.error('获取充值明细失败')
      }
    } finally {
      setPaymentsLoading(false)
    }
  }

  const handleUnbind = async (macAddress: string) => {
    setUnbindingMac(macAddress)
    try {
      await api.post('/wifi/unbind-mac', { mac_address: macAddress })
      message.success('解绑成功')
      // 刷新设备列表
      await fetchDevices()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '解绑失败')
    } finally {
      setUnbindingMac(null)
    }
  }

  const handleLoginSuccess = () => {
    fetchAllData()
  }

  useEffect(() => {
    fetchAllData()
  }, [])

  // 获取设备厂商信息
  useEffect(() => {
    if (devices.length > 0) {
      devices.forEach(d => {
        if (vendors[d.mac_address] === undefined) {
          api.get(`/wifi/mac-vendor?mac=${d.mac_address}`)
            .then(res => setVendors(v => ({ ...v, [d.mac_address]: res.data.is_random ? '随机MAC' : res.data.vendor })))
            .catch(() => {})
        }
      })
    }
  }, [devices])

  const formatFlow = (mb: number) => {
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(2)} GB`
    }
    return `${mb.toFixed(2)} MB`
  }

  const getDeviceIcon = (terminalInfo: string) => {
    const info = terminalInfo.toLowerCase()
    if (info.includes('iphone') || info.includes('android') || info.includes('mobile')) {
      return <MobileOutlined style={{ fontSize: 20, color: '#1890ff' }} />
    }
    if (info.includes('windows') || info.includes('mac') || info.includes('linux') || info.includes('pc')) {
      return <DesktopOutlined style={{ fontSize: 20, color: '#52c41a' }} />
    }
    return <QuestionCircleOutlined style={{ fontSize: 20, color: '#999' }} />
  }

  const columns = [
    {
      title: '设备',
      key: 'device',
      width: 220,
      render: (_: any, record: Device) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {getDeviceIcon(record.terminal_info)}
          <div>
            <div style={{ fontWeight: 500 }}>
              {record.terminal_name || record.terminal_info || '未知设备'}
            </div>
            <div style={{ fontSize: 12, color: '#999' }}>
              {record.mac_address}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 70,
      render: (_: any, record: Device) => (
        record.online
          ? <Tag color="green">在线</Tag>
          : <Tag color="default">离线</Tag>
      ),
    },
    {
      title: '终端类型',
      key: 'terminal_info',
      width: 180,
      ellipsis: true,
      render: (_: any, record: Device) => record.terminal_info || vendors[record.mac_address] || '-',
    },
    {
      title: '最近登录',
      key: 'last_login',
      width: 180,
      render: (_: any, record: Device) => (
        <div>
          <div>{record.last_login_time || '-'}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{record.last_login_ip || '-'}</div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: Device) => (
        <Popconfirm
          title="确定要解绑此设备吗？"
          description="解绑后该设备需要重新认证才能上网"
          onConfirm={() => handleUnbind(record.mac_address)}
          okText="解绑"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            loading={unbindingMac === record.mac_address}
            disabled={record.online}
          >
            解绑
          </Button>
        </Popconfirm>
      ),
    },
  ]

  // 在线设备表格列
  const onlineColumns = [
    {
      title: '上线时间',
      dataIndex: 'login_time',
      key: 'login_time',
      width: 160,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
    },
    {
      title: 'MAC地址',
      dataIndex: 'mac_address',
      key: 'mac_address',
      width: 140,
    },
    {
      title: '使用时长',
      key: 'duration',
      width: 100,
      render: (_: any, record: OnlineDevice) => {
        const minutes = record.duration_minutes
        if (minutes >= 60) {
          const hours = Math.floor(minutes / 60)
          const mins = minutes % 60
          return `${hours}小时${mins}分钟`
        }
        return `${minutes}分钟`
      },
    },
    {
      title: '使用流量',
      key: 'used_flow',
      width: 100,
      render: (_: any, record: OnlineDevice) => formatFlow(record.used_flow_mb),
    },
    {
      title: '终端类型',
      dataIndex: 'device_type',
      key: 'device_type',
      width: 120,
    },
  ]

  // 近期上网记录表格列
  const historyColumns = [
    {
      title: '上线时间',
      dataIndex: 'login_time',
      key: 'login_time',
      width: 160,
    },
    {
      title: '注销时间',
      dataIndex: 'logout_time',
      key: 'logout_time',
      width: 160,
      render: (text: string | null) => text || '-',
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
    },
    {
      title: 'MAC地址',
      key: 'mac_address',
      width: 140,
      render: (_: any, record: LoginHistory) => {
        const mac = record.mac_address.replace(/[-:]/g, '')
        return mac.match(/.{2}/g)?.join('-').toUpperCase() || record.mac_address
      },
    },
    {
      title: '使用时长',
      key: 'duration',
      width: 100,
      render: (_: any, record: LoginHistory) => {
        const minutes = record.duration_minutes
        if (minutes >= 60) {
          const hours = Math.floor(minutes / 60)
          const mins = minutes % 60
          return `${hours}小时${mins}分钟`
        }
        return `${minutes}分钟`
      },
    },
    {
      title: '使用流量',
      key: 'used_flow',
      width: 100,
      render: (_: any, record: LoginHistory) => formatFlow(record.used_flow_mb),
    },
    {
      title: '费用',
      key: 'cost',
      width: 80,
      render: (_: any, record: LoginHistory) => `¥${record.cost.toFixed(2)}`,
    },
    {
      title: '终端类型',
      dataIndex: 'device_type',
      key: 'device_type',
      width: 120,
    },
  ]

  // 账单表格列
  const billColumns = [
    {
      title: '账单周期',
      key: 'period',
      width: 180,
      render: (_: any, record: Bill) => `${record.start_time} ~ ${record.end_time}`,
    },
    {
      title: '套餐',
      dataIndex: 'package',
      key: 'package',
      width: 100,
    },
    {
      title: '使用时长',
      key: 'duration',
      width: 120,
      render: (_: any, record: Bill) => {
        const minutes = record.duration_minutes
        if (minutes >= 60) {
          const hours = Math.floor(minutes / 60)
          const mins = minutes % 60
          return `${hours}小时${mins}分钟`
        }
        return `${minutes}分钟`
      },
    },
    {
      title: '使用流量',
      key: 'used_flow',
      width: 100,
      render: (_: any, record: Bill) => formatFlow(record.used_flow_mb),
    },
    {
      title: '基本月租',
      key: 'base_fee',
      width: 90,
      render: (_: any, record: Bill) => `¥${record.base_fee.toFixed(2)}`,
    },
    {
      title: '流量计费',
      key: 'usage_fee',
      width: 90,
      render: (_: any, record: Bill) => `¥${record.usage_fee.toFixed(2)}`,
    },
    {
      title: '出账时间',
      dataIndex: 'bill_time',
      key: 'bill_time',
      width: 160,
    },
  ]

  // 充值明细表格列
  const paymentColumns = [
    {
      title: '交费时间',
      dataIndex: 'pay_time',
      key: 'pay_time',
      width: 160,
    },
    {
      title: '金额',
      key: 'amount',
      width: 100,
      render: (_: any, record: Payment) => `¥${record.amount.toFixed(2)}`,
    },
    {
      title: '交费类型',
      dataIndex: 'pay_type',
      key: 'pay_type',
      width: 120,
    },
    {
      title: '受理终端',
      dataIndex: 'terminal',
      key: 'terminal',
      width: 150,
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
    },
  ]

  if (needLogin) {
    return (
      <AppLayout standaloneMode>
        <Card>
          <Empty
            image={<WifiOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
            description="请先登录校园网"
          >
            <Button type="primary" icon={<LoginOutlined />} onClick={() => setLoginModalOpen(true)}>
              登录校园网
            </Button>
          </Empty>
        </Card>
        <WifiLoginModal
          open={loginModalOpen}
          onClose={() => setLoginModalOpen(false)}
          onSuccess={handleLoginSuccess}
        />
      </AppLayout>
    )
  }

  return (
    <AppLayout standaloneMode>
      <Spin spinning={loading}>
        {/* 流量统计卡片 */}
        <Card
          title={
            <span>
              <WifiOutlined style={{ marginRight: 8 }} />
              流量概览
            </span>
          }
          extra={
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={fetchAllData}
              loading={loading}
            >
              刷新
            </Button>
          }
          style={{ marginBottom: 24 }}
        >
          {flowData && (
            <Row gutter={[24, 24]}>
              <Col xs={12} sm={8} md={6}>
                <Statistic
                  title="账户余额"
                  value={flowData.balance}
                  precision={2}
                  suffix="元"
                  valueStyle={{ color: flowData.balance < 5 ? '#cf1322' : '#3f8600' }}
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <Statistic
                  title="本月已用"
                  value={flowData.used_flow >= 1024 ? flowData.used_flow / 1024 : flowData.used_flow}
                  precision={2}
                  suffix={flowData.used_flow >= 1024 ? 'GB' : 'MB'}
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <Statistic
                  title="剩余流量"
                  value={flowData.available_flow >= 1024 ? flowData.available_flow / 1024 : flowData.available_flow}
                  precision={2}
                  suffix={flowData.available_flow >= 1024 ? 'GB' : 'MB'}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col xs={12} sm={8} md={6}>
                <Statistic
                  title="账户状态"
                  value={flowData.status}
                  valueStyle={{
                    color: flowData.status === '正常' ? '#52c41a' : '#ff4d4f',
                    fontSize: 20
                  }}
                />
              </Col>
            </Row>
          )}
          {flowData && (
            <div style={{ marginTop: 16, color: '#999', fontSize: 12 }}>
              <span>套餐：{flowData.package || '-'}</span>
              <span style={{ marginLeft: 24 }}>到期：{flowData.expire_date || '-'}</span>
              <span style={{ marginLeft: 24 }}>更新时间：{flowData.update_time}</span>
            </div>
          )}
        </Card>

        {/* 在线信息卡片 */}
        <Card
          title={
            <span>
              <ClockCircleOutlined style={{ marginRight: 8 }} />
              在线信息 ({flowData?.online_devices?.length || 0})
            </span>
          }
          style={{ marginBottom: 24 }}
        >
          <Table
            dataSource={flowData?.online_devices || []}
            columns={onlineColumns}
            rowKey={(record) => `${record.mac_address}-${record.login_time}`}
            loading={loading}
            pagination={false}
            scroll={{ x: 800 }}
            locale={{
              emptyText: <Empty description="当前没有在线设备" />
            }}
          />
        </Card>

        {/* 近期上网记录卡片 */}
        <Card
          title={
            <span>
              <HistoryOutlined style={{ marginRight: 8 }} />
              近期上网记录
            </span>
          }
          style={{ marginBottom: 24 }}
        >
          <Table
            dataSource={flowData?.recent_history || []}
            columns={historyColumns}
            rowKey={(record) => `${record.mac_address}-${record.login_time}`}
            loading={loading}
            pagination={false}
            scroll={{ x: 1000 }}
            locale={{
              emptyText: <Empty description="暂无上网记录" />
            }}
          />
        </Card>

        {/* 历史账单卡片 */}
        <Card
          title={
            <span>
              <AccountBookOutlined style={{ marginRight: 8 }} />
              历史账单
            </span>
          }
          extra={
            <Select
              value={billYear}
              onChange={(v) => { setBillYear(v); fetchBills(v) }}
              style={{ width: 100 }}
              options={Array.from({ length: 10 }, (_, i) => {
                const y = new Date().getFullYear() - i
                return { value: y, label: `${y}年` }
              })}
            />
          }
          style={{ marginBottom: 24 }}
        >
          {bills?.summary && (
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col xs={12} sm={6}>
                <Statistic title="总使用时长" value={Math.floor(bills.summary.total_time / 60)} suffix="小时" />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="总使用流量" value={(bills.summary.total_flow / 1024).toFixed(2)} suffix="GB" />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="基本月租" value={bills.summary.base_fee} precision={2} prefix="¥" />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="流量计费" value={bills.summary.usage_fee} precision={2} prefix="¥" />
              </Col>
            </Row>
          )}
          <Table
            dataSource={bills?.bills || []}
            columns={billColumns}
            rowKey={(record) => `${record.start_time}-${record.end_time}`}
            loading={billsLoading}
            pagination={false}
            scroll={{ x: 900 }}
            locale={{
              emptyText: <Empty description="暂无账单记录" />
            }}
          />
        </Card>

        {/* 充值明细卡片 */}
        <Card
          title={
            <span>
              <PayCircleOutlined style={{ marginRight: 8 }} />
              充值明细
              <Tag color="blue" style={{ marginLeft: 8 }}>Beta测试</Tag>
            </span>
          }
          extra={
            <DatePicker.RangePicker
              size="small"
              defaultValue={[dayjs('2024-01-01'), dayjs()]}
              onChange={(_, dateStrings) => {
                if (dateStrings[0] && dateStrings[1]) {
                  setPaymentDates([dateStrings[0], dateStrings[1]])
                  fetchPayments(dateStrings[0], dateStrings[1])
                }
              }}
            />
          }
          style={{ marginBottom: 24 }}
        >
          {payments && (
            <Statistic
              title="充值总金额"
              value={payments.total_amount}
              precision={2}
              prefix="¥"
              style={{ marginBottom: 16 }}
            />
          )}
          <Table
            dataSource={payments?.payments || []}
            columns={paymentColumns}
            rowKey={(record) => `${record.pay_time}-${record.amount}`}
            loading={paymentsLoading}
            pagination={false}
            scroll={{ x: 700 }}
            locale={{
              emptyText: <Empty description="暂无充值记录" />
            }}
          />
        </Card>

        {/* 设备管理卡片 */}
        <Card
          title={
            <span>
              <DesktopOutlined style={{ marginRight: 8 }} />
              我的设备 ({devices.length})
            </span>
          }
          extra={
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={fetchDevices}
              loading={devicesLoading}
            >
              刷新
            </Button>
          }
        >
          <Table
            dataSource={devices}
            columns={columns}
            rowKey="mac_address"
            loading={devicesLoading}
            pagination={false}
            scroll={{ x: 750 }}
            locale={{
              emptyText: <Empty description="暂无绑定设备" />
            }}
          />
          <div style={{ marginTop: 16, color: '#999', fontSize: 12 }}>
            提示：在线设备无法解绑，请先断开该设备的网络连接
          </div>
        </Card>
      </Spin>

      <WifiLoginModal
        open={loginModalOpen}
        onClose={() => setLoginModalOpen(false)}
        onSuccess={handleLoginSuccess}
      />
    </AppLayout>
  )
}

import { useEffect, useState } from 'react'
import { Card, Descriptions, Spin, message, Avatar } from 'antd'
import { UserOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import AppLayout from '../components/AppLayout'

export default function UserInfo() {
  const [loading, setLoading] = useState(true)
  const [userInfo, setUserInfo] = useState<any>({})
  const [studentInfo, setStudentInfo] = useState<any>({})

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [userRes, studentRes] = await Promise.all([
        api.get('/grades/user-info'),
        api.get('/grades/student-info')
      ])
      setUserInfo(userRes.data || {})
      setStudentInfo(studentRes.data || {})
    } catch (error) {
      message.error('获取用户信息失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout>
      <Spin spinning={loading}>
        <Card style={{ marginBottom: 24 }}>
          <Card.Meta
            avatar={<Avatar size={64} icon={<UserOutlined />} />}
            title={studentInfo.XM || userInfo.name || '未命名'}
            description={studentInfo.XH || userInfo.username}
          />
        </Card>

        <Card title="基本信息">
          <Descriptions bordered column={2}>
            <Descriptions.Item label="姓名">{studentInfo.XM}</Descriptions.Item>
            <Descriptions.Item label="学号">{studentInfo.XH}</Descriptions.Item>
            <Descriptions.Item label="年级">{studentInfo.NJMC}</Descriptions.Item>
            <Descriptions.Item label="院系">{studentInfo.YXMC}</Descriptions.Item>
            <Descriptions.Item label="专业">{studentInfo.ZYMC}</Descriptions.Item>
            <Descriptions.Item label="班级">{studentInfo.BJMC}</Descriptions.Item>
            <Descriptions.Item label="角色">{userInfo.role?.[0]?.jsmc || '学生'}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Spin>
    </AppLayout>
  )
}
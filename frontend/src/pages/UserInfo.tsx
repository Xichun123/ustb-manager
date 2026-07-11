import { useEffect, useState } from 'react'
import { Avatar, Card, Descriptions, Spin, message } from 'antd'
import { UserOutlined } from '@ant-design/icons'
import AppLayout from '../components/AppLayout'
import { api, getApiErrorMessage } from '../services/api'
import type { components } from '../services/openapi'

type UserProfile = components['schemas']['UserProfile']

export default function UserInfo() {
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<UserProfile | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const { data } = await api.get<UserProfile>('/me')
        setProfile(data)
      } catch (error: unknown) {
        message.error(getApiErrorMessage(error, '获取用户信息失败'))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <AppLayout>
      <Spin spinning={loading}>
        <Card style={{ marginBottom: 24 }}>
          <Card.Meta
            avatar={<Avatar size={64} src={profile?.photo_url} icon={<UserOutlined />} />}
            title={profile?.name || '未命名'}
            description={profile?.student_id}
          />
        </Card>

        <Card title="基本信息">
          <Descriptions bordered column={2}>
            <Descriptions.Item label="姓名">{profile?.name || '-'}</Descriptions.Item>
            <Descriptions.Item label="学号">{profile?.student_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="年级">{profile?.grade || '-'}</Descriptions.Item>
            <Descriptions.Item label="院系">{profile?.college || '-'}</Descriptions.Item>
            <Descriptions.Item label="专业">{profile?.major || '-'}</Descriptions.Item>
            <Descriptions.Item label="班级">{profile?.class_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{profile?.email || '-'}</Descriptions.Item>
            <Descriptions.Item label="角色">
              {profile?.roles?.map(role => role.name).join('、') || '学生'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </Spin>
    </AppLayout>
  )
}

import { get } from '../../services/api'
import type { components } from '../../services/openapi'

const app = getApp<IAppOption>()
type Notice = components['schemas']['NoticeRecord']
type NoticePage = components['schemas']['NoticePage']

Page({
  data: {
    loading: true,
    notices: [] as Notice[],
  },

  onLoad() {
    this.loadNotices()
  },

  async loadNotices() {
    if (!app.globalData.isAuthenticated) {
      wx.redirectTo({ url: '/pages/login/login' })
      return
    }
    try {
      this.setData({ loading: true })
      const page = await get<NoticePage>('/api/notices', { page: 1, page_size: 100 })
      this.setData({ notices: page.items || [] })
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : '通知加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  openNotice(event: WechatMiniprogram.TouchEvent) {
    const index = Number(event.currentTarget.dataset.index)
    const notice = this.data.notices[index]
    if (!notice) return
    wx.showModal({
      title: notice.title,
      content: [notice.sender, notice.sent_at, notice.content].filter(Boolean).join('\n\n'),
      showCancel: false,
    })
  },
})

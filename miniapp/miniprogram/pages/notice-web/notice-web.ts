Page({
  data: {
    url: '',
  },

  onLoad(options: Record<string, string | undefined>) {
    const url = decodeURIComponent(options.url || '')
    if (!/^https?:\/\//i.test(url)) {
      wx.showToast({ title: '通知链接无效', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    this.setData({ url })
  },
})

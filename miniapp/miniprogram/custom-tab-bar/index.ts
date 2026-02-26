Component({
  data: {
    selected: 0,
    list: [
      { pagePath: '/pages/index/index', text: '首页', icon: '🏠' },
      { pagePath: '/pages/schedule/schedule', text: '课表', icon: '📅' },
      { pagePath: '/pages/grades/grades', text: '成绩', icon: '📊' },
      { pagePath: '/pages/wifi/wifi', text: '📶', icon: '📶' },
      { pagePath: '/pages/me/me', text: '我的', icon: '👤' },
    ],
  },

  methods: {
    switchTab(e: any) {
      const idx = e.currentTarget.dataset.index
      const item = this.data.list[idx]
      wx.switchTab({ url: item.pagePath })
    },
  },
})

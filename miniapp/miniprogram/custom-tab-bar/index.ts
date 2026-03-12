Component({
  data: {
    selected: 0,
    list: [
      {
        pagePath: '/pages/index/index',
        text: '首页',
        iconPath: '/assets/tabbar/home-default.png',
        selectedIconPath: '/assets/tabbar/home-active.png',
      },
      {
        pagePath: '/pages/schedule/schedule',
        text: '课表',
        iconPath: '/assets/tabbar/schedule-default.png',
        selectedIconPath: '/assets/tabbar/schedule-active.png',
      },
      {
        pagePath: '/pages/grades/grades',
        text: '成绩',
        iconPath: '/assets/tabbar/grades-default.png',
        selectedIconPath: '/assets/tabbar/grades-active.png',
      },
      {
        pagePath: '/pages/wifi/wifi',
        text: '校园网',
        iconPath: '/assets/tabbar/wifi-default.png',
        selectedIconPath: '/assets/tabbar/wifi-active.png',
      },
      {
        pagePath: '/pages/me/me',
        text: '我的',
        iconPath: '/assets/tabbar/me-default.png',
        selectedIconPath: '/assets/tabbar/me-active.png',
      },
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

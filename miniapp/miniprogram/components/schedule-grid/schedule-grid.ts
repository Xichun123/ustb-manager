Component({
  properties: {
    schedule: { type: Array, value: [] },
    dates: { type: Object, value: {} },
    compact: { type: Boolean, value: false },
  },

  data: {
    grid: [] as any[][],
    weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    periods: ['1-2节', '3-4节', '5-6节', '7-8节', '9-10节', '11-12节'],
    colorMap: {} as Record<string, { bg: string; text: string }>,
  },

  observers: {
    schedule(val: any[]) {
      this.buildGrid(val)
    },
  },

  methods: {
    buildGrid(schedule: any[]) {
      const colors = [
        '#e6f7ff', '#f6ffed', '#fff7e6', '#fff2f0', '#f9f0ff',
        '#e6fffb', '#fcffe6', '#fff0f6', '#feffe6', '#e8f5e9',
      ]
      const textColors = [
        '#1890ff', '#52c41a', '#fa8c16', '#ff4d4f', '#722ed1',
        '#13c2c2', '#a0d911', '#eb2f96', '#fadb14', '#389e0d',
      ]

      // Build color map
      const colorMap: Record<string, { bg: string; text: string }> = {}
      let colorIdx = 0
      schedule.forEach((item: any) => {
        if (!colorMap[item.course_name]) {
          colorMap[item.course_name] = {
            bg: colors[colorIdx % colors.length],
            text: textColors[colorIdx % textColors.length],
          }
          colorIdx++
        }
      })

      // Build 6×7 grid
      const grid: any[][] = Array.from({ length: 6 }, () => Array.from({ length: 7 }, () => null))
      schedule.forEach((item: any) => {
        const periodIdx = Math.floor((item.start_period - 1) / 2)
        const dayIdx = item.weekday - 1
        if (periodIdx >= 0 && periodIdx < 6 && dayIdx >= 0 && dayIdx < 7) {
          grid[periodIdx][dayIdx] = {
            ...item,
            color: colorMap[item.course_name],
          }
        }
      })

      this.setData({ grid, colorMap })
    },

    onCourseClick(e: any) {
      const { period, day } = e.currentTarget.dataset
      const row = this.data.grid[period]
      const course = row ? row[day] : null
      if (course) {
        this.triggerEvent('courseclick', { course })
      }
    },
  },
})

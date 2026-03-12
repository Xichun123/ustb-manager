const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

Component({
  properties: {
    schedule: { type: Array, value: [] },
    dates: { type: Object, value: {} },
    compact: { type: Boolean, value: false },
    hideWeekend: { type: Boolean, value: false },
  },

  data: {
    grid: [] as any[][][],
    rawDates: {} as Record<string, string>,
    headerColumns: [] as Array<{ label: string; date: string; dayIdx: number }>,
    periods: ['I', 'II', 'III', 'IV', 'V', 'VI'],
    colorMap: {} as Record<string, { bg: string; text: string }>,
  },

  observers: {
    schedule(val: any[]) {
      this.buildGrid(val)
    },
    dates(val: Record<string, string>) {
      this.buildDisplayDates(val)
    },
    hideWeekend() {
      this.buildGrid(this.data.schedule as any[])
      this.buildDisplayDates(this.data.rawDates as Record<string, string>)
    },
  },

  methods: {
    getVisibleDayIndexes() {
      return this.data.hideWeekend ? [0, 1, 2, 3, 4] : [0, 1, 2, 3, 4, 5, 6]
    },

    formatDate(dateText: string) {
      const text = String(dateText || '').trim()
      const match = text.match(/(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/)
      if (!match) {
        return text
      }
      const month = match[2].padStart(2, '0')
      const day = match[3].padStart(2, '0')
      return `${month}-${day}`
    },

    buildHeaderColumns(formattedDates: Record<string, string>) {
      const visibleDayIndexes = this.getVisibleDayIndexes()
      return visibleDayIndexes.map((dayIdx) => ({
        label: WEEKDAYS[dayIdx],
        date: formattedDates[String(dayIdx + 1)] || '',
        dayIdx,
      }))
    },

    buildDisplayDates(dates: Record<string, string>) {
      const formattedDates: Record<string, string> = {}
      Object.keys(dates || {}).forEach((key) => {
        formattedDates[key] = this.formatDate(dates[key])
      })
      this.setData({
        rawDates: formattedDates,
        headerColumns: this.buildHeaderColumns(formattedDates),
      })
    },

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

      // Build 6×7 grid first, then slice visible weekdays.
      const fullGrid: any[][][] = Array.from({ length: 6 }, () => Array.from({ length: 7 }, () => []))
      schedule.forEach((item: any) => {
        const periodIdx = Math.floor((item.start_period - 1) / 2)
        const dayIdx = item.weekday - 1
        if (periodIdx >= 0 && periodIdx < 6 && dayIdx >= 0 && dayIdx < 7) {
          fullGrid[periodIdx][dayIdx].push({
            ...item,
            location_short: String(item.location || '')
              .replace(/【[^】]+】/g, '')
              .replace(/\s+/g, ' ')
              .trim(),
            color: colorMap[item.course_name],
          })
        }
      })

      const visibleDayIndexes = this.getVisibleDayIndexes()
      const grid = fullGrid.map((row) => visibleDayIndexes.map((dayIdx) => row[dayIdx]))

      this.setData({ grid, colorMap })
    },

    onCourseClick(e: any) {
      const { period, day, course } = e.currentTarget.dataset
      if (day < 0 || course < 0) return
      const row = this.data.grid[period]
      const courseList = row ? row[day] : null
      const selectedCourse = courseList ? courseList[course] : null
      if (selectedCourse) {
        this.triggerEvent('courseclick', { course: selectedCourse })
      }
    },
  },
})

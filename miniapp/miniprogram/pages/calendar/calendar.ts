import { get } from '../../services/api'
import type { components } from '../../services/openapi'

type AcademicContext = components['schemas']['AcademicContextResponse']
type AcademicCalendar = components['schemas']['AcademicCalendar']
interface CalendarWeek { key: string; label: string; dates: string[] }

Page({
  data: {
    loading: true,
    term: '',
    month: new Date().getMonth() + 1,
    months: Array.from({ length: 12 }, (_, index) => `${index + 1}月`),
    weeks: [] as CalendarWeek[],
  },

  onLoad() {
    this.init()
  },

  async init() {
    try {
      const context = await get<AcademicContext>('/api/academic/context')
      this.setData({ term: context.teaching_term.code })
      await this.loadMonth()
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : '校历加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  async loadMonth() {
    try {
      this.setData({ loading: true })
      const calendar = await get<AcademicCalendar>('/api/academic/calendar', {
        term: this.data.term,
        month: this.data.month,
      })
      const groups = new Map<number | null, string[]>()
      for (const item of calendar.dates || []) {
        const week = item.week === undefined || item.week === null ? null : item.week
        groups.set(week, [...(groups.get(week) || []), item.date])
      }
      const weeks = Array.from(groups.entries()).map(([week, dates]): CalendarWeek => ({
        key: `${week}-${dates[0] || ''}`,
        label: week ? `第 ${week} 教学周` : '非教学周',
        dates,
      }))
      this.setData({ weeks })
    } catch (error) {
      wx.showToast({ title: error instanceof Error ? error.message : '校历加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onMonthChange(event: WechatMiniprogram.PickerChange) {
    const month = Number(event.detail.value) + 1
    this.setData({ month }, () => this.loadMonth())
  },
})

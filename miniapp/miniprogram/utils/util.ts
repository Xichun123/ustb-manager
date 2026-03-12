export const formatTime = (date: Date) => {
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hour = date.getHours()
  const minute = date.getMinutes()
  const second = date.getSeconds()

  return (
    [year, month, day].map(formatNumber).join('/') +
    ' ' +
    [hour, minute, second].map(formatNumber).join(':')
  )
}

const formatNumber = (n: number) => {
  const s = n.toString()
  return s[1] ? s : '0' + s
}

/** Format flow in MB/GB */
export const formatFlow = (mb: number): string => {
  if (mb >= 1024) {
    return (mb / 1024).toFixed(2) + ' GB'
  }
  return mb.toFixed(2) + ' MB'
}

/** Format duration in minutes to hours + minutes */
export const formatDuration = (minutes: number): string => {
  if (minutes >= 60) {
    const h = Math.floor(minutes / 60)
    const m = minutes % 60
    return m > 0 ? `${h}小时${m}分钟` : `${h}小时`
  }
  return `${minutes}分钟`
}

/** Format money */
export const formatMoney = (amount: number): string => {
  return '¥' + amount.toFixed(2)
}

/** Get score color class */
export const getScoreColor = (score: string): string => {
  const num = parseFloat(score)
  if (isNaN(num)) return ''
  if (num >= 90) return 'text-success'
  if (num >= 80) return 'text-primary'
  if (num >= 70) return 'text-warning'
  return 'text-error'
}

/** Period time mapping (1-2节, 3-4节, etc.) */
export const PERIOD_TIMES: Record<number, string> = {
  1: '08:00-09:35',
  2: '10:05-11:40',
  3: '13:30-15:05',
  4: '15:30-17:05',
  5: '18:00-19:35',
  6: '19:50-21:25',
}

export const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

/** Course color palette for schedule */
export const COURSE_COLORS = [
  '#e6f7ff', '#f6ffed', '#fff7e6', '#fff2f0', '#f9f0ff',
  '#e6fffb', '#fcffe6', '#fff0f6', '#feffe6', '#e8f5e9',
]

export const COURSE_TEXT_COLORS = [
  '#1890ff', '#52c41a', '#fa8c16', '#ff4d4f', '#722ed1',
  '#13c2c2', '#a0d911', '#eb2f96', '#fadb14', '#389e0d',
]

export const extractWeekNumbers = (weekList: any[]): number[] => {
  if (!Array.isArray(weekList)) return []

  return weekList
    .map((item) => {
      if (typeof item === 'number') return item
      if (item && typeof item === 'object') {
        const value = item.ZC !== undefined && item.ZC !== null ? item.ZC : item.zc
        const parsed = Number(value)
        return Number.isFinite(parsed) ? parsed : null
      }
      return null
    })
    .filter((week): week is number => week !== null && week > 0 && week !== 99)
}

export const calculateCurrentWeekFromDates = (
  firstWeekDates: Record<string, string> | null | undefined,
  availableWeeks: number[],
): number | null => {
  if (!firstWeekDates || availableWeeks.length === 0) return null

  const firstMonday = firstWeekDates['1'] || firstWeekDates[1 as unknown as keyof typeof firstWeekDates]
  if (!firstMonday) return null

  const firstDate = new Date(String(firstMonday))
  if (Number.isNaN(firstDate.getTime())) return null

  const today = new Date()
  firstDate.setHours(0, 0, 0, 0)
  today.setHours(0, 0, 0, 0)

  const diffDays = Math.floor((today.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24))
  const calculatedWeek = Math.floor(diffDays / 7) + 1
  const minWeek = availableWeeks[0]
  const maxWeek = availableWeeks[availableWeeks.length - 1]

  if (Number.isNaN(calculatedWeek)) return null
  return Math.max(minWeek, Math.min(calculatedWeek, maxWeek))
}

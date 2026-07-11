import type { components } from './openapi'

type CourseItem = components['schemas']['ScheduleCourse']

export function buildScheduleGrid(
  courses: CourseItem[],
  periodCount: number,
  weekdayCount: number,
): CourseItem[][][] {
  const grid = Array.from({ length: periodCount }, () =>
    Array.from({ length: weekdayCount }, () => [] as CourseItem[])
  )

  courses.forEach(course => {
    const startPeriodIdx = Math.floor((course.start_period - 1) / 2)
    const endPeriodIdx = Math.floor((course.end_period - 1) / 2)
    const weekdayIdx = course.weekday - 1

    if (weekdayIdx < 0 || weekdayIdx >= weekdayCount) return

    for (let periodIdx = startPeriodIdx; periodIdx <= endPeriodIdx; periodIdx += 1) {
      if (periodIdx >= 0 && periodIdx < periodCount) {
        grid[periodIdx][weekdayIdx].push(course)
      }
    }
  })

  return grid
}

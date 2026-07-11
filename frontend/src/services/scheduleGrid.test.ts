import { describe, expect, it } from 'vitest'
import type { components } from './openapi'
import { buildScheduleGrid } from './scheduleGrid'

type CourseItem = components['schemas']['ScheduleCourse']

const course: CourseItem = {
  course_id: 'data-science',
  course_code: '36077001',
  course_name: '数据科学前沿',
  course_name_en: 'Advanced Data Science',
  teacher: '李新',
  weekday: 1,
  start_period: 9,
  end_period: 12,
  weeks: [1, 2],
  week_text: '1-2周',
  location: '管理楼512',
  campus: '校本部',
  period_text: '第9-12节',
  task_code: '001',
}

describe('buildScheduleGrid', () => {
  it('places a 9-12 course in both 9-10 and 11-12 rows', () => {
    const grid = buildScheduleGrid([course], 6, 7)

    expect(grid[4][0]).toEqual([course])
    expect(grid[5][0]).toEqual([course])
  })
})

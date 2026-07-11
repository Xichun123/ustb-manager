import { describe, expect, it } from 'vitest'

import { formatAcademicTermLabel } from './academic-terms'

describe('formatAcademicTermLabel', () => {
  it('restores the complete summer term label when the API name is only -3', () => {
    expect(formatAcademicTermLabel({
      year: '2025-2026',
      semester: '3',
      name: '-3',
    })).toBe('2025-2026学年夏季学期')
  })

  it('uses semantic labels for normal semesters', () => {
    expect(formatAcademicTermLabel({ year: '2025-2026', semester: '1', name: '-1' }))
      .toBe('2025-2026学年第一学期')
    expect(formatAcademicTermLabel({ year: '2025-2026', semester: '2', name: '-2' }))
      .toBe('2025-2026学年第二学期')
  })
})

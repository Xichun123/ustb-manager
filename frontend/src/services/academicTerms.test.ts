import { describe, expect, it } from 'vitest'
import type { components } from './openapi'
import { formatAcademicTermLabel } from './academicTerms'

type Term = components['schemas']['AcademicTermOption']

describe('formatAcademicTermLabel', () => {
  it('restores the year and semantic name when BYYT returns only -3', () => {
    const term: Term = {
      year: '2025-2026',
      semester: '3',
      code: '2025-2026-3',
      name: '-3',
      name_en: 'Summer',
      is_current: false,
    }

    expect(formatAcademicTermLabel(term)).toBe('2025-2026学年夏季学期')
  })

  it('uses readable names for the first and second semesters', () => {
    expect(formatAcademicTermLabel({
      year: '2025-2026', semester: '1', code: '2025-2026-1', name: '-1', name_en: 'Autumn', is_current: false,
    })).toBe('2025-2026学年第一学期')
    expect(formatAcademicTermLabel({
      year: '2025-2026', semester: '2', code: '2025-2026-2', name: '-2', name_en: 'Spring', is_current: false,
    })).toBe('2025-2026学年第二学期')
  })
})

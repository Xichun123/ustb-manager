import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  getCoursesPageState,
  setCoursesPageState,
  setUserInfo,
  type CoursesPageState,
} from './storage'

const values = new Map<string, unknown>()

const wxStorage = {
  getStorageSync: vi.fn((key: string) => values.get(key) || ''),
  setStorageSync: vi.fn((key: string, value: unknown) => values.set(key, value)),
  removeStorageSync: vi.fn((key: string) => values.delete(key)),
}

vi.stubGlobal('wx', wxStorage)

const state: CoursesPageState = {
  viewMode: 'selected',
  rawCourses: [],
  displayCourses: [],
  totalCredits: 0,
  totalHours: 0,
  courseCount: 0,
  collegeCount: 0,
  currentXn: '2025-2026',
  currentXq: '2',
  termList: [],
  selectedTermIdx: 0,
  selectedMethodIdx: 0,
  colleges: [],
  selectedCollegeIdx: 0,
  campuses: [],
  selectedCampusIdx: 0,
  categoryOptions: [],
  selectedCategoryIdx: 0,
  searchText: '',
  announcements: [],
  showAnnouncements: false,
  updatedAt: 1,
}

const user = (studentId: string) => ({
  name: '测试用户',
  student_id: studentId,
  dept: '学院',
  major: '专业',
  class_name: '班级',
})

describe('page cache envelopes', () => {
  beforeEach(() => {
    values.clear()
    vi.clearAllMocks()
  })

  it('rejects a legacy cache without a schema version', () => {
    values.set('courses_page_state', state)

    expect(getCoursesPageState()).toBeNull()
    expect(values.has('courses_page_state')).toBe(false)
  })

  it('rejects cache data from another user', () => {
    setUserInfo(user('student-a'))
    setCoursesPageState(state)
    setUserInfo(user('student-b'))

    expect(getCoursesPageState()).toBeNull()
  })

  it('restores current-schema cache for the same user', () => {
    setUserInfo(user('student-a'))
    setCoursesPageState(state)

    expect(getCoursesPageState()).toEqual(state)
  })
})

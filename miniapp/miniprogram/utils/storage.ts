import type { components } from '../services/openapi'

const CACHE_SCHEMA_VERSION = 2

type ScheduleCourse = components['schemas']['ScheduleCourse']
type CachedScheduleCourse = Omit<ScheduleCourse, 'weeks'> & { weeks: string }
type GradeRecord = components['schemas']['GradeRecord'] & { scoreColor: string }
type UserProfile = components['schemas']['UserProfile']
type ExamRecord = components['schemas']['ExamRecord'] & { isPast: boolean; isToday: boolean }
type ProgressSummary = components['schemas']['AcademicProgress']
type ProgressModule = components['schemas']['AcademicProgressModule']
type CourseRecord = components['schemas']['CourseSelectionRecord']
type CourseAnnouncement = components['schemas']['CourseAnnouncement']

interface CachedCreditCategory {
  code: string
  name: string
  required: number
  completed: number
  remaining: number
  percentage: number
}

interface ScheduleCacheEntry {
  schedule: CachedScheduleCourse[]
  dates: Record<string, string>
  cachedAt: number
}

const STORAGE_KEYS = {
  SESSION_ID: 'ustb_session_id',
  USER_INFO: 'ustb_user_info',
  WIFI_STUDENT_ID: 'wifi_student_id',
  SCHEDULE_HIDE_WEEKEND: 'schedule_hide_weekend',
  DASHBOARD_PAGE_STATE: 'dashboard_page_state',
  SCHEDULE_PAGE_STATE: 'schedule_page_state',
  GRADES_PAGE_STATE: 'grades_page_state',
  ME_PAGE_STATE: 'me_page_state',
  EXAMS_PAGE_STATE: 'exams_page_state',
  PROGRESS_PAGE_STATE: 'progress_page_state',
  COURSES_PAGE_STATE: 'courses_page_state',
  WIFI_PAGE_STATE: 'wifi_page_state',
}

function getStoredData<T>(key: string): T | null {
  const data = wx.getStorageSync(key)
  return data || null
}

function setStoredData<T>(key: string, value: T): void {
  wx.setStorageSync(key, value)
}

function removeStoredData(key: string): void {
  wx.removeStorageSync(key)
}

interface PageCacheEnvelope<T> {
  schemaVersion: number
  owner: string
  value: T
}

function cacheOwner(): string {
  const user = getStoredData<UserInfo>(STORAGE_KEYS.USER_INFO)
  return user?.student_id || getWifiStudentId() || 'anonymous'
}

function getPageCache<T>(key: string): T | null {
  const envelope = getStoredData<PageCacheEnvelope<T>>(key)
  if (
    !envelope
    || envelope.schemaVersion !== CACHE_SCHEMA_VERSION
    || envelope.owner !== cacheOwner()
  ) {
    removeStoredData(key)
    return null
  }
  return envelope.value
}

function setPageCache<T>(key: string, value: T): void {
  setStoredData<PageCacheEnvelope<T>>(key, {
    schemaVersion: CACHE_SCHEMA_VERSION,
    owner: cacheOwner(),
    value,
  })
}

export function getSessionId(): string {
  return wx.getStorageSync(STORAGE_KEYS.SESSION_ID) || ''
}

export function hasSessionId(): boolean {
  return !!getSessionId()
}

export function setSessionId(sid: string): void {
  wx.setStorageSync(STORAGE_KEYS.SESSION_ID, sid)
}

export function removeSessionId(): void {
  wx.removeStorageSync(STORAGE_KEYS.SESSION_ID)
}

export interface UserInfo {
  name: string
  student_id: string
  dept: string
  major: string
  class_name: string
}

export interface SchedulePageState {
  viewMode: 'week' | 'term'
  selectedTermCode: string
  selectedWeek: number
  currentWeek: number
  currentXn: string
  currentXq: string
  currentTermCode: string
  termList: Array<{ code: string; name: string }>
  weekList: number[]
  schedule: CachedScheduleCourse[]
  dates: Record<string, string>
  scheduleCaches: Record<'week' | 'term', Record<string, ScheduleCacheEntry>>
  updatedAt: number
}

export interface DashboardPageState {
  studentInfo: UserInfo | null
  schedule: CachedScheduleCourse[]
  scheduleDates: Record<string, string>
  currentWeek: number
  wifiStatus: any
  wifiFlow: any
  wifiFlowDisplay: string
  wifiBalanceDisplay: string
  updatedAt: number
}

export interface GradesPageState {
  grades: GradeRecord[]
  gpaStats: {
    gpa: number
    total_credits: number
    passed_credits: number
    failed_count: number
  }
  updatedAt: number
}

export interface MePageState {
  userInfo: UserProfile | null
  studentInfo: UserInfo | null
  updatedAt: number
}

export interface ExamsPageState {
  exams: ExamRecord[]
  updatedAt: number
}

export interface ProgressPageState {
  activeTab: 'credits' | 'required' | 'plan'
  creditCategories: CachedCreditCategory[]
  requiredStats: ProgressSummary | null
  planData: ProgressModule[]
  tabUpdatedAt: {
    credits: number
    required: number
    plan: number
  }
  updatedAt: number
}

export interface CoursesPageState {
  viewMode: 'selected' | 'available'
  rawCourses: CourseRecord[]
  displayCourses: CourseRecord[]
  totalCredits: number
  totalHours: number
  courseCount: number
  collegeCount: number
  currentXn: string
  currentXq: string
  termList: Array<{ value: string; label: string }>
  selectedTermIdx: number
  selectedMethodIdx: number
  colleges: Array<{ value: string; label: string }>
  selectedCollegeIdx: number
  campuses: Array<{ value: string; label: string }>
  selectedCampusIdx: number
  categoryOptions: Array<{ value: string; label: string }>
  selectedCategoryIdx: number
  searchText: string
  announcements: CourseAnnouncement[]
  showAnnouncements: boolean
  updatedAt: number
}

export interface WifiPageState {
  loggedIn: boolean
  loginMode: string
  wifiStudentId: string
  flow: any
  flowDisplay: any
  onlineDevices: any[]
  devices: any[]
  payments: any[]
  activeSection: string
  updatedAt: number
}

export function getUserInfo(): UserInfo | null {
  return getStoredData<UserInfo>(STORAGE_KEYS.USER_INFO)
}

export function setUserInfo(info: UserInfo): void {
  setStoredData(STORAGE_KEYS.USER_INFO, info)
}

export function removeUserInfo(): void {
  removeStoredData(STORAGE_KEYS.USER_INFO)
}

export function getWifiStudentId(): string {
  return wx.getStorageSync(STORAGE_KEYS.WIFI_STUDENT_ID) || ''
}

export function setWifiStudentId(id: string): void {
  setStoredData(STORAGE_KEYS.WIFI_STUDENT_ID, id)
}

export function removeWifiStudentId(): void {
  removeStoredData(STORAGE_KEYS.WIFI_STUDENT_ID)
}

export function getScheduleHideWeekend(): boolean {
  return !!wx.getStorageSync(STORAGE_KEYS.SCHEDULE_HIDE_WEEKEND)
}

export function setScheduleHideWeekend(value: boolean): void {
  setStoredData(STORAGE_KEYS.SCHEDULE_HIDE_WEEKEND, !!value)
}

export function getDashboardPageState(): DashboardPageState | null {
  return getPageCache<DashboardPageState>(STORAGE_KEYS.DASHBOARD_PAGE_STATE)
}

export function setDashboardPageState(state: DashboardPageState): void {
  setPageCache(STORAGE_KEYS.DASHBOARD_PAGE_STATE, state)
}

export function removeDashboardPageState(): void {
  removeStoredData(STORAGE_KEYS.DASHBOARD_PAGE_STATE)
}

export function getSchedulePageState(): SchedulePageState | null {
  return getPageCache<SchedulePageState>(STORAGE_KEYS.SCHEDULE_PAGE_STATE)
}

export function setSchedulePageState(state: SchedulePageState): void {
  setPageCache(STORAGE_KEYS.SCHEDULE_PAGE_STATE, state)
}

export function removeSchedulePageState(): void {
  removeStoredData(STORAGE_KEYS.SCHEDULE_PAGE_STATE)
}

export function getGradesPageState(): GradesPageState | null {
  return getPageCache<GradesPageState>(STORAGE_KEYS.GRADES_PAGE_STATE)
}

export function setGradesPageState(state: GradesPageState): void {
  setPageCache(STORAGE_KEYS.GRADES_PAGE_STATE, state)
}

export function removeGradesPageState(): void {
  removeStoredData(STORAGE_KEYS.GRADES_PAGE_STATE)
}

export function getMePageState(): MePageState | null {
  return getPageCache<MePageState>(STORAGE_KEYS.ME_PAGE_STATE)
}

export function setMePageState(state: MePageState): void {
  setPageCache(STORAGE_KEYS.ME_PAGE_STATE, state)
}

export function removeMePageState(): void {
  removeStoredData(STORAGE_KEYS.ME_PAGE_STATE)
}

export function getExamsPageState(): ExamsPageState | null {
  return getPageCache<ExamsPageState>(STORAGE_KEYS.EXAMS_PAGE_STATE)
}

export function setExamsPageState(state: ExamsPageState): void {
  setPageCache(STORAGE_KEYS.EXAMS_PAGE_STATE, state)
}

export function removeExamsPageState(): void {
  removeStoredData(STORAGE_KEYS.EXAMS_PAGE_STATE)
}

export function getProgressPageState(): ProgressPageState | null {
  return getPageCache<ProgressPageState>(STORAGE_KEYS.PROGRESS_PAGE_STATE)
}

export function setProgressPageState(state: ProgressPageState): void {
  setPageCache(STORAGE_KEYS.PROGRESS_PAGE_STATE, state)
}

export function removeProgressPageState(): void {
  removeStoredData(STORAGE_KEYS.PROGRESS_PAGE_STATE)
}

export function getCoursesPageState(): CoursesPageState | null {
  return getPageCache<CoursesPageState>(STORAGE_KEYS.COURSES_PAGE_STATE)
}

export function setCoursesPageState(state: CoursesPageState): void {
  setPageCache(STORAGE_KEYS.COURSES_PAGE_STATE, state)
}

export function removeCoursesPageState(): void {
  removeStoredData(STORAGE_KEYS.COURSES_PAGE_STATE)
}

export function getWifiPageState(): WifiPageState | null {
  return getPageCache<WifiPageState>(STORAGE_KEYS.WIFI_PAGE_STATE)
}

export function setWifiPageState(state: WifiPageState): void {
  setPageCache(STORAGE_KEYS.WIFI_PAGE_STATE, state)
}

export function removeWifiPageState(): void {
  removeStoredData(STORAGE_KEYS.WIFI_PAGE_STATE)
}

export function clearAll(): void {
  removeStoredData(STORAGE_KEYS.SESSION_ID)
  removeStoredData(STORAGE_KEYS.USER_INFO)
  removeStoredData(STORAGE_KEYS.WIFI_STUDENT_ID)
  removeStoredData(STORAGE_KEYS.DASHBOARD_PAGE_STATE)
  removeStoredData(STORAGE_KEYS.SCHEDULE_PAGE_STATE)
  removeStoredData(STORAGE_KEYS.GRADES_PAGE_STATE)
  removeStoredData(STORAGE_KEYS.ME_PAGE_STATE)
  removeStoredData(STORAGE_KEYS.EXAMS_PAGE_STATE)
  removeStoredData(STORAGE_KEYS.PROGRESS_PAGE_STATE)
  removeStoredData(STORAGE_KEYS.COURSES_PAGE_STATE)
  removeStoredData(STORAGE_KEYS.WIFI_PAGE_STATE)
}

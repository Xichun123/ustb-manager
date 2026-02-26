const STORAGE_KEYS = {
  SESSION_ID: 'ustb_session_id',
  USER_INFO: 'ustb_user_info',
  WIFI_STUDENT_ID: 'wifi_student_id',
}

export function getSessionId(): string {
  return wx.getStorageSync(STORAGE_KEYS.SESSION_ID) || ''
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

export function getUserInfo(): UserInfo | null {
  const data = wx.getStorageSync(STORAGE_KEYS.USER_INFO)
  return data || null
}

export function setUserInfo(info: UserInfo): void {
  wx.setStorageSync(STORAGE_KEYS.USER_INFO, info)
}

export function removeUserInfo(): void {
  wx.removeStorageSync(STORAGE_KEYS.USER_INFO)
}

export function getWifiStudentId(): string {
  return wx.getStorageSync(STORAGE_KEYS.WIFI_STUDENT_ID) || ''
}

export function setWifiStudentId(id: string): void {
  wx.setStorageSync(STORAGE_KEYS.WIFI_STUDENT_ID, id)
}

export function clearAll(): void {
  wx.removeStorageSync(STORAGE_KEYS.SESSION_ID)
  wx.removeStorageSync(STORAGE_KEYS.USER_INFO)
  wx.removeStorageSync(STORAGE_KEYS.WIFI_STUDENT_ID)
}

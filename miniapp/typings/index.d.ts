/// <reference path="./types/index.d.ts" />

interface IAppOption {
  globalData: {
    isAuthenticated: boolean
    userInfo: {
      name: string
      student_id: string
      dept: string
      major: string
      class_name: string
    } | null
    baseUrl: string
  }
}

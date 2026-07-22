import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider, useTheme } from './contexts/ThemeContext'
import { lightTheme, darkTheme } from './theme'
import { ProtectedRoute } from './components/ProtectedRoute'
import { WifiRoute } from './components/WifiRoute'
import { LoginPage } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import Grades from './pages/Grades'
import UserInfo from './pages/UserInfo'
import ProgressPage from './pages/Progress'
import SchedulePage from './pages/Schedule'
import ExamsPage from './pages/Exams'
import WifiPage from './pages/Wifi'
import WifiStandalonePage from './pages/WifiStandalone'
import CoursesPage from './pages/Courses'
import CalendarPage from './pages/Calendar'
import NoticesPage from './pages/Notices'
import './theme/global.css'

function ThemedApp() {
  const { resolvedTheme } = useTheme()

  return (
    <ConfigProvider locale={zhCN} theme={resolvedTheme === 'dark' ? darkTheme : lightTheme}>
      <ErrorBoundary>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/wifi-standalone" element={<WifiStandalonePage />} />
                <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/schedule" element={<ProtectedRoute><SchedulePage /></ProtectedRoute>} />
                <Route path="/grades" element={<ProtectedRoute><Grades /></ProtectedRoute>} />
                <Route path="/user-info" element={<ProtectedRoute><UserInfo /></ProtectedRoute>} />
                <Route path="/progress" element={<ProtectedRoute><ProgressPage /></ProtectedRoute>} />
                <Route path="/exams" element={<ProtectedRoute><ExamsPage /></ProtectedRoute>} />
                <Route path="/courses" element={<ProtectedRoute><CoursesPage /></ProtectedRoute>} />
                <Route path="/calendar" element={<ProtectedRoute><CalendarPage /></ProtectedRoute>} />
                <Route path="/notices" element={<ProtectedRoute><NoticesPage /></ProtectedRoute>} />
                <Route path="/wifi" element={<WifiRoute><WifiPage /></WifiRoute>} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </ConfigProvider>
  )
}

export function App() {
  return (
    <ThemeProvider>
      <ThemedApp />
    </ThemeProvider>
  )
}

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { api, AUTH_REQUIRED_EVENT } from '../services/api'

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  checkAuth: () => Promise<boolean>
  setAuthenticated: (value: boolean) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const checkAuth = useCallback(async (): Promise<boolean> => {
    try {
      const { data } = await api.get('/auth/status')
      setIsAuthenticated(data.authenticated)
      return data.authenticated
    } catch {
      setIsAuthenticated(false)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  const setAuthenticated = useCallback((value: boolean) => {
    setIsAuthenticated(value)
    setIsLoading(false)
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  useEffect(() => {
    const handleAuthRequired = () => setAuthenticated(false)
    window.addEventListener(AUTH_REQUIRED_EVENT, handleAuthRequired)
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, handleAuthRequired)
  }, [setAuthenticated])

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, checkAuth, setAuthenticated }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

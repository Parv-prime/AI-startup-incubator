import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import * as authApi from "../api/auth"
import { clearAuthToken, getAuthToken, setAuthToken } from "../api/client"

interface AuthState {
  user: authApi.User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<authApi.User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getAuthToken()) {
      setLoading(false)
      return
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => clearAuthToken())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    setAuthToken(res.access_token)
    setUser(res.user)
  }, [])

  const signup = useCallback(async (name: string, email: string, password: string) => {
    const res = await authApi.signup(name, email, password)
    setAuthToken(res.access_token)
    setUser(res.user)
  }, [])

  const logout = useCallback(() => {
    authApi.logout().catch(() => {})
    clearAuthToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, signup, logout }),
    [user, loading, login, signup, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

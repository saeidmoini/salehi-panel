import React, { createContext, useContext, useEffect, useState } from 'react'
import client from '../api/client'

interface AdminUser {
  id: number
  username: string
  is_active: boolean
}

interface AuthContextValue {
  user: AdminUser | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AdminUser | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [loading, setLoading] = useState<boolean>(!!token)

  useEffect(() => {
    const fetchMe = async () => {
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const { data } = await client.get<AdminUser>('/api/auth/me')
        setUser(data)
      } catch (e) {
        logout()
      } finally {
        setLoading(false)
      }
    }
    fetchMe()
  }, [token])

  const login = async (username: string, password: string) => {
    const { data } = await client.post<{ access_token: string }>('/api/auth/login', { username, password })
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
    const me = await client.get<AdminUser>('/api/auth/me')
    setUser(me.data)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

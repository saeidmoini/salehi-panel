import React, { createContext, useContext, useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from './useAuth'
import client from '../api/client'

interface Company {
  id: number
  name: string
  display_name: string
  is_active: boolean
  settings?: Record<string, any>
  created_at?: string
  updated_at?: string
}

interface CompanyContextValue {
  company: Company | null
  loading: boolean
}

const CompanyContext = createContext<CompanyContextValue | null>(null)

export const CompanyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { companySlug } = useParams<{ companySlug: string }>()
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadCompany = async () => {
      if (authLoading) return

      if (!companySlug) {
        setLoading(false)
        return
      }

      if (!user) {
        navigate('/login')
        return
      }

      // Verify user has access to this company
      if (!user.is_superuser && user.company_name !== companySlug) {
        console.error('User does not have access to this company')
        navigate('/login')
        return
      }

      try {
        const { data } = await client.get<Company>(`/api/companies/${companySlug}`)
        setCompany(data)
      } catch (error) {
        console.error('Failed to load company', error)
        navigate('/login')
      } finally {
        setLoading(false)
      }
    }

    loadCompany()
  }, [companySlug, user, authLoading, navigate])

  return (
    <CompanyContext.Provider value={{ company, loading }}>
      {!loading && children}
    </CompanyContext.Provider>
  )
}

export const useCompany = () => {
  const context = useContext(CompanyContext)
  if (!context) {
    throw new Error('useCompany must be used within CompanyProvider')
  }
  return context
}

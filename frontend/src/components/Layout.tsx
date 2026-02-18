import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useCompany } from '../hooks/useCompany'
import { useState, useEffect } from 'react'
import client from '../api/client'

interface CompanyOption {
  name: string
  display_name: string
  is_active: boolean
}

interface NavItem {
  path: string
  label: string
  roles: Array<'ADMIN' | 'AGENT'>
  superuserOnly?: boolean
}

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [companies, setCompanies] = useState<CompanyOption[]>([])

  // Company context might be null for admin routes like /admin/companies
  let company = null
  try {
    const ctx = useCompany()
    company = ctx?.company
  } catch (e) {
    // Not in a company-scoped route
  }

  useEffect(() => {
    if (user?.is_superuser) {
      client.get<CompanyOption[]>('/api/companies/').then(({ data }) => {
        setCompanies(data.filter((c) => c.is_active))
      }).catch(() => {})
    }
  }, [user?.is_superuser])

  // Build nav items dynamically based on company context
  const companyNavItems: NavItem[] = company ? [
    ...(user?.is_superuser ? [{ path: '/admin/companies', label: 'مدیریت شرکت‌ها', roles: ['ADMIN'] as Array<'ADMIN' | 'AGENT'>, superuserOnly: true }] : []),
    { path: `/${company.name}/dashboard`, label: 'داشبورد', roles: ['ADMIN'] },
    { path: `/${company.name}/numbers`, label: 'مدیریت شماره‌ها', roles: ['ADMIN', 'AGENT'] },
    { path: `/${company.name}/schedule`, label: 'زمان‌بندی تماس', roles: ['ADMIN'] },
    { path: `/${company.name}/billing`, label: 'تنظیمات مالی', roles: ['ADMIN'], superuserOnly: true },
    { path: `/${company.name}/admins`, label: 'مدیریت کاربران', roles: ['ADMIN'] },
    { path: `/${company.name}/scenarios`, label: 'سناریوها', roles: ['ADMIN'] },
    { path: `/${company.name}/outbound-lines`, label: 'خطوط خروجی', roles: ['ADMIN'], superuserOnly: true },
    { path: `/${company.name}/profile`, label: 'حساب کاربری', roles: ['ADMIN', 'AGENT'] },
  ] : []

  const navItems: NavItem[] = company
    ? companyNavItems
    : (user?.is_superuser ? [{ path: '/admin/companies', label: 'مدیریت شرکت‌ها', roles: ['ADMIN'], superuserOnly: true }] : [])

  const availableNav = navItems.filter((item) => {
    if (item.superuserOnly && !user?.is_superuser) return false
    return !item.roles || item.roles.includes(user?.role || 'ADMIN')
  })

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const switchCompany = (nextCompanyName: string) => {
    if (!company || nextCompanyName === company.name) return
    const currentPath = location.pathname.replace(`/${company.name}`, `/${nextCompanyName}`)
    navigate(currentPath)
  }

  return (
    <div className="min-h-screen flex flex-row-reverse bg-slate-50 text-slate-900" dir="rtl">
      <aside
        className={`w-64 bg-white border-l border-slate-200 p-4 ${
          menuOpen ? 'block' : 'hidden'
        } md:block fixed md:static inset-y-0 right-0 z-30`}
      >
        <div className="flex items-center justify-between mb-6">
          <div className="text-lg font-semibold text-right">پنل تماس</div>
          <button className="md:hidden text-sm text-slate-600" onClick={() => setMenuOpen(false)}>
            بستن
          </button>
        </div>
        <nav className="space-y-2">
          {availableNav.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm font-medium hover:bg-slate-100 text-right ${
                  isActive ? 'bg-slate-200' : ''
                }`
              }
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      {menuOpen && <div className="fixed inset-0 bg-black/40 z-20 md:hidden" onClick={() => setMenuOpen(false)}></div>}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between bg-white border-b border-slate-200 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden rounded border border-slate-200 px-3 py-1 text-sm"
              onClick={() => setMenuOpen(true)}
            >
              منو
            </button>
            <div className="font-semibold">
              {company ? company.display_name : 'پنل مدیریت'}
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm min-w-0">
            <div>{user?.username}</div>
            {/* Company switcher for super admin */}
            {user?.is_superuser && company && (
              <div className="flex items-center gap-2">
                {companies.length > 1 && (
                  <>
                    <select
                      className="md:hidden rounded border border-slate-300 bg-white px-2 py-1 text-xs max-w-[140px]"
                      value={company.name}
                      onChange={(e) => switchCompany(e.target.value)}
                    >
                      {companies.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.display_name}
                        </option>
                      ))}
                    </select>
                    <div className="hidden md:flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
                      {companies.map((c) => (
                        <button
                          key={c.name}
                          className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                            c.name === company.name
                              ? 'bg-white text-slate-900 shadow-sm'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                          onClick={() => switchCompany(c.name)}
                        >
                          {c.display_name}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
            <button onClick={handleLogout} className="rounded bg-slate-900 text-white px-3 py-1 text-xs">
              خروج
            </button>
          </div>
        </header>
        <main className="p-4 md:p-6 flex-1">{children}</main>
      </div>
    </div>
  )
}

export default Layout

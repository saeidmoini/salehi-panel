import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const navItems = [
  { to: '/', label: 'داشبورد' },
  { to: '/numbers', label: 'مدیریت شماره‌ها' },
  { to: '/schedule', label: 'زمان‌بندی تماس' },
  { to: '/admins', label: 'مدیریت مدیران' },
]

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-row-reverse bg-slate-50 text-slate-900" dir="rtl">
      <aside className="w-64 bg-white border-l border-slate-200 p-4 hidden md:block">
        <div className="text-lg font-semibold mb-6 text-right">پنل تماس</div>
        <nav className="space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm font-medium hover:bg-slate-100 text-right ${
                  isActive ? 'bg-slate-200' : ''
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="flex items-center justify-between bg-white border-b border-slate-200 px-4 py-3">
          <div className="font-semibold">به پنل مدیریت خوش آمدید</div>
          <div className="flex items-center gap-3 text-sm">
            <div>{user?.username}</div>
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

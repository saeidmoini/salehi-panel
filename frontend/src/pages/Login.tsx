import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const LoginPage = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const me = await login(username, password)

      // Redirect based on user type and company
      if (me.is_superuser) {
        navigate('/admin/companies')
      } else if (me.company_name) {
        if (me.role === 'AGENT') {
          navigate(`/${me.company_name}/numbers`)
        } else {
          navigate(`/${me.company_name}/dashboard`)
        }
      } else {
        setError('کاربر به شرکتی اختصاص داده نشده است')
      }
    } catch (err) {
      setError('ورود ناموفق بود')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-brand-700 text-white">
      <div className="bg-white text-slate-900 rounded-xl shadow-xl p-8 w-full max-w-md">
        <h1 className="text-xl font-semibold mb-4">ورود مدیر</h1>
        <p className="text-sm text-slate-600 mb-6">به پنل مدیریت تماس خوش آمدید</p>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="text-sm text-slate-700">نام کاربری</label>
            <input
              className="mt-1 w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm text-slate-700">رمز عبور</label>
            <input
              type="password"
              className="mt-1 w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div className="text-red-600 text-sm">{error}</div>}
          <button
            type="submit"
            className="w-full rounded bg-slate-900 text-white py-2 text-sm font-semibold hover:bg-slate-800"
            disabled={loading}
          >
            {loading ? '...' : 'ورود'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage

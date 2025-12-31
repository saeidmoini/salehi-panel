import { useState } from 'react'
import client from '../api/client'
import { useAuth } from '../hooks/useAuth'

const ProfilePage = () => {
  const { user, login } = useAuth()
  const [username, setUsername] = useState(user?.username || '')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState(user?.first_name || '')
  const [lastName, setLastName] = useState(user?.last_name || '')
  const [phoneNumber, setPhoneNumber] = useState(user?.phone_number || '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      await client.put('/api/auth/me', {
        username,
        password: password || undefined,
        first_name: firstName || null,
        last_name: lastName || null,
        phone_number: phoneNumber || null,
      })
      setMessage('ذخیره شد')
      if (password) {
        await login(username || user?.username || '', password)
      }
    } catch (err) {
      setMessage('خطا در ذخیره')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-xl w-full bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <h2 className="font-semibold mb-3">ویرایش حساب کاربری</h2>
      <form className="space-y-3" onSubmit={handleSubmit}>
        <div>
          <label className="text-sm text-slate-600">نام کاربری</label>
          <input
            className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm text-slate-600">رمز عبور جدید</label>
          <input
            type="password"
            className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="برای تغییر رمز، مقدار وارد کنید"
          />
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="text-sm text-slate-600">نام</label>
            <input
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm text-slate-600">نام خانوادگی</label>
            <input
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="text-sm text-slate-600">شماره تماس</label>
          <input
            className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
          />
        </div>
        {message && <div className="text-sm text-slate-600">{message}</div>}
        <button
          type="submit"
          className="rounded bg-brand-500 text-white px-4 py-2 text-sm disabled:opacity-50"
          disabled={saving}
        >
          {saving ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
        </button>
      </form>
    </div>
  )
}

export default ProfilePage

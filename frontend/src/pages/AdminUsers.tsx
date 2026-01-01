import { FormEvent, useEffect, useState } from 'react'
import client from '../api/client'

interface AdminUser {
  id: number
  username: string
  is_active: boolean
  role: 'ADMIN' | 'AGENT'
  is_superuser?: boolean
  first_name?: string | null
  last_name?: string | null
  phone_number?: string | null
}

const AdminUsersPage = () => {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [role, setRole] = useState<'ADMIN' | 'AGENT'>('AGENT')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')

  const fetchUsers = async () => {
    const { data } = await client.get<AdminUser[]>('/api/admins')
    setUsers(data)
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await client.post('/api/admins', {
      username,
      password,
      is_active: isActive,
      role,
      first_name: firstName || null,
      last_name: lastName || null,
      phone_number: phoneNumber || null,
    })
    setUsername('')
    setPassword('')
    setIsActive(true)
    setRole('AGENT')
    setFirstName('')
    setLastName('')
    setPhoneNumber('')
    fetchUsers()
  }

  const toggleActive = async (user: AdminUser) => {
    await client.put(`/api/admins/${user.id}`, { is_active: !user.is_active })
    fetchUsers()
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
        <h2 className="font-semibold mb-3">ایجاد مدیر جدید</h2>
        <form className="grid gap-3 md:grid-cols-3 lg:grid-cols-4 items-end" onSubmit={handleSubmit}>
          <div>
            <label className="text-sm text-slate-600">نام کاربری</label>
            <input
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm text-slate-600">رمز عبور</label>
            <input
              type="password"
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm text-slate-600">نقش</label>
            <select
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={role}
              onChange={(e) => setRole(e.target.value as 'ADMIN' | 'AGENT')}
            >
              <option value="AGENT">کارشناس فروش</option>
              <option value="ADMIN">مدیر</option>
            </select>
          </div>
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
          <div>
            <label className="text-sm text-slate-600">شماره تماس کارشناس</label>
            <input
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            فعال باشد
          </div>
          <button
            type="submit"
            className="rounded bg-brand-500 text-white px-4 py-2 text-sm md:col-span-3 lg:col-span-4 w-full md:w-auto"
          >
            ایجاد کاربر
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
        <h3 className="font-semibold mb-3">لیست مدیران</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-right text-slate-500">
              <th className="py-2">نام کاربری</th>
              <th>نام و نام خانوادگی</th>
              <th>نقش</th>
              <th>شماره تماس</th>
              <th>وضعیت</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="py-2">{u.username}</td>
                <td>
                  {`${(u.first_name || '')} ${(u.last_name || '')}`.trim() || '—'}
                </td>
                <td>{u.role === 'ADMIN' ? 'مدیر' : 'کارشناس'}</td>
                <td className="font-mono text-xs">{u.phone_number || '—'}</td>
                <td>{u.is_active ? 'فعال' : 'غیرفعال'}</td>
                <td className="space-x-3 space-x-reverse">
                  {u.is_superuser ? (
                    <span className="text-xs text-slate-400">—</span>
                  ) : (
                    <>
                      <button className="text-xs text-brand-700" onClick={() => toggleActive(u)}>
                        {u.is_active ? 'غیرفعال کن' : 'فعال کن'}
                      </button>
                      <button
                        className="text-xs text-red-600"
                        onClick={async () => {
                          const ok = window.confirm('کاربر حذف شود؟')
                          if (!ok) return
                          await client.delete(`/api/admins/${u.id}`)
                          fetchUsers()
                        }}
                      >
                        حذف
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default AdminUsersPage

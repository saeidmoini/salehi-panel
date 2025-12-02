import { FormEvent, useEffect, useState } from 'react'
import client from '../api/client'

interface AdminUser {
  id: number
  username: string
  is_active: boolean
}

const AdminUsersPage = () => {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(true)

  const fetchUsers = async () => {
    const { data } = await client.get<AdminUser[]>('/api/admins')
    setUsers(data)
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await client.post('/api/admins', { username, password, is_active: isActive })
    setUsername('')
    setPassword('')
    setIsActive(true)
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
        <form className="grid gap-3 md:grid-cols-3 items-end" onSubmit={handleSubmit}>
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
          <div className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            فعال باشد
          </div>
          <button type="submit" className="rounded bg-brand-500 text-white px-4 py-2 text-sm md:col-span-3 w-full md:w-auto">
            ایجاد مدیر
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
        <h3 className="font-semibold mb-3">لیست مدیران</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="py-2">نام کاربری</th>
              <th>وضعیت</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="py-2">{u.username}</td>
                <td>{u.is_active ? 'فعال' : 'غیرفعال'}</td>
                <td>
                  <button className="text-xs text-brand-700" onClick={() => toggleActive(u)}>
                    {u.is_active ? 'غیرفعال کن' : 'فعال کن'}
                  </button>
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

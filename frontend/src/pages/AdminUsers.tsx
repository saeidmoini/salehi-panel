import { FormEvent, useEffect, useState } from 'react'
import { useCompany } from '../hooks/useCompany'
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
  company_id?: number | null
  company_name?: string | null
  agent_type?: 'INBOUND' | 'OUTBOUND' | 'BOTH'
}

const AdminUsersPage = () => {
  const { company } = useCompany()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [role, setRole] = useState<'ADMIN' | 'AGENT'>('AGENT')
  const [agentType, setAgentType] = useState<'INBOUND' | 'OUTBOUND' | 'BOTH'>('BOTH')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [editingUserId, setEditingUserId] = useState<number | null>(null)
  const [editPassword, setEditPassword] = useState('')
  const [editIsActive, setEditIsActive] = useState(true)
  const [editRole, setEditRole] = useState<'ADMIN' | 'AGENT'>('AGENT')
  const [editAgentType, setEditAgentType] = useState<'INBOUND' | 'OUTBOUND' | 'BOTH'>('BOTH')
  const [editFirstName, setEditFirstName] = useState('')
  const [editLastName, setEditLastName] = useState('')
  const [editPhoneNumber, setEditPhoneNumber] = useState('')

  const fetchUsers = async () => {
    if (!company) return
    const { data } = await client.get<AdminUser[]>(`/api/${company.name}/admins`)
    setUsers(data.filter((u) => !u.is_superuser))
  }

  useEffect(() => {
    if (company) {
      fetchUsers()
    }
  }, [company])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!company) return
    await client.post(`/api/${company.name}/admins`, {
      username,
      password,
      is_active: isActive,
      role,
      agent_type: agentType,
      first_name: firstName || null,
      last_name: lastName || null,
      phone_number: phoneNumber || null,
    })
    setUsername('')
    setPassword('')
    setIsActive(true)
    setRole('AGENT')
    setAgentType('BOTH')
    setFirstName('')
    setLastName('')
    setPhoneNumber('')
    fetchUsers()
  }

  const toggleActive = async (user: AdminUser) => {
    if (!company) return
    await client.put(`/api/${company.name}/admins/${user.id}`, { is_active: !user.is_active })
    fetchUsers()
  }

  const startEdit = (user: AdminUser) => {
    setEditingUserId(user.id)
    setEditPassword('')
    setEditIsActive(user.is_active)
    setEditRole(user.role)
    setEditAgentType(user.agent_type || 'BOTH')
    setEditFirstName(user.first_name || '')
    setEditLastName(user.last_name || '')
    setEditPhoneNumber(user.phone_number || '')
  }

  const cancelEdit = () => {
    setEditingUserId(null)
    setEditPassword('')
    setEditIsActive(true)
    setEditRole('AGENT')
    setEditAgentType('BOTH')
    setEditFirstName('')
    setEditLastName('')
    setEditPhoneNumber('')
  }

  const submitEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!company || !editingUserId) return
    await client.put(`/api/${company.name}/admins/${editingUserId}`, {
      password: editPassword || undefined,
      is_active: editIsActive,
      role: editRole,
      agent_type: editAgentType,
      first_name: editFirstName || null,
      last_name: editLastName || null,
      phone_number: editPhoneNumber || null,
    })
    cancelEdit()
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
            <label className="text-sm text-slate-600">نوع اپراتور</label>
            <select
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              value={agentType}
              onChange={(e) => setAgentType(e.target.value as 'INBOUND' | 'OUTBOUND' | 'BOTH')}
            >
              <option value="BOTH">ورودی و خروجی (هردو)</option>
              <option value="INBOUND">فقط ورودی</option>
              <option value="OUTBOUND">فقط خروجی</option>
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
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="text-right text-slate-500">
                <th className="py-2 whitespace-nowrap">نام کاربری</th>
                <th className="whitespace-nowrap">نام و نام خانوادگی</th>
                <th className="whitespace-nowrap">نقش</th>
                <th className="whitespace-nowrap">نوع اپراتور</th>
                <th className="whitespace-nowrap">شماره تماس</th>
                <th className="whitespace-nowrap">وضعیت</th>
                <th className="whitespace-nowrap"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t">
                  <td className="py-2 whitespace-nowrap">{u.username}</td>
                  <td className="whitespace-nowrap">
                    {`${(u.first_name || '')} ${(u.last_name || '')}`.trim() || '—'}
                  </td>
                  <td className="whitespace-nowrap">{u.role === 'ADMIN' ? 'مدیر' : 'کارشناس'}</td>
                  <td className="text-xs whitespace-nowrap">
                    {u.agent_type === 'INBOUND' && 'ورودی'}
                    {u.agent_type === 'OUTBOUND' && 'خروجی'}
                    {u.agent_type === 'BOTH' && 'هردو'}
                    {!u.agent_type && '—'}
                  </td>
                  <td className="font-mono text-xs whitespace-nowrap">{u.phone_number || '—'}</td>
                  <td className="whitespace-nowrap">{u.is_active ? 'فعال' : 'غیرفعال'}</td>
                  <td className="space-x-3 space-x-reverse whitespace-nowrap">
                    <button className="text-xs text-brand-700" onClick={() => startEdit(u)}>
                      ویرایش
                    </button>
                    <button className="text-xs text-brand-700" onClick={() => toggleActive(u)}>
                      {u.is_active ? 'غیرفعال کن' : 'فعال کن'}
                    </button>
                    <button
                      className="text-xs text-red-600"
                      onClick={async () => {
                        if (!company) return
                        const ok = window.confirm('کاربر حذف شود؟')
                        if (!ok) return
                        await client.delete(`/api/${company.name}/admins/${u.id}`)
                        if (editingUserId === u.id) cancelEdit()
                        fetchUsers()
                      }}
                    >
                      حذف
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {editingUserId && (
        <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
          <h3 className="font-semibold mb-3">ویرایش کاربر</h3>
          <form className="grid gap-3 md:grid-cols-3 lg:grid-cols-4 items-end" onSubmit={submitEdit}>
            <div>
              <label className="text-sm text-slate-600">رمز عبور جدید (اختیاری)</label>
              <input
                type="password"
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                value={editPassword}
                onChange={(e) => setEditPassword(e.target.value)}
                placeholder="در صورت نیاز تغییر دهید"
              />
            </div>
            <div>
              <label className="text-sm text-slate-600">نقش</label>
              <select
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                value={editRole}
                onChange={(e) => setEditRole(e.target.value as 'ADMIN' | 'AGENT')}
              >
                <option value="AGENT">کارشناس فروش</option>
                <option value="ADMIN">مدیر</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-slate-600">نوع اپراتور</label>
              <select
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                value={editAgentType}
                onChange={(e) => setEditAgentType(e.target.value as 'INBOUND' | 'OUTBOUND' | 'BOTH')}
              >
                <option value="BOTH">ورودی و خروجی (هردو)</option>
                <option value="INBOUND">فقط ورودی</option>
                <option value="OUTBOUND">فقط خروجی</option>
              </select>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={editIsActive} onChange={(e) => setEditIsActive(e.target.checked)} />
              فعال باشد
            </div>
            <div>
              <label className="text-sm text-slate-600">نام</label>
              <input
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                value={editFirstName}
                onChange={(e) => setEditFirstName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm text-slate-600">نام خانوادگی</label>
              <input
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                value={editLastName}
                onChange={(e) => setEditLastName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm text-slate-600">شماره تماس کارشناس</label>
              <input
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                value={editPhoneNumber}
                onChange={(e) => setEditPhoneNumber(e.target.value)}
              />
            </div>
            <div className="flex gap-2 md:col-span-3 lg:col-span-4 w-full md:w-auto">
              <button type="submit" className="rounded bg-brand-500 text-white px-4 py-2 text-sm">
                ذخیره تغییرات
              </button>
              <button type="button" className="rounded border border-slate-300 px-4 py-2 text-sm" onClick={cancelEdit}>
                انصراف
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

export default AdminUsersPage

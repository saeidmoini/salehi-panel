import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

interface Company {
  id: number
  name: string
  display_name: string
  is_active: boolean
  settings?: Record<string, any>
}

const CompanySelectorPage = () => {
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)

  const [name, setName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [isActive, setIsActive] = useState(true)

  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editDisplayName, setEditDisplayName] = useState('')
  const [editIsActive, setEditIsActive] = useState(true)

  const [deleteCompanyId, setDeleteCompanyId] = useState<number | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState('')

  const deleteTarget = useMemo(
    () => companies.find((c) => c.id === deleteCompanyId) || null,
    [companies, deleteCompanyId],
  )

  const fetchCompanies = async () => {
    try {
      const { data } = await client.get<Company[]>('/api/companies')
      setCompanies(data)
    } catch (error) {
      console.error('Failed to fetch companies', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCompanies()
  }, [])

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    await client.post('/api/companies', {
      name: name.trim(),
      display_name: displayName.trim(),
      is_active: isActive,
    })
    setName('')
    setDisplayName('')
    setIsActive(true)
    fetchCompanies()
  }

  const startEdit = (company: Company) => {
    setEditingId(company.id)
    setEditName(company.name)
    setEditDisplayName(company.display_name)
    setEditIsActive(company.is_active)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditName('')
    setEditDisplayName('')
    setEditIsActive(true)
  }

  const handleUpdate = async (e: FormEvent) => {
    e.preventDefault()
    if (!editingId) return
    await client.put(`/api/companies/${editingId}`, {
      name: editName.trim(),
      display_name: editDisplayName.trim(),
      is_active: editIsActive,
    })
    cancelEdit()
    fetchCompanies()
  }

  const toggleActive = async (company: Company) => {
    await client.put(`/api/companies/${company.id}`, {
      is_active: !company.is_active,
    })
    fetchCompanies()
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    if (deleteConfirm !== deleteTarget.name) {
      alert('نام شرکت درست وارد نشده است')
      return
    }
    const ok = window.confirm(`حذف کامل شرکت "${deleteTarget.display_name}" انجام شود؟ این عملیات قابل بازگشت نیست.`)
    if (!ok) return
    await client.delete(`/api/companies/${deleteTarget.id}`, {
      data: { confirm_name: deleteConfirm },
    })
    setDeleteCompanyId(null)
    setDeleteConfirm('')
    fetchCompanies()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-slate-500">در حال بارگذاری...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">مدیریت شرکت‌ها</h1>
        <p className="text-sm text-slate-600 mt-1">ساخت، ویرایش و حذف شرکت‌ها (فقط سوپر ادمین)</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <h2 className="font-semibold mb-3">انتخاب شرکت برای ورود به پنل</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.filter((c) => c.is_active).map((company) => (
            <div
              key={`entry-${company.id}`}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
              onClick={() => navigate(`/${company.name}/dashboard`)}
            >
              <div className="flex flex-col items-center text-center gap-3">
                <div className="w-16 h-16 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 text-2xl font-bold">
                  {company.display_name.charAt(0)}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 group-hover:text-brand-600 transition-colors">
                    {company.display_name}
                  </h3>
                  <p className="text-sm text-slate-500 font-mono">{company.name}</p>
                </div>
                <span className="inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                  فعال
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <h2 className="font-semibold mb-3">ایجاد شرکت جدید</h2>
        <form className="grid gap-3 md:grid-cols-2 lg:grid-cols-4 items-end" onSubmit={handleCreate}>
          <div>
            <label className="text-sm text-slate-600">نام فنی (slug)</label>
            <input className="w-full rounded border border-slate-200 px-3 py-2 text-sm" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-slate-600">نام نمایشی</label>
            <input className="w-full rounded border border-slate-200 px-3 py-2 text-sm" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            فعال باشد
          </div>
          <button type="submit" className="rounded bg-brand-500 text-white px-4 py-2 text-sm w-full md:w-auto">
            ایجاد شرکت
          </button>
        </form>
      </div>

      {editingId && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h2 className="font-semibold mb-3">ویرایش شرکت</h2>
          <form className="grid gap-3 md:grid-cols-2 lg:grid-cols-4 items-end" onSubmit={handleUpdate}>
            <div>
              <label className="text-sm text-slate-600">نام فنی (slug)</label>
              <input className="w-full rounded border border-slate-200 px-3 py-2 text-sm" value={editName} onChange={(e) => setEditName(e.target.value)} />
            </div>
            <div>
              <label className="text-sm text-slate-600">نام نمایشی</label>
              <input className="w-full rounded border border-slate-200 px-3 py-2 text-sm" value={editDisplayName} onChange={(e) => setEditDisplayName(e.target.value)} />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={editIsActive} onChange={(e) => setEditIsActive(e.target.checked)} />
              فعال باشد
            </div>
            <div className="flex gap-2 lg:col-span-4">
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

      {deleteTarget && (
        <div className="bg-red-50 rounded-xl border border-red-200 p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-red-700">حذف کامل شرکت</h2>
          <p className="text-sm text-red-700">
            برای حذف کامل، نام فنی شرکت را وارد کنید: <span className="font-mono font-semibold">{deleteTarget.name}</span>
          </p>
          <input
            className="w-full rounded border border-red-300 px-3 py-2 text-sm font-mono"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
            placeholder="نام فنی شرکت را تایپ کنید"
          />
          <div className="flex gap-2">
            <button className="rounded bg-red-600 text-white px-4 py-2 text-sm" onClick={handleDelete}>
              حذف قطعی شرکت
            </button>
            <button
              className="rounded border border-slate-300 px-4 py-2 text-sm"
              onClick={() => {
                setDeleteCompanyId(null)
                setDeleteConfirm('')
              }}
            >
              انصراف
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <h2 className="font-semibold mb-3">لیست شرکت‌ها</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.map((company) => (
            <div key={company.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <div className="flex flex-col gap-2">
                <div className="text-lg font-semibold">{company.display_name}</div>
                <div className="text-xs font-mono text-slate-500">{company.name}</div>
                <div>
                  <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${company.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>
                    {company.is_active ? 'فعال' : 'غیرفعال'}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 pt-2">
                  <button
                    className="rounded border border-slate-300 px-3 py-1 text-xs"
                    disabled={!company.is_active}
                    onClick={() => navigate(`/${company.name}/dashboard`)}
                  >
                    ورود به پنل
                  </button>
                  <button className="rounded border border-brand-300 text-brand-700 px-3 py-1 text-xs" onClick={() => startEdit(company)}>
                    ویرایش
                  </button>
                  <button
                    className="rounded border border-slate-300 px-3 py-1 text-xs"
                    onClick={() => toggleActive(company)}
                  >
                    {company.is_active ? 'غیرفعال کن' : 'فعال کن'}
                  </button>
                  <button
                    className="rounded border border-red-300 text-red-700 px-3 py-1 text-xs"
                    onClick={() => {
                      setDeleteCompanyId(company.id)
                      setDeleteConfirm('')
                    }}
                  >
                    حذف کامل
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
        {companies.length === 0 && <div className="text-sm text-slate-500">هیچ شرکتی ثبت نشده است.</div>}
      </div>
    </div>
  )
}

export default CompanySelectorPage

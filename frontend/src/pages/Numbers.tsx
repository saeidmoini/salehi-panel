import { FormEvent, useEffect, useState } from 'react'
import client from '../api/client'
import dayjs from 'dayjs'

interface PhoneNumber {
  id: number
  phone_number: string
  status: string
  total_attempts: number
  last_attempt_at?: string
  last_status_change_at?: string
}

const statusLabels: Record<string, string> = {
  IN_QUEUE: 'در صف تماس',
  MISSED: 'از دست رفته',
  CONNECTED: 'موفق',
  FAILED: 'خطا دریافت شد',
  NOT_INTERESTED: 'عدم نیاز کاربر',
  HANGUP: 'قطع تماس توسط کاربر',
  DISCONNECTED: 'ناموفق',
}

const statusColors: Record<string, string> = {
  IN_QUEUE: 'bg-amber-100 text-amber-800',
  MISSED: 'bg-orange-100 text-orange-800',
  CONNECTED: 'bg-emerald-100 text-emerald-800',
  FAILED: 'bg-red-100 text-red-800',
  NOT_INTERESTED: 'bg-slate-200 text-slate-800',
  HANGUP: 'bg-purple-100 text-purple-800',
  DISCONNECTED: 'bg-gray-200 text-gray-800',
}

const NumbersPage = () => {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [newNumbers, setNewNumbers] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)

  const fetchNumbers = async () => {
    setLoading(true)
    const { data } = await client.get<PhoneNumber[]>('/api/numbers', {
      params: {
        status: statusFilter || undefined,
        search: search || undefined,
      },
    })
    setNumbers(data)
    setLoading(false)
  }

  useEffect(() => {
    fetchNumbers()
  }, [])

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    const phone_numbers = newNumbers.split(/\n|,/).map((s) => s.trim()).filter(Boolean)
    if (!phone_numbers.length) return
    await client.post('/api/numbers', { phone_numbers })
    setNewNumbers('')
    fetchNumbers()
  }

  const updateStatus = async (id: number, status: string) => {
    await client.put(`/api/numbers/${id}/status`, { status })
    fetchNumbers()
  }

  const deleteNumber = async (id: number) => {
    const ok = window.confirm('این شماره حذف شود؟')
    if (!ok) return
    await client.delete(`/api/numbers/${id}`)
    setNumbers((prev) => prev.filter((n) => n.id !== id))
  }

  const resetNumber = async (id: number) => {
    await client.post(`/api/numbers/${id}/reset`)
    fetchNumbers()
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMessage(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await client.post('/api/numbers/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setUploadMessage(`افزودن از فایل: ${data.inserted} اضافه شد، ${data.duplicates} تکراری، ${data.invalid} نامعتبر`)
      fetchNumbers()
    } catch (err) {
      setUploadMessage('خطا در بارگذاری فایل')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="space-y-6 px-2 md:px-0 max-w-full w-full min-w-0">
      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm w-full min-w-0">
        <h2 className="font-semibold mb-3">افزودن شماره جدید</h2>
        <div className="flex flex-col md:flex-row gap-6">
          <form className="flex-1 space-y-3 w-full" onSubmit={handleAdd}>
            <textarea
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              rows={3}
              placeholder="هر خط یک شماره"
              value={newNumbers}
              onChange={(e) => setNewNumbers(e.target.value)}
            />
            <button type="submit" className="rounded bg-brand-500 text-white px-4 py-2 text-sm hover:bg-brand-700">
              افزودن به صف
            </button>
          </form>
          <div className="flex-1 space-y-2 w-full">
            <label className="block text-sm font-medium text-slate-700">افزودن از فایل (یک ستون شماره)</label>
            <input
              type="file"
              accept=".csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              onChange={handleUpload}
              className="block w-full text-sm text-slate-700 file:mr-4 file:rounded file:border-0 file:bg-brand-500 file:px-4 file:py-2 file:text-white hover:file:bg-brand-700"
              disabled={uploading}
            />
            {uploadMessage && <div className="text-xs text-slate-600">{uploadMessage}</div>}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm w-full min-w-0">
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <select
            className="rounded border border-slate-200 px-2 py-1 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">همه وضعیت‌ها</option>
            {Object.entries(statusLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="جستجوی شماره"
            className="rounded border border-slate-200 px-2 py-1 text-sm"
          />
          <button onClick={fetchNumbers} className="rounded bg-slate-900 text-white px-3 py-1 text-sm">
            بروزرسانی
          </button>
        </div>
        {loading ? (
          <div className="text-sm">در حال بارگذاری...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm text-right whitespace-nowrap">
              <thead>
                <tr className="text-slate-500">
                  <th className="py-2 text-right">شماره</th>
                  <th className="text-right">وضعیت</th>
                  <th className="text-right">تعداد تلاش</th>
                  <th className="text-right">آخرین تلاش</th>
                  <th className="text-right">اقدامات</th>
                </tr>
              </thead>
              <tbody>
                {numbers.map((n) => (
                  <tr key={n.id} className="border-t">
                    <td className="py-2 font-mono text-xs">{n.phone_number}</td>
                    <td className="text-right">
                      <span
                        className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${statusColors[n.status] || 'bg-slate-100 text-slate-700'}`}
                      >
                        {statusLabels[n.status] || n.status}
                      </span>
                    </td>
                    <td className="text-right">{n.total_attempts}</td>
                    <td className="text-right">
                      {n.last_attempt_at ? dayjs(n.last_attempt_at).calendar('jalali').format('YYYY/MM/DD HH:mm') : '-'}
                    </td>
                    <td className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <select
                          className="rounded border border-slate-200 px-2 py-1 text-xs"
                          value={n.status}
                          onChange={(e) => updateStatus(n.id, e.target.value)}
                        >
                          {Object.keys(statusLabels).map((key) => (
                            <option key={key} value={key}>
                              {statusLabels[key]}
                            </option>
                          ))}
                        </select>
                        <button
                          className="text-xs text-amber-700"
                          onClick={() => resetNumber(n.id)}
                          title="بازگشت به صف"
                        >
                          ریست
                        </button>
                        <button
                          className="text-xs text-red-600"
                          onClick={() => deleteNumber(n.id)}
                          title="حذف شماره"
                        >
                          حذف
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default NumbersPage

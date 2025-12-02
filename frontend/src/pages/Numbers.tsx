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
}

const statusColors: Record<string, string> = {
  IN_QUEUE: 'bg-amber-100 text-amber-800',
  MISSED: 'bg-orange-100 text-orange-800',
  CONNECTED: 'bg-emerald-100 text-emerald-800',
  FAILED: 'bg-red-100 text-red-800',
  NOT_INTERESTED: 'bg-slate-200 text-slate-800',
}

const NumbersPage = () => {
  const [numbers, setNumbers] = useState<PhoneNumber[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [newNumbers, setNewNumbers] = useState('')
  const [loading, setLoading] = useState(false)

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

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
        <h2 className="font-semibold mb-3">افزودن شماره جدید</h2>
        <form className="space-y-3" onSubmit={handleAdd}>
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
      </div>

      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
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
            <table className="w-full text-sm text-right">
              <thead>
                <tr className="text-slate-500">
                  <th className="py-2 text-right">شماره</th>
                  <th className="text-right">وضعیت</th>
                  <th className="text-right">تعداد تلاش</th>
                  <th className="text-right">آخرین تلاش</th>
                  <th className="text-right"></th>
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

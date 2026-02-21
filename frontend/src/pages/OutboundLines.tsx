import { useEffect, useState } from 'react'
import { useCompany } from '../hooks/useCompany'
import client from '../api/client'

interface OutboundLine {
  id: number
  phone_number: string
  display_name: string
  is_active: boolean
  created_at: string
}

const OutboundLinesPage = () => {
  const { company } = useCompany()
  const [lines, setLines] = useState<OutboundLine[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (company) {
      fetchLines()
    }
  }, [company])

  const fetchLines = async () => {
    if (!company) return
    setLoading(true)
    try {
      const { data } = await client.get<OutboundLine[]>(`/api/${company.name}/outbound-lines`)
      setLines(data)
    } catch (error) {
      console.error('Failed to fetch outbound lines', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleActive = async (line: OutboundLine) => {
    if (!company) return
    try {
      await client.put(`/api/${company.name}/outbound-lines/${line.id}`, {
        is_active: !line.is_active
      })
      fetchLines()
    } catch (error) {
      console.error('Failed to toggle line', error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-slate-500">در حال بارگذاری...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">مدیریت خطوط خروجی</h1>
          <p className="text-sm text-slate-600 mt-1">
            خطوط تلفن خروجی برای شرکت {company?.display_name}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            حذف خطوط خروجی از طریق پنل غیرفعال است.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-100 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr className="text-right text-slate-700">
                <th className="py-3 px-4 font-semibold">شناسه</th>
                <th className="py-3 px-4 font-semibold">شماره تلفن</th>
                <th className="py-3 px-4 font-semibold">نام نمایشی</th>
                <th className="py-3 px-4 font-semibold">وضعیت</th>
                <th className="py-3 px-4 font-semibold">تاریخ ایجاد</th>
                <th className="py-3 px-4 font-semibold">عملیات</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <tr key={line.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="py-3 px-4 font-mono text-xs">{line.id}</td>
                  <td className="py-3 px-4 font-mono">{line.phone_number}</td>
                  <td className="py-3 px-4">{line.display_name}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold ${
                        line.is_active
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {line.is_active ? 'فعال' : 'غیرفعال'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-500">
                    {new Date(line.created_at).toLocaleDateString('fa-IR')}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      <button
                        className={`text-xs px-3 py-1 rounded ${
                          line.is_active
                            ? 'text-orange-600 hover:bg-orange-50'
                            : 'text-emerald-600 hover:bg-emerald-50'
                        }`}
                        onClick={() => toggleActive(line)}
                      >
                        {line.is_active ? 'غیرفعال' : 'فعال'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {lines.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-slate-500">
              هیچ خط خروجی ثبت نشده است. ثبت خطوط توسط مرکز تماس انجام می‌شود.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default OutboundLinesPage

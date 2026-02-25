import { useEffect, useState } from 'react'
import { useCompany } from '../hooks/useCompany'
import client from '../api/client'

interface Scenario {
  id: number
  name: string
  display_name: string
  cost_per_connected: number
  is_active: boolean
  created_at: string
}

const ScenariosPage = () => {
  const { company } = useCompany()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (company) {
      fetchScenarios()
    }
  }, [company])

  const fetchScenarios = async () => {
    if (!company) return
    setLoading(true)
    try {
      const { data } = await client.get<Scenario[]>(`/api/${company.name}/scenarios`)
      setScenarios(data)
    } catch (error) {
      console.error('Failed to fetch scenarios', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleActive = async (scenario: Scenario) => {
    if (!company) return
    try {
      await client.put(`/api/${company.name}/scenarios/${scenario.id}`, {
        is_active: !scenario.is_active
      })
      fetchScenarios()
    } catch (error) {
      console.error('Failed to toggle scenario', error)
    }
  }

  const editCost = async (scenario: Scenario) => {
    if (!company) return
    const value = window.prompt('هزینه هر تماس برای این سناریو (تومان):', String(scenario.cost_per_connected ?? 0))
    if (value === null) return
    const parsed = Number(value)
    if (!Number.isFinite(parsed) || parsed < 0) {
      window.alert('مقدار وارد شده معتبر نیست.')
      return
    }
    try {
      await client.put(`/api/${company.name}/scenarios/${scenario.id}`, {
        cost_per_connected: Math.floor(parsed)
      })
      fetchScenarios()
    } catch (error) {
      console.error('Failed to update scenario cost', error)
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
      <div>
        <h1 className="text-2xl font-bold text-slate-900">مدیریت سناریوها</h1>
        <p className="text-sm text-slate-600 mt-1">
          سناریوهای تماس برای شرکت {company?.display_name}
        </p>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          <strong>توجه:</strong> سناریوها به صورت خودکار توسط سیستم دایلر ثبت می‌شوند.
          شما می‌توانید وضعیت فعال/غیرفعال و هزینه هر سناریو را تغییر دهید.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-100 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr className="text-right text-slate-700">
                <th className="py-3 px-4 font-semibold">شناسه</th>
                <th className="py-3 px-4 font-semibold">نام فنی</th>
                <th className="py-3 px-4 font-semibold">نام نمایشی</th>
                <th className="py-3 px-4 font-semibold">هزینه هر تماس (تومان)</th>
                <th className="py-3 px-4 font-semibold">وضعیت</th>
                <th className="py-3 px-4 font-semibold">تاریخ ایجاد</th>
                <th className="py-3 px-4 font-semibold">عملیات</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((scenario) => (
                <tr key={scenario.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="py-3 px-4 font-mono text-xs">{scenario.id}</td>
                  <td className="py-3 px-4 font-mono text-xs">{scenario.name}</td>
                  <td className="py-3 px-4">{scenario.display_name}</td>
                  <td className="py-3 px-4 font-mono text-xs">
                    {(scenario.cost_per_connected ?? 0).toLocaleString()}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold ${
                        scenario.is_active
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {scenario.is_active ? 'فعال' : 'غیرفعال'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-500">
                    {new Date(scenario.created_at).toLocaleDateString('fa-IR')}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      <button
                        className={`text-xs px-3 py-1 rounded ${
                          scenario.is_active
                            ? 'text-red-600 hover:bg-red-50'
                            : 'text-emerald-600 hover:bg-emerald-50'
                        }`}
                        onClick={() => toggleActive(scenario)}
                      >
                        {scenario.is_active ? 'غیرفعال کردن' : 'فعال کردن'}
                      </button>
                      <button
                        className="text-xs px-3 py-1 rounded text-blue-700 hover:bg-blue-50"
                        onClick={() => editCost(scenario)}
                      >
                        ویرایش هزینه
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {scenarios.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-slate-500">
              هیچ سناریویی یافت نشد. سناریوها به صورت خودکار توسط سیستم دایلر ثبت می‌شوند.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default ScenariosPage

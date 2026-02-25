import { useEffect, useMemo, useState } from 'react'
import { useCompany } from '../hooks/useCompany'
import client from '../api/client'
import dayjs from 'dayjs'
import jalaliday from 'jalaliday'
import { Chart as ChartJS, PointElement, LineElement, CategoryScale, LinearScale, Tooltip, Legend, Filler } from 'chart.js'
import { Line } from 'react-chartjs-2'

dayjs.extend(jalaliday)
ChartJS.register(PointElement, LineElement, CategoryScale, LinearScale, Tooltip, Legend, Filler)

interface ScheduleConfig {
  enabled: boolean
  version: number
  disabled_by_dialer?: boolean
  wallet_balance?: number
  cost_per_connected?: number
}

interface BillingInfo {
  wallet_balance: number
  cost_per_connected: number
  currency: string
}

interface CostSummary {
  currency: string
  daily_cost: number
  daily_count: number
}

interface NumbersSummary {
  total_numbers: number
  status_counts: Array<{ status: string; count: number }>
}

interface TimeBucketBreakdown {
  bucket: string
  total_attempts: number
  status_counts: Array<{ status: string; count: number; percentage: number }>
}

interface AttemptTrendResponse {
  granularity: 'day' | 'hour'
  buckets: TimeBucketBreakdown[]
}

interface DashboardGroup {
  id: number
  name: string
  display_name: string
  statuses: Record<string, number>
  total: number
  billable: number
  inbound: number
}

interface DashboardStats {
  groups: DashboardGroup[]
  totals: Record<string, number>
}

// Updated status labels in Persian
const statusLabels: Record<string, string> = {
  CONNECTED: 'وصل شده',
  DISCONNECTED: 'وصل نشده',
  NOT_INTERESTED: 'عدم نیاز کاربر',
  HANGUP: 'قطع شده',
  UNKNOWN: 'نامشخص',
  MISSED: 'از دست رفته',
  BUSY: 'اشغال',
  POWER_OFF: 'خاموش',
  FAILED: 'خطا',
  INBOUND_CALL: 'تماس ورودی',
  BANNED: 'بن شده',
  IN_QUEUE: 'در صف تماس',
}

const statusColors: Record<string, string> = {
  CONNECTED: '#10b981',
  DISCONNECTED: '#6b7280',
  NOT_INTERESTED: '#94a3b8',
  HANGUP: '#a855f7',
  UNKNOWN: '#f59e0b',
  MISSED: '#fb923c',
  BUSY: '#e11d48',
  POWER_OFF: '#1e293b',
  FAILED: '#ef4444',
  INBOUND_CALL: '#0ea5e9',
  BANNED: '#be123c',
}

const BILLABLE_STATUSES = [
  'CONNECTED', 'NOT_INTERESTED', 'HANGUP', 'UNKNOWN', 'DISCONNECTED', 'FAILED'
]

type TimeFilter = '1h' | 'today' | 'yesterday' | '7d' | '30d'
type GroupBy = 'scenario' | 'line'

const DashboardPage = () => {
  const { company } = useCompany()
  const [config, setConfig] = useState<ScheduleConfig | null>(null)
  const [billing, setBilling] = useState<BillingInfo | null>(null)
  const [costs, setCosts] = useState<CostSummary | null>(null)
  const [numbersSummary, setNumbersSummary] = useState<NumbersSummary | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(false)
  const [trend, setTrend] = useState<AttemptTrendResponse | null>(null)
  const [trendMode, setTrendMode] = useState<'hour24' | 'day7' | 'day14' | 'day30'>('hour24')
  const filteredStatuses = useMemo(() => [...Object.keys(statusLabels).filter((s) => s !== 'IN_QUEUE'), 'BILLABLE'], [])
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(() =>
    ['HANGUP', 'MISSED', 'BILLABLE']
  )

  const [groupBy, setGroupBy] = useState<GroupBy>('scenario')
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('today')

  useEffect(() => {
    if (!company) return
    fetchConfig()
    fetchBilling()
    fetchCosts()
    fetchNumbers()
  }, [company])

  useEffect(() => {
    if (!company) return
    fetchStats()
  }, [company, groupBy, timeFilter])

  useEffect(() => {
    if (!company) return
    fetchTrend(trendMode)
  }, [company, trendMode])

  const fetchConfig = async () => {
    if (!company) return
    try {
      const { data } = await client.get<ScheduleConfig>(`/api/${company.name}/schedule`)
      setConfig(data)
    } catch (error) {
      console.error('Failed to fetch config', error)
    }
  }

  const fetchBilling = async () => {
    if (!company) return
    try {
      const { data } = await client.get<BillingInfo>(`/api/${company.name}/billing`)
      setBilling(data)
    } catch (error) {
      console.error('Failed to fetch billing', error)
    }
  }

  const fetchCosts = async () => {
    if (!company) return
    try {
      const { data } = await client.get<CostSummary>('/api/stats/costs', {
        params: { company: company.name }
      })
      setCosts(data)
    } catch (error) {
      console.error('Failed to fetch costs', error)
    }
  }

  const fetchNumbers = async () => {
    if (!company) return
    try {
      const { data } = await client.get<NumbersSummary>('/api/stats/numbers-summary', {
        params: { company: company.name }
      })
      setNumbersSummary(data)
    } catch (error) {
      console.error('Failed to fetch numbers', error)
    }
  }

  const fetchTrend = async (mode: typeof trendMode) => {
    if (!company) return
    const params: Record<string, number | string> = { company: company.name }
    if (mode === 'hour24') { params.granularity = 'hour'; params.span = 24 }
    else if (mode === 'day7') { params.granularity = 'day'; params.span = 7 }
    else if (mode === 'day14') { params.granularity = 'day'; params.span = 14 }
    else if (mode === 'day30') { params.granularity = 'day'; params.span = 30 }
    try {
      const { data } = await client.get<AttemptTrendResponse>('/api/stats/attempt-trend', { params })
      setTrend(data)
    } catch (error) {
      console.error('Failed to fetch trend', error)
    }
  }

  const fetchStats = async () => {
    if (!company) return
    setLoading(true)
    try {
      const { data } = await client.get<DashboardStats>('/api/stats/dashboard-stats', {
        params: {
          company: company.name,
          group_by: groupBy,
          time_filter: timeFilter
        }
      })
      setStats(data)
    } catch (error) {
      console.error('Failed to fetch stats', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleDialer = async () => {
    if (!config || !company) return
    setSaving(true)
    try {
      const { data } = await client.put(`/api/${company.name}/schedule`, {
        enabled: !config.enabled
      })
      setConfig((prev) => (prev ? { ...prev, enabled: data.enabled } : data))
    } catch (error) {
      console.error('Failed to toggle dialer', error)
    } finally {
      setSaving(false)
    }
  }

  const inQueueCount = numbersSummary?.status_counts.find((s) => s.status === 'IN_QUEUE')?.count ?? 0

  const lineData = useMemo(() => {
    if (!trend) return null
    const labels = trend.buckets.map((b) =>
      trend.granularity === 'hour'
        ? dayjs(b.bucket).calendar('jalali').format('YYYY/MM/DD HH:mm')
        : dayjs(b.bucket).calendar('jalali').format('YYYY/MM/DD')
    )
    const datasets = selectedStatuses.map((status) => {
      const color = statusColors[status] || '#0ea5e9'

      // Special handling for BILLABLE virtual status
      if (status === 'BILLABLE') {
        return {
          label: 'انجام شده',
          statusKey: 'BILLABLE',
          data: trend.buckets.map((bucket) => {
            const billableCount = BILLABLE_STATUSES.reduce((sum, billableStatus) => {
              const match = bucket.status_counts.find((s) => s.status === billableStatus)
              return sum + (match ? match.count : 0)
            }, 0)
            const total = bucket.total_attempts
            return total > 0 ? Number(((billableCount / total) * 100).toFixed(2)) : 0
          }),
          borderColor: '#3b82f6',
          backgroundColor: '#3b82f620',
          fill: false,
          tension: 0.35,
          pointRadius: 3,
          borderWidth: 3,
        }
      }

      return {
        label: statusLabels[status] || status,
        statusKey: status,
        data: trend.buckets.map((bucket) => {
          const match = bucket.status_counts.find((s) => s.status === status)
          return match ? Number(match.percentage.toFixed(2)) : 0
        }),
        borderColor: color,
        backgroundColor: color + '20',
        fill: false,
        tension: 0.35,
        pointRadius: 3,
      }
    })
    return { labels, datasets }
  }, [trend, selectedStatuses])

  const toggleStatusFilter = (status: string) => {
    setSelectedStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]
    )
  }

  const trendModeLabel =
    trendMode === 'hour24' ? '۲۴ ساعت گذشته'
      : trendMode === 'day7' ? '۷ روز گذشته'
        : trendMode === 'day14' ? '۱۴ روز گذشته'
          : '۳۰ روز گذشته'

  return (
    <div className="space-y-6">
      {/* Section 1: Full-width control bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Wallet Balance Card */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100">
          <h3 className="text-sm text-slate-500 mb-2">موجودی کیف پول</h3>
          <div className="text-2xl font-bold text-slate-900">
            {billing ? billing.wallet_balance.toLocaleString() : '-'} تومان
          </div>
          <div className="text-xs text-slate-500 mt-1">
            هزینه پیش‌فرض هر تماس: {billing ? billing.cost_per_connected.toLocaleString() : '-'} تومان
          </div>
          {billing && billing.wallet_balance <= 0 && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-2 py-1 mt-2">
              موجودی کیف پول صفر است
            </div>
          )}
        </div>

        {/* Today's Cost Card */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100">
          <h3 className="text-sm text-slate-500 mb-2">هزینه امروز</h3>
          <div className="text-2xl font-bold text-slate-900">
            {costs ? costs.daily_cost.toLocaleString() : '-'} تومان
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {costs ? costs.daily_count : '-'} تماس انجام شده
          </div>
        </div>

        {/* Dialing Toggle Card */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100">
          <h3 className="text-sm text-slate-500 mb-2">وضعیت سیستم</h3>
          <div className="flex items-center gap-4 mt-3">
            <button
              type="button"
              role="switch"
              aria-checked={config?.enabled ?? false}
              disabled={saving || !!(billing && billing.wallet_balance <= 0)}
              onClick={toggleDialer}
              dir="ltr"
              className={`relative inline-flex h-7 w-14 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-50 disabled:cursor-not-allowed ${
                config?.enabled ? 'bg-emerald-500' : 'bg-slate-200'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ease-in-out ${
                  config?.enabled ? 'translate-x-7' : 'translate-x-0'
                }`}
              />
            </button>
            <span className={`text-sm font-semibold ${config?.enabled ? 'text-emerald-600' : 'text-red-600'}`}>
              {config?.enabled ? 'روشن' : 'خاموش'}
            </span>
          </div>
          {!config?.enabled && config?.disabled_by_dialer && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-2 py-1 mt-2">
              خاموش شده توسط سیستم
            </div>
          )}
          <div className="text-xs text-slate-500 mt-2">
            نسخه: {config?.version ?? '-'}
          </div>
        </div>
      </div>

      {/* Section 2: Statistics Table */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100">
        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          {/* Group By Toggle */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-700">گروه‌بندی:</span>
            <div className="flex gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={groupBy === 'scenario'}
                  onChange={() => setGroupBy('scenario')}
                  className="w-4 h-4"
                />
                <span className="text-sm">بر اساس سناریو</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={groupBy === 'line'}
                  onChange={() => setGroupBy('line')}
                  className="w-4 h-4"
                />
                <span className="text-sm">بر اساس خط</span>
              </label>
            </div>
          </div>

          {/* Time Filter */}
          <div className="flex gap-2">
            {[
              { key: '1h', label: 'ساعت گذشته' },
              { key: 'today', label: 'امروز' },
              { key: 'yesterday', label: 'دیروز' },
              { key: '7d', label: '7 روز' },
              { key: '30d', label: '30 روز' },
            ].map((item) => (
              <button
                key={item.key}
                className={`px-3 py-1 rounded text-sm ${
                  timeFilter === item.key
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
                onClick={() => setTimeFilter(item.key as TimeFilter)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Stats Table */}
        {loading ? (
          <div className="text-center py-8 text-slate-500">در حال بارگذاری...</div>
        ) : stats ? (
          <div className="overflow-x-auto">
            <table className="w-full text-base border-collapse">
              <thead>
                <tr className="bg-slate-50">
                  <th className="border border-slate-200 px-3 py-2 text-right font-semibold">
                    {groupBy === 'scenario' ? 'سناریو' : 'خط'}
                  </th>
                  {Object.entries(statusLabels)
                    .filter(([key]) => key !== 'IN_QUEUE')
                    .map(([key, label]) => (
                      <th key={key} className="border border-slate-200 px-3 py-2 text-center font-semibold">
                        {label}
                      </th>
                    ))}
                  <th className="border border-slate-200 px-3 py-2 text-center font-semibold bg-slate-100">
                    مجموع
                  </th>
                  <th className="border border-slate-200 px-3 py-2 text-center font-semibold bg-blue-50">
                    انجام شده
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.groups.map((group) => (
                  <tr key={group.id} className="hover:bg-slate-50">
                    <td className="border border-slate-200 px-3 py-2 font-medium">
                      {group.display_name || group.name}
                    </td>
                    {Object.keys(statusLabels)
                      .filter((key) => key !== 'IN_QUEUE')
                      .map((status) => {
                        const count = group.statuses[status] || 0
                        const percentage = group.total > 0 ? ((count / group.total) * 100).toFixed(1) : '0.0'
                        return (
                          <td key={status} className="border border-slate-200 px-3 py-2 text-center">
                            {count > 0 ? (
                              <>
                                {count.toLocaleString()}
                                <span className="text-sm text-slate-500 mr-1">({percentage}%)</span>
                              </>
                            ) : (
                              <span className="text-slate-300">-</span>
                            )}
                          </td>
                        )
                      })}
                    <td className="border border-slate-200 px-3 py-2 text-center font-semibold bg-slate-50">
                      {group.total.toLocaleString()}
                    </td>
                    <td className="border border-slate-200 px-3 py-2 text-center font-semibold bg-blue-50">
                      {group.billable.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 font-semibold">
                  <td className="border border-slate-200 px-3 py-2">مجموع کل</td>
                  {Object.keys(statusLabels)
                    .filter((key) => key !== 'IN_QUEUE')
                    .map((status) => (
                      <td key={status} className="border border-slate-200 px-3 py-2 text-center">
                        {(stats.totals[status] || 0).toLocaleString()}
                      </td>
                    ))}
                  <td className="border border-slate-200 px-3 py-2 text-center bg-slate-200">
                    {stats.totals.total.toLocaleString()}
                  </td>
                  <td className="border border-slate-200 px-3 py-2 text-center bg-blue-100">
                    {stats.totals.billable.toLocaleString()}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">داده‌ای برای نمایش وجود ندارد</div>
        )}

        {/* Footer Stats */}
        <div className="flex items-center justify-between gap-4 mt-6 pt-4 border-t border-slate-200 text-sm text-slate-600">
          <span>
            مجموع شماره‌ها: <strong className="text-slate-900">{numbersSummary?.total_numbers.toLocaleString() ?? '-'}</strong>
          </span>
          <span>
            در صف: <strong className="text-slate-900">{inQueueCount.toLocaleString()}</strong>
          </span>
        </div>
      </div>

      {/* Section 3: Trend Line Chart */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">روند وضعیت تماس‌ها</h3>
            <p className="text-sm text-slate-500">نمایش درصد سهم هر وضعیت ({trendModeLabel})</p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm items-center">
            <div className="flex items-center gap-1 bg-slate-100 rounded-full px-2 py-1 text-xs">
              {[
                { key: 'hour24', label: '۲۴س' },
                { key: 'day7', label: '۷روز' },
                { key: 'day14', label: '۱۴روز' },
                { key: 'day30', label: '۳۰روز' },
              ].map((item) => (
                <button
                  key={item.key}
                  className={`px-2 py-1 rounded-full text-xs transition-colors ${
                    trendMode === item.key ? 'bg-blue-500 text-white' : 'text-slate-700 hover:bg-slate-200'
                  }`}
                  onClick={() => setTrendMode(item.key as typeof trendMode)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            {Object.entries(statusLabels)
              .filter(([key]) => key !== 'IN_QUEUE')
              .map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 border border-slate-200 rounded-full px-3 py-1 cursor-pointer hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={selectedStatuses.includes(key)}
                    onChange={() => toggleStatusFilter(key)}
                    className="w-3 h-3"
                  />
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: statusColors[key] || '#cbd5e1' }}></span>
                    {label}
                  </span>
                </label>
              ))}
            {/* BILLABLE virtual status */}
            <label className="flex items-center gap-2 border border-blue-300 bg-blue-50 rounded-full px-3 py-1 cursor-pointer hover:bg-blue-100">
              <input
                type="checkbox"
                checked={selectedStatuses.includes('BILLABLE')}
                onChange={() => toggleStatusFilter('BILLABLE')}
                className="w-3 h-3"
              />
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: '#3b82f6' }}></span>
                انجام شده
              </span>
            </label>
          </div>
        </div>
        <div>
          {lineData && lineData.labels.length ? (
            <Line
              data={lineData}
              options={{
                responsive: true,
                plugins: {
                  legend: { position: 'bottom' },
                  tooltip: {
                    callbacks: {
                      title: (items) => {
                        if (!items.length) return ''
                        const idx = items[0].dataIndex
                        const bucket = trend?.buckets[idx]
                        if (!bucket) return ''
                        return trend?.granularity === 'hour'
                          ? dayjs(bucket.bucket).calendar('jalali').format('YYYY/MM/DD HH:mm')
                          : dayjs(bucket.bucket).calendar('jalali').format('YYYY/MM/DD')
                      },
                      label: (ctx) => {
                        const bucket = trend?.buckets[ctx.dataIndex]
                        const statusKey = (ctx.dataset as any).statusKey as string | undefined
                        const total = bucket?.total_attempts ?? 0

                        // Special handling for BILLABLE virtual status
                        if (statusKey === 'BILLABLE') {
                          const billableCount = BILLABLE_STATUSES.reduce((sum, billableStatus) => {
                            const match = bucket?.status_counts.find((s) => s.status === billableStatus)
                            return sum + (match ? match.count : 0)
                          }, 0)
                          return `${ctx.dataset.label}: ${ctx.parsed.y}% (${billableCount}/${total})`
                        }

                        const match = statusKey ? bucket?.status_counts.find((s) => s.status === statusKey) : undefined
                        const count = match?.count ?? 0
                        return `${ctx.dataset.label}: ${ctx.parsed.y}% (${count}/${total})`
                      },
                    },
                  },
                },
                scales: {
                  y: {
                    title: { display: true, text: 'درصد از کل تماس‌های این بازه' },
                    ticks: { callback: (value) => `${value}%` },
                    suggestedMin: 0,
                    suggestedMax: 100,
                  },
                },
              }}
            />
          ) : (
            <div className="text-sm text-slate-500 text-center py-8">داده‌ای برای نمایش نیست.</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DashboardPage

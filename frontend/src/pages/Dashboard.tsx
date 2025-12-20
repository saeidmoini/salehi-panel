import { useEffect, useMemo, useState } from 'react'
import client from '../api/client'
import dayjs from 'dayjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, PointElement, LineElement, CategoryScale, LinearScale, Filler } from 'chart.js'
import { Pie, Line } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend, PointElement, LineElement, CategoryScale, LinearScale, Filler)

interface ScheduleConfig {
  enabled: boolean
  version: number
}

interface StatusShare {
  status: string
  count: number
  percentage: number
}

interface NumbersSummary {
  total_numbers: number
  status_counts: StatusShare[]
}

interface DailyStatusBreakdown {
  day: string
  total_attempts: number
  status_counts: StatusShare[]
}

interface AttemptTrendResponse {
  days: DailyStatusBreakdown[]
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
  IN_QUEUE: '#f59e0b',
  MISSED: '#fb923c',
  CONNECTED: '#10b981',
  FAILED: '#ef4444',
  NOT_INTERESTED: '#94a3b8',
  HANGUP: '#a855f7',
  DISCONNECTED: '#6b7280',
}

const DashboardPage = () => {
  const [config, setConfig] = useState<ScheduleConfig | null>(null)
  const [loadingConfig, setLoadingConfig] = useState(false)
  const [saving, setSaving] = useState(false)
  const [numbersSummary, setNumbersSummary] = useState<NumbersSummary | null>(null)
  const [trend, setTrend] = useState<AttemptTrendResponse | null>(null)
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(Object.keys(statusLabels))

  const fetchConfig = async () => {
    setLoadingConfig(true)
    const { data } = await client.get<ScheduleConfig>('/api/schedule')
    setConfig(data)
    setLoadingConfig(false)
  }

  const fetchStats = async () => {
    const [numbersRes, trendRes] = await Promise.all([
      client.get<NumbersSummary>('/api/stats/numbers-summary'),
      client.get<AttemptTrendResponse>('/api/stats/attempt-trend', { params: { days: 14 } }),
    ])
    setNumbersSummary(numbersRes.data)
    setTrend(trendRes.data)
  }

  useEffect(() => {
    fetchConfig()
    fetchStats()
  }, [])

  const toggleDialer = async () => {
    if (!config) return
    setSaving(true)
    try {
      const { data } = await client.put('/api/schedule', { enabled: !config.enabled })
      setConfig((prev) => (prev ? { ...prev, enabled: data.enabled } : data))
    } finally {
      setSaving(false)
    }
  }

  const statusBadge = (on: boolean) => (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${on ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
      {on ? 'فعال' : 'غیرفعال'}
    </span>
  )

  const pieData = useMemo(() => {
    if (!numbersSummary) return null
    const sorted = [...numbersSummary.status_counts].sort((a, b) => (a.status > b.status ? 1 : -1))
    return {
      labels: sorted.map((s) => statusLabels[s.status] || s.status),
      datasets: [
        {
          data: sorted.map((s) => Number(s.percentage.toFixed(2))),
          backgroundColor: sorted.map((s) => statusColors[s.status] || '#94a3b8'),
          borderWidth: 1,
        },
      ],
    }
  }, [numbersSummary])

  const lineData = useMemo(() => {
    if (!trend) return null
    const labels = trend.days.map((d) => dayjs(d.day).calendar('jalali').format('YYYY/MM/DD'))
    const datasets = selectedStatuses.map((status) => {
      const color = statusColors[status] || '#0ea5e9'
      return {
        label: statusLabels[status] || status,
        data: trend.days.map((day) => {
          const match = day.status_counts.find((s) => s.status === status)
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

  const attemptedCount = useMemo(() => {
    if (!numbersSummary) return null
    const inQueue = numbersSummary.status_counts.find((s) => s.status === 'IN_QUEUE')?.count ?? 0
    const value = numbersSummary.total_numbers - inQueue
    return value < 0 ? 0 : value
  }, [numbersSummary])

  const toggleStatusFilter = (status: string) => {
    setSelectedStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-100 flex flex-col gap-3 md:col-span-3 lg:col-span-1">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500">مرکز تماس</div>
            {statusBadge(!!config?.enabled)}
          </div>
          <div className="text-sm text-slate-700">
            کنترل روشن/خاموش بودن سرور مرکز تماس. در صورت خاموش بودن هیچ شماره‌ای ارسال نمی‌شود.
          </div>
          <button
            className="rounded bg-brand-500 text-white px-4 py-2 text-sm disabled:opacity-50"
            onClick={toggleDialer}
            disabled={saving || loadingConfig}
          >
            {saving ? 'در حال اعمال...' : config?.enabled ? 'خاموش کردن' : 'روشن کردن'}
          </button>
          <div className="text-xs text-slate-500">نسخه زمان‌بندی: {config?.version ?? '-'}</div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-100 md:col-span-3 lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold">نمای کلی شماره‌ها</h3>
              <p className="text-sm text-slate-500">تعداد کل و توزیع وضعیت‌ها</p>
            </div>
            <div className="text-right space-y-1">
              <div className="text-sm font-semibold text-slate-700">
                مجموع: {numbersSummary?.total_numbers ?? '-'}
              </div>
              <div className="text-xs text-slate-600">
                کل تماس‌های انجام‌شده: {attemptedCount ?? '-'}
              </div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              {numbersSummary ? (
                numbersSummary.status_counts.map((s) => (
                  <div key={s.status} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: statusColors[s.status] || '#cbd5e1' }}></span>
                      <span className="text-sm text-slate-700">{statusLabels[s.status] || s.status}</span>
                    </div>
                    <div className="text-sm font-semibold text-slate-800">
                      {s.count}{' '}
                      <span className="text-xs text-slate-500">({s.percentage.toFixed(1)}%)</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-500">در حال بارگذاری...</div>
              )}
            </div>
            <div className="flex items-center justify-center">
              {pieData ? (
                <Pie
                  data={pieData}
                  options={{
                    plugins: {
                      legend: { position: 'bottom' },
                      tooltip: {
                        callbacks: {
                          label: (ctx) => {
                            const label = ctx.label || ''
                            const value = ctx.parsed
                            const count = numbersSummary?.status_counts[ctx.dataIndex]?.count ?? 0
                            return `${label}: ${value}% (${count})`
                          },
                        },
                      },
                    },
                  }}
                />
              ) : (
                <div className="text-sm text-slate-500">داده‌ای برای نمایش نیست.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-100 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">روند درصد وضعیت تماس‌ها (روزانه)</h3>
            <p className="text-sm text-slate-500">نمایش درصد سهم هر وضعیت در تماس‌های هر روز (تقویم شمسی)</p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            {Object.entries(statusLabels).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 border border-slate-200 rounded-full px-3 py-1">
                <input
                  type="checkbox"
                  checked={selectedStatuses.includes(key)}
                  onChange={() => toggleStatusFilter(key)}
                />
                <span className="flex items-center gap-1">
                  <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: statusColors[key] || '#cbd5e1' }}></span>
                  {label}
                </span>
              </label>
            ))}
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
                        const isoDate = trend?.days[idx]?.day
                        return isoDate ? dayjs(isoDate).calendar('jalali').format('YYYY/MM/DD') : ''
                      },
                      label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}%`,
                    },
                  },
                },
                scales: {
                  y: {
                    title: { display: true, text: 'درصد از کل تماس‌های روز' },
                    ticks: { callback: (value) => `${value}%` },
                    suggestedMin: 0,
                    suggestedMax: 100,
                  },
                },
              }}
            />
          ) : (
            <div className="text-sm text-slate-500">داده‌ای برای نمایش نیست.</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DashboardPage

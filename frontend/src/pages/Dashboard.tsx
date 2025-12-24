import { useEffect, useMemo, useState } from 'react'
import client from '../api/client'
import dayjs from 'dayjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, PointElement, LineElement, CategoryScale, LinearScale, Filler } from 'chart.js'
import { Pie, Line } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend, PointElement, LineElement, CategoryScale, LinearScale, Filler)

interface ScheduleConfig {
  enabled: boolean
  version: number
  disabled_by_dialer?: boolean
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

interface AttemptSummary {
  total_attempts: number
  status_counts: StatusShare[]
}

interface TimeBucketBreakdown {
  bucket: string
  total_attempts: number
  status_counts: StatusShare[]
}

interface AttemptTrendResponse {
  granularity: 'day' | 'hour'
  buckets: TimeBucketBreakdown[]
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
  const [attemptSummary, setAttemptSummary] = useState<AttemptSummary | null>(null)
  const [trend, setTrend] = useState<AttemptTrendResponse | null>(null)
  const filteredStatuses = useMemo(() => Object.keys(statusLabels).filter((s) => s !== 'IN_QUEUE'), [])
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(filteredStatuses)
  const [attemptMode, setAttemptMode] = useState<'all' | 'today' | '1h' | '3h' | '7d' | '30d'>('all')
  const [trendMode, setTrendMode] = useState<'hour6' | 'hour24' | 'day7' | 'day30'>('hour24')

  const fetchConfig = async () => {
    setLoadingConfig(true)
    const { data } = await client.get<ScheduleConfig>('/api/schedule')
    setConfig(data)
    setLoadingConfig(false)
  }

  const fetchNumbers = async () => {
    const { data } = await client.get<NumbersSummary>('/api/stats/numbers-summary')
    setNumbersSummary(data)
  }

  const fetchAttemptSummary = async (mode: typeof attemptMode) => {
    const params: Record<string, number | string> = {}
    if (mode === 'today') params.days = 1
    if (mode === '1h') params.hours = 1
    if (mode === '3h') params.hours = 3
    if (mode === '7d') params.days = 7
    if (mode === '30d') params.days = 30
    const { data } = await client.get<AttemptSummary>('/api/stats/attempts-summary', { params })
    setAttemptSummary(data)
  }

  const fetchTrend = async (mode: typeof trendMode) => {
    const params: Record<string, number | string> = {}
    if (mode === 'hour6') {
      params.granularity = 'hour'
      params.span = 6
    } else if (mode === 'hour24') {
      params.granularity = 'hour'
      params.span = 24
    } else if (mode === 'day7') {
      params.granularity = 'day'
      params.span = 7
    } else if (mode === 'day30') {
      params.granularity = 'day'
      params.span = 30
    }
    const { data } = await client.get<AttemptTrendResponse>('/api/stats/attempt-trend', { params })
    setTrend(data)
  }

  useEffect(() => {
    fetchConfig()
    fetchNumbers()
    fetchTrend(trendMode)
  }, [])

  useEffect(() => {
    fetchAttemptSummary(attemptMode)
  }, [attemptMode])

  useEffect(() => {
    fetchTrend(trendMode)
  }, [trendMode])

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

  const attemptedCount = useMemo(() => attemptSummary?.total_attempts ?? null, [attemptSummary])

  const inQueueCount = useMemo(() => {
    if (!numbersSummary) return null
    return numbersSummary.status_counts.find((s) => s.status === 'IN_QUEUE')?.count ?? 0
  }, [numbersSummary])

  const attemptedStatusCounts = useMemo(() => {
    if (!attemptSummary) return null
    const attemptTotal = attemptSummary.total_attempts
    const filtered = attemptSummary.status_counts.filter((s) => s.status !== 'IN_QUEUE')
    return filtered.map((s) => ({
      ...s,
      percentage: attemptTotal > 0 ? (s.count / attemptTotal) * 100 : 0,
    }))
  }, [attemptSummary])

  const pieData = useMemo(() => {
    if (!attemptedStatusCounts) return null
    const sorted = [...attemptedStatusCounts].sort((a, b) => (a.status > b.status ? 1 : -1))
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
  }, [attemptedStatusCounts])

  const lineData = useMemo(() => {
    if (!trend) return null
    const labels = trend.buckets.map((b) =>
      trend.granularity === 'hour'
        ? dayjs(b.bucket).calendar('jalali').format('YYYY/MM/DD HH:mm')
        : dayjs(b.bucket).calendar('jalali').format('YYYY/MM/DD')
    )
    const datasets = selectedStatuses.map((status) => {
      const color = statusColors[status] || '#0ea5e9'
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

  const attemptModeLabel =
    attemptMode === 'today'
      ? 'امروز'
      : attemptMode === '1h'
        ? '۱ ساعت گذشته'
        : attemptMode === '3h'
          ? '۳ ساعت گذشته'
          : attemptMode === '7d'
            ? '۷ روز گذشته'
            : attemptMode === '30d'
              ? '۳۰ روز گذشته'
              : 'کل'

  const trendModeLabel =
    trendMode === 'hour6'
      ? '۶ ساعت گذشته'
      : trendMode === 'hour24'
        ? '۲۴ ساعت گذشته'
        : trendMode === 'day7'
          ? '۷ روز گذشته'
          : '۳۰ روز گذشته'

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
          {!config?.enabled && config?.disabled_by_dialer && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-3 py-2">
              سیستم با خطا مواجه شد (خاموش توسط مرکز تماس)
            </div>
          )}
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
              <p className="text-sm text-slate-500">توذیع وضعیت‌ها (بر اساس تماس‌های گرفته‌شده)</p>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              {attemptedStatusCounts ? (
                attemptedStatusCounts.map((s) => (
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
              <div className="border border-slate-100 rounded-lg px-3 py-3 bg-slate-50">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-col text-sm text-slate-700 space-y-1">
                    <div>مجموع: <span className="font-semibold">{numbersSummary?.total_numbers ?? '-'}</span></div>
                    <div>تماس‌های انجام‌شده ({attemptModeLabel}): <span className="font-semibold">{attemptedCount ?? '-'}</span></div>
                    <div>در صف: <span className="font-semibold">{inQueueCount ?? '-'}</span></div>
                  </div>
                  <div className="flex flex-wrap items-center gap-1 bg-white border border-slate-200 rounded-full px-2 py-1 text-xs">
                    {[
                      { key: 'all', label: 'کل' },
                      { key: 'today', label: 'امروز' },
                      { key: '1h', label: '۱س' },
                      { key: '3h', label: '۳س' },
                      { key: '7d', label: '۷روز' },
                      { key: '30d', label: '۳۰روز' },
                    ].map((item) => (
                      <button
                        key={item.key}
                        className={`px-2 py-1 rounded-full text-xs ${attemptMode === item.key ? 'bg-brand-500 text-white' : 'text-slate-700'}`}
                        onClick={() => setAttemptMode(item.key as typeof attemptMode)}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
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
                            const count = attemptedStatusCounts?.[ctx.dataIndex]?.count ?? 0
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
            <h3 className="font-semibold">روند درصد وضعیت تماس‌ها</h3>
            <p className="text-sm text-slate-500">نمایش درصد سهم هر وضعیت در تماس‌های هر بازه ({trendModeLabel}، بدون در صف)</p>
          </div>
          <div className="flex flex-wrap gap-2 text-sm items-center">
            <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-full px-2 py-1 text-xs">
              {[
                { key: 'hour6', label: '۶س' },
                { key: 'hour24', label: '۲۴س' },
                { key: 'day7', label: '۷روز' },
                { key: 'day30', label: '۳۰روز' },
              ].map((item) => (
                <button
                  key={item.key}
                  className={`px-2 py-1 rounded-full text-xs ${trendMode === item.key ? 'bg-brand-500 text-white' : 'text-slate-700'}`}
                  onClick={() => setTrendMode(item.key as typeof trendMode)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            {Object.entries(statusLabels)
              .filter(([key]) => key !== 'IN_QUEUE')
              .map(([key, label]) => (
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
                    const bucket = trend?.buckets[idx]
                    if (!bucket) return ''
                    return trend?.granularity === 'hour'
                      ? dayjs(bucket.bucket).calendar('jalali').format('YYYY/MM/DD HH:mm')
                      : dayjs(bucket.bucket).calendar('jalali').format('YYYY/MM/DD')
                    },
                    label: (ctx) => {
                        const bucket = trend?.buckets[ctx.dataIndex]
                        const statusKey = (ctx.dataset as any).statusKey as string | undefined
                        const match = statusKey ? bucket?.status_counts.find((s) => s.status === statusKey) : undefined
                        const count = match?.count ?? 0
                        const total = bucket?.total_attempts ?? 0
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
            <div className="text-sm text-slate-500">داده‌ای برای نمایش نیست.</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DashboardPage

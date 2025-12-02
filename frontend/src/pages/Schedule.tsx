import { useEffect, useState } from 'react'
import client from '../api/client'

interface ScheduleInterval {
  day_of_week: number
  start_time: string
  end_time: string
}

interface ScheduleConfig {
  skip_holidays: boolean
  enabled: boolean
  version: number
  intervals: ScheduleInterval[]
}

const dayNames = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']

const SchedulePage = () => {
  const [config, setConfig] = useState<ScheduleConfig | null>(null)
  const [skipHolidays, setSkipHolidays] = useState(true)
  const [enabled, setEnabled] = useState(true)
  const [intervals, setIntervals] = useState<ScheduleInterval[]>([])
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const fetchConfig = async () => {
    const { data } = await client.get<ScheduleConfig>('/api/schedule')
    setConfig(data)
    setSkipHolidays(data.skip_holidays)
    setEnabled(data.enabled)
    setIntervals(data.intervals)
  }

  useEffect(() => {
    fetchConfig()
  }, [])

  const addInterval = () => {
    setIntervals([...intervals, { day_of_week: 0, start_time: '09:00', end_time: '18:00' }])
  }

  const updateInterval = (index: number, field: keyof ScheduleInterval, value: string | number) => {
    const next = [...intervals]
    next[index] = { ...next[index], [field]: value }
    setIntervals(next)
  }

  const removeInterval = (index: number) => {
    setIntervals(intervals.filter((_, i) => i !== index))
  }

  const save = async () => {
    setSaving(true)
    setSaveMessage(null)
    try {
      await client.put('/api/schedule', { skip_holidays: skipHolidays, enabled, intervals })
      setSaveMessage({ type: 'success', text: 'تغییرات ذخیره شد' })
      fetchConfig()
    } catch (e) {
      setSaveMessage({ type: 'error', text: 'خطا در ذخیره تغییرات' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold">تنظیمات زمان‌بندی تماس</h2>
            <p className="text-sm text-slate-500">بازه‌های زمانی بر اساس منطقه زمانی تهران</p>
          </div>
          <div className="text-xs text-slate-500">نسخه زمان‌بندی: {config?.version ?? '-'}</div>
        </div>
      </div>

      <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm space-y-3">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={skipHolidays} onChange={(e) => setSkipHolidays(e.target.checked)} />
          عدم تماس در تعطیلات رسمی
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          فعال بودن تماس‌ها (غیرفعال شود تا هیچ شماره‌ای به سرور تماس ارسال نشود)
        </label>

        <div className="flex justify-between items-center">
          <h3 className="font-semibold">بازه‌های زمانی مجاز</h3>
          <button className="rounded bg-brand-500 text-white px-3 py-1 text-sm" onClick={addInterval}>
            افزودن بازه
          </button>
        </div>

        <div className="space-y-2">
          {intervals.map((interval, idx) => (
            <div key={idx} className="flex flex-wrap items-center gap-2 bg-slate-50 p-3 rounded">
              <select
                className="rounded border border-slate-200 px-2 py-1 text-sm"
                value={interval.day_of_week}
                onChange={(e) => updateInterval(idx, 'day_of_week', Number(e.target.value))}
              >
                {dayNames.map((name, index) => (
                  <option key={index} value={index}>
                    {name}
                  </option>
                ))}
              </select>
              <input
                type="time"
                value={interval.start_time}
                onChange={(e) => updateInterval(idx, 'start_time', e.target.value)}
                className="rounded border border-slate-200 px-2 py-1 text-sm"
              />
              <span className="text-slate-500">تا</span>
              <input
                type="time"
                value={interval.end_time}
                onChange={(e) => updateInterval(idx, 'end_time', e.target.value)}
                className="rounded border border-slate-200 px-2 py-1 text-sm"
              />
              <button className="text-xs text-red-600" onClick={() => removeInterval(idx)}>
                حذف
              </button>
            </div>
          ))}
          {!intervals.length && <div className="text-sm text-slate-500">بازه‌ای تعریف نشده است.</div>}
        </div>

        <button onClick={save} className="rounded bg-slate-900 text-white px-4 py-2 text-sm">
          {saving ? 'در حال ذخیره...' : 'ذخیره تغییرات'}
        </button>
        {saveMessage && (
          <div
            className={`text-sm mt-2 ${saveMessage.type === 'success' ? 'text-emerald-700' : 'text-red-600'}`}
          >
            {saveMessage.text}
          </div>
        )}
      </div>
    </div>
  )
}

export default SchedulePage

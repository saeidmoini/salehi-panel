import { FormEvent, useEffect, useMemo, useState } from 'react'
import client from '../api/client'
import dayjs from 'dayjs'
import { useAuth } from '../hooks/useAuth'
import DatePicker from 'react-multi-date-picker'
import persian from 'react-date-object/calendars/persian'
import persian_fa from 'react-date-object/locales/persian_fa'
import gregorian from 'react-date-object/calendars/gregorian'

interface PhoneNumber {
  id: number
  phone_number: string
  status: string
  total_attempts: number
  last_attempt_at?: string
  last_status_change_at?: string
  last_user_message?: string | null
  assigned_agent_id?: number | null
  assigned_agent?: {
    id: number
    username: string
    first_name?: string | null
    last_name?: string | null
    phone_number?: string | null
  } | null
}

const statusLabels: Record<string, string> = {
  IN_QUEUE: 'در صف تماس',
  MISSED: 'از دست رفته',
  CONNECTED: 'موفق',
  FAILED: 'خطا',
  NOT_INTERESTED: 'عدم نیاز کاربر',
  HANGUP: 'قطع تماس توسط کاربر',
  DISCONNECTED: 'ناموفق',
  BUSY: 'مشغول',
  POWER_OFF: 'خاموش',
  BANNED: 'بن شده',
  UNKNOWN: 'نامشخص',
}

const statusColors: Record<string, string> = {
  IN_QUEUE: 'bg-amber-100 text-amber-800',
  MISSED: 'bg-orange-100 text-orange-800',
  CONNECTED: 'bg-emerald-100 text-emerald-800',
  FAILED: 'bg-red-100 text-red-800',
  NOT_INTERESTED: 'bg-slate-200 text-slate-800',
  HANGUP: 'bg-purple-100 text-purple-800',
  DISCONNECTED: 'bg-gray-200 text-gray-800',
  BUSY: 'bg-yellow-100 text-yellow-800',
  POWER_OFF: 'bg-slate-100 text-slate-700',
  BANNED: 'bg-rose-100 text-rose-700',
  UNKNOWN: 'bg-blue-100 text-blue-800',
}

const modifiableStatuses = ['IN_QUEUE', 'MISSED', 'BUSY', 'POWER_OFF', 'BANNED']

const NumbersPage = () => {
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'
  const isSuper = !!user?.is_superuser
  const [numbers, setNumbers] = useState<PhoneNumber[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [startDateValue, setStartDateValue] = useState<any>(null)
  const [endDateValue, setEndDateValue] = useState<any>(null)
  const [startDateIso, setStartDateIso] = useState<string | undefined>(undefined)
  const [endDateIso, setEndDateIso] = useState<string | undefined>(undefined)
  const [newNumbers, setNewNumbers] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const pageSize = 50
  const [hasMore, setHasMore] = useState(false)
  const [totalCount, setTotalCount] = useState(0)

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set())
  const [selectAll, setSelectAll] = useState(false)

  const [bulkAction, setBulkAction] = useState<'update_status' | 'reset' | 'delete'>('update_status')
  const [bulkStatus, setBulkStatus] = useState<string>('IN_QUEUE')
  const [sortBy, setSortBy] = useState<'created_at' | 'last_attempt_at' | 'status'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [exporting, setExporting] = useState(false)

  const canModifyStatus = (status: string) => isSuper || modifiableStatuses.includes(status)
  const isRowSelectable = (n: PhoneNumber) => canModifyStatus(n.status)
  const handleStartDateChange = (value: any) => {
    if (!value) {
      setStartDateValue(null)
      setStartDateIso(undefined)
      setPage(0)
      clearSelection()
      return
    }
    const dateObj = Array.isArray(value) ? value[0] : value
    setStartDateValue(dateObj)
    setStartDateIso(dateObj.convert(gregorian).format('YYYY-MM-DD'))
    setPage(0)
    clearSelection()
  }

  const handleEndDateChange = (value: any) => {
    if (!value) {
      setEndDateValue(null)
      setEndDateIso(undefined)
      setPage(0)
      clearSelection()
      return
    }
    const dateObj = Array.isArray(value) ? value[0] : value
    setEndDateValue(dateObj)
    setEndDateIso(dateObj.convert(gregorian).format('YYYY-MM-DD'))
    setPage(0)
    clearSelection()
  }

  const fetchNumbers = async () => {
    setLoading(true)
    const { data } = await client.get<PhoneNumber[]>('/api/numbers', {
      params: {
        status: statusFilter || undefined,
        search: search || undefined,
        start_date: startDateIso,
        end_date: endDateIso,
        skip: page * pageSize,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      },
    })
    setNumbers(data)
    setHasMore(data.length === pageSize)
    setLoading(false)
  }

  const fetchStats = async () => {
    const { data } = await client.get<{ total: number }>('/api/numbers/stats', {
      params: {
        status: statusFilter || undefined,
        search: search || undefined,
        start_date: startDateIso,
        end_date: endDateIso,
      },
    })
    setTotalCount(data.total)
  }

  useEffect(() => {
    fetchNumbers()
    fetchStats()
  }, [page, statusFilter, search, sortBy, sortOrder, startDateIso, endDateIso])

  const clearSelection = () => {
    setSelectedIds(new Set())
    setExcludedIds(new Set())
    setSelectAll(false)
  }

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    if (!isAdmin) return
    const phone_numbers = newNumbers.split(/\n|,/).map((s) => s.trim()).filter(Boolean)
    if (!phone_numbers.length) return
    await client.post('/api/numbers', { phone_numbers })
    setNewNumbers('')
    fetchNumbers()
    fetchStats()
  }

  const updateStatus = async (id: number, status: string) => {
    const target = numbers.find((n) => n.id === id)
    if (target && !canModifyStatus(target.status)) return
    await client.put(`/api/numbers/${id}/status`, { status })
    fetchNumbers()
  }

  const deleteNumber = async (id: number) => {
    const target = numbers.find((n) => n.id === id)
    if (target && !canModifyStatus(target.status)) return
    const ok = window.confirm('این شماره حذف شود؟')
    if (!ok) return
    await client.delete(`/api/numbers/${id}`)
    setNumbers((prev) => prev.filter((n) => n.id !== id))
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
    setExcludedIds((prev) => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
    fetchStats()
  }

  const resetNumber = async (id: number) => {
    const target = numbers.find((n) => n.id === id)
    if (target && !canModifyStatus(target.status)) return
    await client.post(`/api/numbers/${id}/reset`)
    fetchNumbers()
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!isAdmin) return
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

  const isRowSelected = (id: number) => {
    if (selectAll) {
      return !excludedIds.has(id)
    }
    return selectedIds.has(id)
  }

  const toggleRow = (id: number) => {
    const target = numbers.find((n) => n.id === id)
    if (target && !isRowSelectable(target)) return
    if (selectAll) {
      const next = new Set(excludedIds)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      setExcludedIds(next)
    } else {
      const next = new Set(selectedIds)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      setSelectedIds(next)
    }
  }

  const allVisibleSelected = useMemo(
    () => {
      const selectable = numbers.filter(isRowSelectable)
      return selectable.length > 0 && selectable.every((n) => isRowSelected(n.id))
    },
    [numbers, selectedIds, excludedIds, selectAll],
  )

  const toggleCurrentPage = () => {
    if (selectAll) {
      const next = new Set(excludedIds)
      numbers.forEach((n) => {
        if (!isRowSelectable(n)) return
        if (allVisibleSelected) {
          next.add(n.id)
        } else {
          next.delete(n.id)
        }
      })
      setExcludedIds(next)
    } else {
      const next = new Set(selectedIds)
      numbers.forEach((n) => {
        if (!isRowSelectable(n)) return
        if (allVisibleSelected) {
          next.delete(n.id)
        } else {
          next.add(n.id)
        }
      })
      setSelectedIds(next)
    }
  }

  const handleBulk = async () => {
    const ids = selectAll ? [] : Array.from(selectedIds)
    const excluded_ids = selectAll ? Array.from(excludedIds) : []
    if (!selectAll && ids.length === 0) {
      alert('هیچ ردیفی انتخاب نشده است')
      return
    }
    if (selectAll && !statusFilter && !isSuper) {
      alert('برای عملیات انتخاب همه، لطفا وضعیت قابل تغییر را فیلتر کنید (در صف/از دست رفته/مشغول/خاموش/بن‌شده)')
      return
    }
    if (!selectAll) {
      const selectedRows = numbers.filter((n) => selectedIds.has(n.id))
      const invalid = selectedRows.filter((n) => !isRowSelectable(n))
      if (invalid.length) {
        alert('فقط وضعیت‌های در صف/از دست رفته/مشغول/خاموش/بن‌شده قابل تغییر یا حذف هستند')
        return
      }
    } else if (statusFilter && !modifiableStatuses.includes(statusFilter) && !isSuper) {
      alert('برای انتخاب همه، فیلتر وضعیت را روی یک وضعیت قابل تغییر بگذارید')
      return
    }
    if (bulkAction === 'delete') {
      const ok = window.confirm('حذف دسته‌جمعی انجام شود؟')
      if (!ok) return
    }
    const payload: any = {
      action: bulkAction,
      ids,
      select_all: selectAll,
      excluded_ids,
      filter_status: statusFilter || undefined,
      search: search || undefined,
      start_date: startDateIso,
      end_date: endDateIso,
      sort_by: sortBy,
      sort_order: sortOrder,
    }
    if (bulkAction === 'update_status') {
      payload.status = bulkStatus
    }
    await client.post('/api/numbers/bulk', payload)
    clearSelection()
    fetchNumbers()
    fetchStats()
  }

  const handleExport = async () => {
    const ids = selectAll ? [] : Array.from(selectedIds)
    const excluded_ids = selectAll ? Array.from(excludedIds) : []
    if (!selectAll && ids.length === 0) {
      alert('برای خروجی گرفتن، ردیفی انتخاب کنید یا انتخاب همه را بزنید')
      return
    }
    setExporting(true)
    try {
      const payload: any = {
        ids,
        select_all: selectAll,
        excluded_ids,
        filter_status: statusFilter || undefined,
        search: search || undefined,
        start_date: startDateIso,
        end_date: endDateIso,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      const response = await client.post('/api/numbers/export', payload, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'numbers.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('خطا در دریافت خروجی اکسل')
    } finally {
      setExporting(false)
    }
  }

  const selectedCount = selectAll ? totalCount - excludedIds.size : selectedIds.size
  const canBulk = selectAll ? totalCount > excludedIds.size : selectedIds.size > 0
  const canExport = canBulk || selectAll

  const handleSort = (field: 'last_attempt_at' | 'status') => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  return (
    <div className="space-y-6 px-2 md:px-0 max-w-full w-full min-w-0">
      {isAdmin && (
        <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm w-full min-w-0">
          <h2 className="font-semibold mb-3">افزودن شماره جدید</h2>
          <div className="flex flex-col gap-6">
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
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm w-full min-w-0">
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <select
            className="rounded border border-slate-200 px-2 py-1 text-sm"
            value={statusFilter}
            onChange={(e) => {
              setPage(0)
              clearSelection()
              setStatusFilter(e.target.value)
            }}
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
            onChange={(e) => {
              setPage(0)
              clearSelection()
              setSearch(e.target.value)
            }}
            placeholder="جستجوی شماره یا کارشناس"
            className="rounded border border-slate-200 px-2 py-1 text-sm"
          />
          <DatePicker
            value={startDateValue}
            onChange={handleStartDateChange}
            calendar={persian}
            locale={persian_fa}
            calendarPosition="bottom-right"
            format="YYYY/MM/DD"
            placeholder="از تاریخ"
            inputClass="rounded border border-slate-200 px-2 py-1 text-sm w-[140px] text-right"
          />
          <DatePicker
            value={endDateValue}
            onChange={handleEndDateChange}
            calendar={persian}
            locale={persian_fa}
            calendarPosition="bottom-right"
            format="YYYY/MM/DD"
            placeholder="تا تاریخ"
            inputClass="rounded border border-slate-200 px-2 py-1 text-sm w-[140px] text-right"
          />
          <button onClick={() => { setPage(0); fetchNumbers(); fetchStats(); }} className="rounded bg-slate-900 text-white px-3 py-1 text-sm">
            بروزرسانی
          </button>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span>انتخاب شده: {selectedCount}</span>
            <button
              className="rounded border border-slate-200 px-2 py-1 text-[11px]"
              onClick={() => {
                setSelectAll(true)
                setSelectedIds(new Set())
                setExcludedIds(new Set())
              }}
              disabled={totalCount === 0}
            >
              انتخاب همه نتایج
            </button>
            <button
              className="rounded border border-slate-200 px-2 py-1 text-[11px]"
              onClick={clearSelection}
              disabled={selectedCount === 0 && !selectAll}
            >
              لغو انتخاب
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <div className="flex flex-wrap items-center gap-2 w-full">
            <label className="text-xs text-slate-600 whitespace-nowrap">عملیات گروهی</label>
            <select
              className="rounded border border-slate-200 px-2 py-1 text-sm w-full sm:w-auto"
              value={bulkAction}
              onChange={(e) => setBulkAction(e.target.value as any)}
            >
              <option value="update_status">تغییر وضعیت</option>
              <option value="reset">ریست (برگشت به صف)</option>
              <option value="delete">حذف</option>
            </select>
            {bulkAction === 'update_status' && (
              <select
                className="rounded border border-slate-200 px-2 py-1 text-sm w-full sm:w-auto"
                value={bulkStatus}
                onChange={(e) => setBulkStatus(e.target.value)}
              >
                {Object.entries(statusLabels).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            )}
            <button
              className="rounded bg-brand-500 text-white px-3 py-1 text-sm disabled:opacity-50 w-full sm:w-auto"
              disabled={!canBulk}
              onClick={handleBulk}
            >
              اعمال
            </button>
            <button
              className="rounded border border-slate-200 px-3 py-1 text-sm disabled:opacity-50 w-full sm:w-auto"
              disabled={!canExport || exporting}
              onClick={handleExport}
            >
              {exporting ? 'در حال آماده‌سازی...' : 'خروجی اکسل'}
            </button>
            <div className="text-[11px] text-slate-500 w-full">
              عملیات فقط روی وضعیت‌های در صف، از دست رفته، مشغول، خاموش و بن‌شده انجام می‌شود.
            </div>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-slate-600">صفحه {page + 1}</span>
            <button
              className="text-xs rounded border border-slate-200 px-2 py-1 disabled:opacity-50"
              onClick={() => setPage((p) => Math.max(p - 1, 0))}
              disabled={page === 0}
            >
              قبلی
            </button>
            <button
              className="text-xs rounded border border-slate-200 px-2 py-1 disabled:opacity-50"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
            >
              بعدی
            </button>
          </div>
        </div>
        {loading ? (
          <div className="text-sm">در حال بارگذاری...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto text-sm text-right">
              <thead>
                <tr className="text-slate-500">
                  <th className="py-2 text-right w-10 whitespace-nowrap">
                    <input type="checkbox" checked={allVisibleSelected} onChange={toggleCurrentPage} />
                  </th>
                  <th className="py-2 text-right whitespace-nowrap">شماره</th>
                  <th className="text-right cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('status')}>
                    وضعیت {sortBy === 'status' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="text-right whitespace-nowrap">تعداد تلاش</th>
                  <th className="text-right w-32 cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('last_attempt_at')}>
                    آخرین تلاش {sortBy === 'last_attempt_at' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="text-right w-36 whitespace-nowrap">کارشناس</th>
                  <th className="text-right min-w-[220px] max-w-[520px]">پیام تماس</th>
                  <th className="text-right w-52 whitespace-nowrap">اقدامات</th>
                </tr>
              </thead>
              <tbody>
                {numbers.map((n) => (
                  <tr key={n.id} className="border-t">
                    <td className="py-2 text-right">
                      <input
                        type="checkbox"
                        checked={isRowSelectable(n) && isRowSelected(n.id)}
                        onChange={() => toggleRow(n.id)}
                        disabled={!isRowSelectable(n)}
                        title={!isRowSelectable(n) && !isSuper ? 'این وضعیت قابل تغییر یا حذف نیست' : ''}
                      />
                    </td>
                    <td className="py-2 font-mono text-xs whitespace-nowrap">{n.phone_number}</td>
                    <td className="text-right whitespace-nowrap">
                      <span
                        className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${statusColors[n.status] || 'bg-slate-100 text-slate-700'}`}
                      >
                        {statusLabels[n.status] || n.status}
                      </span>
                    </td>
                    <td className="text-right whitespace-nowrap">{n.total_attempts}</td>
                    <td className="text-right whitespace-nowrap">
                      {n.last_attempt_at ? dayjs(n.last_attempt_at).calendar('jalali').format('YYYY/MM/DD HH:mm') : '-'}
                    </td>
                    <td className="text-right whitespace-nowrap">
                      {n.assigned_agent ? (
                        <div className="space-y-0.5">
                          <div className="text-sm">
                            {`${(n.assigned_agent.first_name || '')} ${(n.assigned_agent.last_name || '')}`.trim() ||
                              n.assigned_agent.username}
                          </div>
                          {n.assigned_agent.phone_number && (
                            <div className="text-xs text-slate-500 font-mono">{n.assigned_agent.phone_number}</div>
                          )}
                        </div>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="text-right align-top">
                      <div className="text-xs text-slate-700 whitespace-pre-line break-words max-w-[520px]">
                        {n.last_user_message || '—'}
                      </div>
                    </td>
                    <td className="text-right w-52 whitespace-nowrap">
                      <div className="flex items-center justify-start gap-2">
                        <select
                          className="rounded border border-slate-200 px-2 py-1 text-xs w-28"
                          value={n.status}
                          onChange={(e) => updateStatus(n.id, e.target.value)}
                          disabled={!canModifyStatus(n.status)}
                        >
                          {Object.keys(statusLabels).map((key) => (
                            <option key={key} value={key}>
                              {statusLabels[key]}
                            </option>
                          ))}
                        </select>
                        <button
                          className="text-xs text-amber-700 ml-2"
                          onClick={() => resetNumber(n.id)}
                          title="بازگشت به صف"
                          disabled={!canModifyStatus(n.status)}
                        >
                          ریست
                        </button>
                        <button
                          className="text-xs text-red-600"
                          onClick={() => deleteNumber(n.id)}
                          title="حذف شماره"
                          disabled={!canModifyStatus(n.status)}
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

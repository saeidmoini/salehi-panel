import { FormEvent, useEffect, useState } from 'react'
import dayjs from 'dayjs'
import DatePicker from 'react-multi-date-picker'
import persian from 'react-date-object/calendars/persian'
import persian_fa from 'react-date-object/locales/persian_fa'
import { useCompany } from '../hooks/useCompany'
import { useAuth } from '../hooks/useAuth'
import client from '../api/client'

interface BillingInfo {
  wallet_balance: number
  cost_per_connected: number
  currency: string
  disabled_by_dialer?: boolean
}

interface WalletTransaction {
  id: number
  amount_toman: number
  balance_after: number
  source: string
  note?: string | null
  transaction_at: string
  created_at: string
  created_by_username?: string | null
}

interface WalletTransactionList {
  items: WalletTransaction[]
  total: number
}

const BillingPage = () => {
  const { user } = useAuth()
  const { company } = useCompany()
  const [data, setData] = useState<BillingInfo | null>(null)
  const [wallet, setWallet] = useState<number | ''>('') // direct set (superuser only)
  const [rate, setRate] = useState<number | ''>('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [txMessage, setTxMessage] = useState<string | null>(null)

  const [manualAmount, setManualAmount] = useState<number | ''>('')
  const [manualOperation, setManualOperation] = useState<'ADD' | 'SUBTRACT'>('ADD')
  const [manualNote, setManualNote] = useState('')
  const [manualLoading, setManualLoading] = useState(false)

  const [matchAmount, setMatchAmount] = useState<number | ''>('')
  const [matchDate, setMatchDate] = useState<any>(null)
  const [matchHour, setMatchHour] = useState('')
  const [matchMinute, setMatchMinute] = useState('')
  const [matchLoading, setMatchLoading] = useState(false)

  const [fromDate, setFromDate] = useState<any>(null)
  const [toDate, setToDate] = useState<any>(null)
  const [transactions, setTransactions] = useState<WalletTransaction[]>([])
  const [txTotal, setTxTotal] = useState(0)

  const isSuperuser = !!user?.is_superuser

  const sourceLabels: Record<string, string> = {
    MANUAL_ADJUST: 'تراکنش دستی',
    BANK_MATCH: 'شارژ بانکی',
  }

  const fetchInfo = async () => {
    if (!company) return
    const { data } = await client.get<BillingInfo>(`/api/${company.name}/billing`)
    setData(data)
    setWallet(data.wallet_balance)
    setRate(data.cost_per_connected)
  }

  useEffect(() => {
    if (company) {
      fetchInfo()
      fetchTransactions()
    }
  }, [company])

  const fetchTransactions = async () => {
    if (!company) return
    const params: Record<string, string> = {}
    if (fromDate) params.from_jalali = fromDate.format('YYYY/MM/DD')
    if (toDate) params.to_jalali = toDate.format('YYYY/MM/DD')
    const { data } = await client.get<WalletTransactionList>(`/api/${company.name}/billing/transactions`, { params })
    setTransactions(data.items)
    setTxTotal(data.total)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!company) return
    setSaving(true)
    setMessage(null)
    await client.put(`/api/${company.name}/billing`, {
      wallet_balance: wallet === '' ? undefined : wallet,
      cost_per_connected: rate === '' ? undefined : rate,
    })
    setMessage('Saved')
    fetchInfo()
    setSaving(false)
  }

  const handleManualAdjust = async (e: FormEvent) => {
    e.preventDefault()
    if (!company || manualAmount === '' || manualAmount <= 0) return
    setManualLoading(true)
    setTxMessage(null)
    try {
      await client.post(`/api/${company.name}/billing/manual-adjust`, {
        amount_toman: manualAmount,
        operation: manualOperation,
        note: manualNote || undefined,
      })
      setManualAmount('')
      setManualNote('')
      setTxMessage('تراکنش دستی ثبت شد')
      await fetchInfo()
      await fetchTransactions()
    } finally {
      setManualLoading(false)
    }
  }

  const handleTopupMatch = async (e: FormEvent) => {
    e.preventDefault()
    if (!company || !matchDate || matchAmount === '') return
    const hour = Number(matchHour)
    const minute = Number(matchMinute)
    if (!Number.isInteger(hour) || hour < 0 || hour > 23) return
    if (!Number.isInteger(minute) || minute < 0 || minute > 59) return

    setMatchLoading(true)
    setTxMessage(null)
    try {
      await client.post(`/api/${company.name}/billing/topup-match`, {
        amount_toman: matchAmount,
        jalali_date: matchDate.format('YYYY/MM/DD'),
        hour,
        minute,
      })
      setTxMessage('شارژ کیف پول انجام شد')
      setMatchAmount('')
      setMatchDate(null)
      setMatchHour('')
      setMatchMinute('')
      await fetchInfo()
      await fetchTransactions()
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      setTxMessage(detail === 'Matching bank transaction not found' ? 'تراکنش بانکی مطابق پیدا نشد' : 'خطا در شارژ کیف پول')
    } finally {
      setMatchLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">تنظیمات هزینه و کیف پول</h1>
      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm space-y-4">
        {isSuperuser && (
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-slate-600">هزینه پیش‌فرض هر تماس برقرار شده ({data?.currency || 'تومان'})</label>
              <input
                type="number"
                className="rounded border border-slate-200 px-3 py-2 text-sm"
                value={rate}
                onChange={(e) => setRate(e.target.value === '' ? '' : Number(e.target.value))}
                min={0}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-slate-600">موجودی کیف پول ({data?.currency || 'تومان'})</label>
              <input
                type="number"
                className="rounded border border-slate-200 px-3 py-2 text-sm"
                value={wallet}
                onChange={(e) => setWallet(e.target.value === '' ? '' : Number(e.target.value))}
              />
              <p className="text-xs text-slate-500">در صورت صفر شدن موجودی، سیستم خودکار خاموش می‌شود.</p>
            </div>
            <button
              type="submit"
              className="rounded bg-brand-500 text-white px-4 py-2 text-sm disabled:opacity-50"
              disabled={saving}
            >
              {saving ? 'در حال ذخیره...' : 'ذخیره تنظیمات'}
            </button>
            {message && <div className="text-xs text-emerald-600">{message}</div>}
          </form>
        )}

        {data && (
          <div className="text-sm text-slate-700 space-y-1 border-t border-slate-100 pt-4">
            <div>موجودی فعلی: {data.wallet_balance.toLocaleString()} {data.currency}</div>
            <div>هزینه پیش‌فرض هر تماس: {data.cost_per_connected.toLocaleString()} {data.currency}</div>
            {data.disabled_by_dialer && <div className="text-amber-700">به دلیل اتمام موجودی، تماس‌گیری غیرفعال شده است.</div>}
          </div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
          <h2 className="font-semibold mb-3">ثبت درخواست شارژ بانکی</h2>
          <form className="grid gap-3" onSubmit={handleTopupMatch}>
            <div>
              <label className="text-sm text-slate-600">مبلغ (تومان)</label>
              <input
                type="number"
                min={1}
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                value={matchAmount}
                onChange={(e) => setMatchAmount(e.target.value === '' ? '' : Number(e.target.value))}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2" dir="ltr">
              <div>
                <label className="text-sm text-slate-600 block mb-1 text-right">تاریخ تراکنش (شمسی)</label>
                <DatePicker
                  value={matchDate}
                  onChange={setMatchDate}
                  calendar={persian}
                  locale={persian_fa}
                  format="YYYY/MM/DD"
                  editable={false}
                  calendarPosition="bottom-right"
                  inputClass="w-full rounded border border-slate-200 px-3 py-2 text-sm text-right"
                />
              </div>
              <div>
                <label className="text-sm text-slate-600 text-right block">ساعت</label>
                <input
                  type="number"
                  min={0}
                  max={23}
                  className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                  value={matchHour}
                  onChange={(e) => setMatchHour(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm text-slate-600 text-right block">دقیقه</label>
                <input
                  type="number"
                  min={0}
                  max={59}
                  className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                  value={matchMinute}
                  onChange={(e) => setMatchMinute(e.target.value)}
                />
              </div>
            </div>
            <button
              type="submit"
              className="rounded bg-brand-500 text-white px-4 py-2 text-sm disabled:opacity-50"
              disabled={matchLoading}
            >
              {matchLoading ? 'در حال بررسی...' : 'افزایش موجودی'}
            </button>
          </form>
        </div>

        {isSuperuser && (
          <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
            <h2 className="font-semibold mb-3">تغییر دستی موجودی (سوپر ادمین)</h2>
            <form className="grid gap-3" onSubmit={handleManualAdjust}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-sm text-slate-600">مبلغ (تومان)</label>
                  <input
                    type="number"
                    min={1}
                    className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                    value={manualAmount}
                    onChange={(e) => setManualAmount(e.target.value === '' ? '' : Number(e.target.value))}
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-600 block mb-1">نوع عملیات</label>
                  <div className="inline-flex rounded border border-slate-200 overflow-hidden">
                    <button
                      type="button"
                      className={`px-3 py-2 text-sm ${manualOperation === 'ADD' ? 'bg-emerald-600 text-white' : 'bg-white text-slate-700'}`}
                      onClick={() => setManualOperation('ADD')}
                    >
                      +
                    </button>
                    <button
                      type="button"
                      className={`px-3 py-2 text-sm ${manualOperation === 'SUBTRACT' ? 'bg-red-600 text-white' : 'bg-white text-slate-700'}`}
                      onClick={() => setManualOperation('SUBTRACT')}
                    >
                      -
                    </button>
                  </div>
                </div>
              </div>
              <div>
                <label className="text-sm text-slate-600">توضیح (اختیاری)</label>
                <input
                  className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                  value={manualNote}
                  onChange={(e) => setManualNote(e.target.value)}
                />
              </div>
              <button
                type="submit"
                className="rounded bg-slate-900 text-white px-4 py-2 text-sm disabled:opacity-50"
                disabled={manualLoading}
              >
                {manualLoading ? 'در حال ثبت...' : 'ثبت تراکنش دستی'}
              </button>
            </form>
          </div>
        )}
      </div>

      {txMessage && <div className="text-sm text-emerald-700">{txMessage}</div>}

      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <DatePicker
            value={fromDate}
            onChange={setFromDate}
            calendar={persian}
            locale={persian_fa}
            format="YYYY/MM/DD"
            editable={false}
            placeholder="از تاریخ"
            calendarPosition="bottom-right"
            inputClass="rounded border border-slate-200 px-3 py-2 text-sm w-[140px] text-right"
          />
          <DatePicker
            value={toDate}
            onChange={setToDate}
            calendar={persian}
            locale={persian_fa}
            format="YYYY/MM/DD"
            editable={false}
            placeholder="تا تاریخ"
            calendarPosition="bottom-right"
            inputClass="rounded border border-slate-200 px-3 py-2 text-sm w-[140px] text-right"
          />
          <button className="rounded border border-slate-300 px-3 py-2 text-sm" onClick={fetchTransactions}>
            فیلتر
          </button>
          <span className="text-xs text-slate-500">تعداد: {txTotal}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr className="text-right">
                <th className="py-2 px-3 whitespace-nowrap">تاریخ تراکنش</th>
                <th className="py-2 px-3 whitespace-nowrap">نوع</th>
                <th className="py-2 px-3 whitespace-nowrap">مبلغ</th>
                <th className="py-2 px-3 whitespace-nowrap">موجودی بعد از تراکنش</th>
                <th className="py-2 px-3 whitespace-nowrap">ثبت کننده</th>
                <th className="py-2 px-3 whitespace-nowrap">توضیح</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id} className="border-t border-slate-100">
                  <td className="py-2 px-3 whitespace-nowrap">
                    {dayjs(tx.transaction_at).calendar('jalali').format('YYYY/MM/DD HH:mm')}
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap">{sourceLabels[tx.source] || tx.source}</td>
                  <td className={`py-2 px-3 whitespace-nowrap font-mono ${tx.amount_toman >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                    {tx.amount_toman >= 0 ? '+' : ''}{tx.amount_toman.toLocaleString()}
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap font-mono">{tx.balance_after.toLocaleString()}</td>
                  <td className="py-2 px-3 whitespace-nowrap">{tx.created_by_username || '-'}</td>
                  <td className="py-2 px-3">{tx.note || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {transactions.length === 0 && (
          <div className="text-sm text-slate-500 py-8 text-center">تراکنشی ثبت نشده است.</div>
        )}
      </div>
    </div>
  )
}

export default BillingPage

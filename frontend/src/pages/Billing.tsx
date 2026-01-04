import { FormEvent, useEffect, useState } from 'react'
import client from '../api/client'

interface BillingInfo {
  wallet_balance: number
  cost_per_connected: number
  currency: string
}

const BillingPage = () => {
  const [data, setData] = useState<BillingInfo | null>(null)
  const [wallet, setWallet] = useState<number | ''>('')
  const [rate, setRate] = useState<number | ''>('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const fetchInfo = async () => {
    const { data } = await client.get<BillingInfo>('/api/billing')
    setData(data)
    setWallet(data.wallet_balance)
    setRate(data.cost_per_connected)
  }

  useEffect(() => {
    fetchInfo()
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    await client.put('/api/billing', {
      wallet_balance: wallet === '' ? undefined : wallet,
      cost_per_connected: rate === '' ? undefined : rate,
    })
    setMessage('Saved')
    fetchInfo()
    setSaving(false)
  }

  return (
    <div className="space-y-4 max-w-xl">
      <h1 className="text-lg font-semibold">تنظیمات هزینه و کیف پول</h1>
      <div className="bg-white rounded-xl border border-slate-100 p-4 shadow-sm">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-slate-600">هزینه هر تماس برقرار شده ({data?.currency || 'تومان'})</label>
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
            {saving ? 'در حال ذخیره...' : 'ذخیره'}
          </button>
          {message && <div className="text-xs text-emerald-600">{message}</div>}
        </form>
        {data && (
          <div className="mt-4 text-sm text-slate-700 space-y-1">
            <div>موجودی فعلی: {data.wallet_balance.toLocaleString()} {data.currency}</div>
            <div>هزینه هر تماس: {data.cost_per_connected.toLocaleString()} {data.currency}</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BillingPage

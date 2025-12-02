const DashboardPage = () => {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-100">
        <div className="text-sm text-slate-500">وضعیت کلی</div>
        <div className="text-2xl font-semibold">پنل فعال است</div>
      </div>
      <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-100">
        <div className="text-sm text-slate-500">زمان‌بندی</div>
        <div className="text-sm">تماس‌ها بر اساس بازه‌های مجاز زمان تهران مدیریت می‌شوند.</div>
      </div>
      <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-100">
        <div className="text-sm text-slate-500">نکته</div>
        <div className="text-sm">نمایش تاریخ در رابط کاربری به‌صورت تقویم شمسی است.</div>
      </div>
    </div>
  )
}

export default DashboardPage

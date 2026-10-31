import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { reportsApi } from '../../api'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Legend
} from 'recharts'

const fmt = (n: number) => n >= 100000 ? `₹${(n/100000).toFixed(1)}L` : n >= 1000 ? `₹${(n/1000).toFixed(1)}K` : `₹${n.toFixed(0)}`

type TabKey = 'overview' | 'revenue' | 'forecast' | 'overdue' | 'audit'

export default function ReportsPage() {
  const [tab, setTab] = useState<TabKey>('overview')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data: dash } = useQuery({ queryKey: ['dashboard'], queryFn: () => reportsApi.dashboard().then(r => r.data) })
  const { data: mrrArr } = useQuery({ queryKey: ['mrr-arr'], queryFn: () => reportsApi.mrrArr().then(r => r.data) })
  const { data: revenue } = useQuery({
    queryKey: ['revenue', dateFrom, dateTo],
    queryFn: () => reportsApi.revenue({ from: dateFrom || undefined, to: dateTo || undefined }).then(r => r.data),
    enabled: tab === 'revenue',
  })
  const { data: forecast } = useQuery({
    queryKey: ['forecast'], queryFn: () => reportsApi.forecast().then(r => r.data), enabled: tab === 'forecast'
  })
  const { data: overdue } = useQuery({
    queryKey: ['overdue-report'], queryFn: () => reportsApi.overdue({ per_page: 50 }).then(r => r.data), enabled: tab === 'overdue'
  })
  const { data: auditLogs } = useQuery({
    queryKey: ['audit-logs'], queryFn: () => reportsApi.auditLogs({ per_page: 50 }).then(r => r.data), enabled: tab === 'audit'
  })

  const TABS: [TabKey, string][] = [['overview', 'Overview'], ['revenue', 'Revenue'], ['forecast', 'Forecast'], ['overdue', 'Overdue'], ['audit', 'Audit Log']]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>

      <div className="flex gap-2 border-b border-gray-200">
        {TABS.map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-4">
          {/* MRR/ARR Cards */}
          <div className="grid md:grid-cols-3 gap-4">
            {[
              ['Monthly Recurring Revenue', fmt(dash?.mrr ?? 0), 'Normalized from active subscriptions'],
              ['Annual Recurring Revenue', fmt(dash?.arr ?? 0), 'MRR × 12'],
              ['Revenue Collected', fmt(dash?.revenue_collected ?? 0), `₹${(dash?.outstanding_revenue ?? 0).toFixed(0)} outstanding`],
            ].map(([title, val, sub]) => (
              <div key={title} className="card p-6">
                <p className="text-sm text-gray-500">{title}</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{val}</p>
                <p className="text-xs text-gray-400 mt-1">{sub}</p>
              </div>
            ))}
          </div>
          {/* Revenue trend */}
          <div className="card p-6">
            <h3 className="font-semibold text-gray-800 mb-4">Monthly Revenue Trend</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dash?.monthly_revenue_trend ?? []}>
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Area type="monotone" dataKey="billed" stroke="#3b82f6" fill="#dbeafe" name="Billed" />
                  <Area type="monotone" dataKey="collected" stroke="#10b981" fill="#d1fae5" name="Collected" />
                  <Legend />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* Revenue by product */}
          <div className="card p-6">
            <h3 className="font-semibold text-gray-800 mb-4">Revenue by Product</h3>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dash?.revenue_by_product ?? []} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={fmt} />
                  <YAxis type="category" dataKey="product" tick={{ fontSize: 11 }} width={140} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Bar dataKey="revenue" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* MRR breakdown */}
          {mrrArr && (
            <div className="card">
              <div className="card-header"><h3 className="font-semibold text-gray-800">MRR Breakdown</h3></div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="bg-gray-50 border-b">{['Subscription','Customer','Plan','Frequency','Amount','Monthly Equiv.'].map(h => (
                    <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-500">{h}</th>
                  ))}</tr></thead>
                  <tbody>
                    {mrrArr.breakdown?.map((b: any) => (
                      <tr key={b.subscription_number} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-2 font-mono text-xs text-blue-600">{b.subscription_number}</td>
                        <td className="px-4 py-2">{b.customer}</td>
                        <td className="px-4 py-2">{b.plan}</td>
                        <td className="px-4 py-2 capitalize">{b.frequency}</td>
                        <td className="px-4 py-2">₹{b.amount?.toFixed(2)}</td>
                        <td className="px-4 py-2 font-medium">₹{b.monthly_equivalent?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'revenue' && (
        <div className="space-y-4">
          <div className="flex gap-3 flex-wrap">
            <div><label className="label">From</label><input type="date" className="input" value={dateFrom} onChange={e => setDateFrom(e.target.value)} /></div>
            <div><label className="label">To</label><input type="date" className="input" value={dateTo} onChange={e => setDateTo(e.target.value)} /></div>
          </div>
          {revenue && (
            <>
              <div className="grid md:grid-cols-3 gap-4">
                {[
                  ['Total Billed', `₹${revenue.total_billed?.toFixed(2)}`],
                  ['Total Collected', `₹${revenue.total_collected?.toFixed(2)}`],
                  ['Total Outstanding', `₹${revenue.total_outstanding?.toFixed(2)}`],
                ].map(([k, v]) => (
                  <div key={k} className="card p-6">
                    <p className="text-sm text-gray-500">{k}</p>
                    <p className="text-2xl font-bold text-gray-900">{v}</p>
                  </div>
                ))}
              </div>
              <div className="card">
                <div className="card-header"><h3 className="font-semibold text-gray-800">Invoice List ({revenue.invoice_count})</h3></div>
                <table className="w-full text-sm">
                  <thead><tr className="bg-gray-50 border-b">{['Invoice','Customer','Date','Total','Paid','Outstanding','Status'].map(h => (
                    <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-500">{h}</th>
                  ))}</tr></thead>
                  <tbody>
                    {revenue.items?.slice(0, 50).map((i: any) => (
                      <tr key={i.invoice_number} className="border-b hover:bg-gray-50 text-xs">
                        <td className="px-4 py-2 font-mono text-blue-600">{i.invoice_number}</td>
                        <td className="px-4 py-2">{i.customer}</td>
                        <td className="px-4 py-2">{i.date}</td>
                        <td className="px-4 py-2">₹{i.grand_total?.toFixed(2)}</td>
                        <td className="px-4 py-2 text-emerald-600">₹{i.paid_amount?.toFixed(2)}</td>
                        <td className="px-4 py-2 text-red-600">₹{i.outstanding_amount?.toFixed(2)}</td>
                        <td className="px-4 py-2 capitalize">{i.status.replace('_',' ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'forecast' && forecast && (
        <div className="space-y-4">
          <div className="p-3 bg-amber-50 rounded-lg text-sm text-amber-800">⚠️ {forecast.note}</div>
          <div className="card p-6">
            <h3 className="font-semibold text-gray-800 mb-4">12-Month Revenue Forecast</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={forecast.forecast ?? []}>
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Bar dataKey="projected_revenue" fill="#3b82f6" name="Projected Revenue" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {tab === 'overdue' && (
        <div className="card">
          <div className="card-header"><h3 className="font-semibold text-gray-800">Overdue Invoices ({overdue?.total ?? 0})</h3></div>
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 border-b">{['Invoice','Customer','Due Date','Outstanding','Overdue Days','Status'].map(h => (
              <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-500">{h}</th>
            ))}</tr></thead>
            <tbody>
              {(overdue?.items ?? []).map((i: any) => (
                <tr key={i.invoice_id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs text-blue-600">{i.invoice_number}</td>
                  <td className="px-4 py-2">{i.customer_name}</td>
                  <td className="px-4 py-2 text-red-600">{i.due_date}</td>
                  <td className="px-4 py-2 font-medium text-red-600">₹{i.outstanding_amount?.toFixed(2)}</td>
                  <td className="px-4 py-2"><span className="badge-overdue">{i.overdue_days} days</span></td>
                  <td className="px-4 py-2 capitalize">{i.status.replace('_',' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'audit' && (
        <div className="card">
          <div className="card-header"><h3 className="font-semibold text-gray-800">Audit Log</h3></div>
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 border-b">{['Time','Actor','Action','Entity','Notes'].map(h => (
              <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-500">{h}</th>
            ))}</tr></thead>
            <tbody>
              {(auditLogs?.items ?? []).map((l: any) => (
                <tr key={l.id} className="border-b hover:bg-gray-50 text-xs">
                  <td className="px-4 py-2 text-gray-400">{l.created_at?.slice(0,19).replace('T',' ')}</td>
                  <td className="px-4 py-2 text-gray-600">{l.actor}</td>
                  <td className="px-4 py-2 font-mono text-blue-700">{l.action}</td>
                  <td className="px-4 py-2 text-gray-500">{l.entity_type}</td>
                  <td className="px-4 py-2 text-gray-500 max-w-xs truncate">{l.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

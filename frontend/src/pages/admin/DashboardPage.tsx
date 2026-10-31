import { useQuery } from '@tanstack/react-query'
import { reportsApi, billingApi } from '../../api'
import StatCard from '../../components/ui/StatCard'
import {
  Users, RefreshCw, TrendingUp, DollarSign, AlertTriangle,
  Activity, Zap, BarChart2, Calendar
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend
} from 'recharts'
import toast from 'react-hot-toast'

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4']

const fmt = (n: number) =>
  n >= 100000 ? `₹${(n/100000).toFixed(1)}L` :
  n >= 1000   ? `₹${(n/1000).toFixed(1)}K` :
  `₹${n.toFixed(0)}`

export default function DashboardPage() {
  const { data: dash, isLoading, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => reportsApi.dashboard().then(r => r.data),
    refetchInterval: 60_000,
  })

  const { data: billingDue } = useQuery({
    queryKey: ['billing-due'],
    queryFn: () => billingApi.dueCount().then(r => r.data),
    refetchInterval: 30_000,
  })

  async function runBilling() {
    try {
      const { data } = await billingApi.run()
      toast.success(`Billing complete: ${data.invoices_generated} invoices generated`)
      refetch()
    } catch {
      toast.error('Billing run failed.')
    }
  }

  const statusData = dash ? Object.entries(dash.subscription_status_distribution).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1), value
  })) : []

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <div key={i} className="skeleton h-28 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
          <p className="text-sm text-gray-500 mt-0.5">As of {dash?.as_of}</p>
        </div>
        <div className="flex gap-2">
          {billingDue && billingDue.due_count > 0 && (
            <button onClick={runBilling} className="btn-primary">
              <Zap size={16} />
              Run Billing ({billingDue.due_count} due)
            </button>
          )}
          <button onClick={() => refetch()} className="btn-secondary">
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Customers" value={dash?.total_customers ?? '—'}
          icon={Users} iconBg="bg-blue-100" />
        <StatCard title="Active Subscriptions" value={dash?.active_subscriptions ?? '—'}
          subtitle={`${dash?.paused_subscriptions ?? 0} paused`}
          icon={Activity} iconBg="bg-emerald-100" />
        <StatCard title="MRR" value={fmt(dash?.mrr ?? 0)}
          subtitle={`ARR ${fmt(dash?.arr ?? 0)}`}
          icon={TrendingUp} iconBg="bg-violet-100" />
        <StatCard title="Revenue Collected" value={fmt(dash?.revenue_collected ?? 0)}
          subtitle={`₹${(dash?.outstanding_revenue ?? 0).toFixed(0)} outstanding`}
          icon={DollarSign} iconBg="bg-green-100" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Total Subscriptions" value={dash?.total_subscriptions ?? '—'}
          icon={RefreshCw} iconBg="bg-blue-100" />
        <StatCard title="New This Month" value={dash?.new_subscriptions_this_month ?? '—'}
          icon={BarChart2} iconBg="bg-cyan-100" />
        <StatCard title="Overdue Invoices" value={dash?.overdue_invoices_count ?? '—'}
          subtitle={fmt(dash?.overdue_invoices_amount ?? 0)}
          icon={AlertTriangle} iconBg="bg-red-100" />
        <StatCard title="Renewal Rate" value={`${dash?.renewal_rate ?? 0}%`}
          icon={Calendar} iconBg="bg-amber-100" />
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Revenue trend */}
        <div className="lg:col-span-2 card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-800">Revenue Trend (Last 6 Months)</h3>
          </div>
          <div className="p-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dash?.monthly_revenue_trend ?? []}>
                <defs>
                  <linearGradient id="billed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="collected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => fmt(v)} />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Area type="monotone" dataKey="billed" stroke="#3b82f6" fill="url(#billed)" name="Billed" />
                <Area type="monotone" dataKey="collected" stroke="#10b981" fill="url(#collected)" name="Collected" />
                <Legend />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Subscription status */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-800">Subscription Status</h3>
          </div>
          <div className="p-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                  dataKey="value" nameKey="name" paddingAngle={3}>
                  {statusData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconSize={10} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid lg:grid-cols-2 gap-4">
        {/* Revenue by product */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-800">Revenue by Product</h3>
          </div>
          <div className="p-4 h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dash?.revenue_by_product ?? []} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => fmt(v)} />
                <YAxis type="category" dataKey="product" tick={{ fontSize: 11 }} width={140} />
                <Tooltip formatter={(v: number) => fmt(v)} />
                <Bar dataKey="revenue" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Upcoming renewals */}
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-gray-800">Upcoming Renewals (30 days)</h3>
          </div>
          <div className="overflow-y-auto max-h-52">
            {(dash?.upcoming_renewals ?? []).length === 0 ? (
              <p className="text-sm text-gray-400 p-4 text-center">No upcoming renewals.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left px-4 py-2 text-xs text-gray-500 font-semibold">Subscription</th>
                    <th className="text-left px-4 py-2 text-xs text-gray-500 font-semibold">Customer</th>
                    <th className="text-right px-4 py-2 text-xs text-gray-500 font-semibold">Date</th>
                    <th className="text-right px-4 py-2 text-xs text-gray-500 font-semibold">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {(dash?.upcoming_renewals ?? []).map((r: any) => (
                    <tr key={r.subscription_number} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs text-blue-600">{r.subscription_number}</td>
                      <td className="px-4 py-2 text-gray-600">{r.customer_name}</td>
                      <td className="px-4 py-2 text-right text-gray-600">{r.next_billing_date}</td>
                      <td className="px-4 py-2 text-right font-medium">₹{r.amount.toFixed(0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

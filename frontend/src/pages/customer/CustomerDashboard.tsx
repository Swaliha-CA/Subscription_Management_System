import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getStoredUser } from '../../hooks/useAuth'
import { customersApi, subscriptionsApi, invoicesApi } from '../../api'
import { RefreshCw, Receipt, DollarSign, AlertTriangle } from 'lucide-react'
import StatusBadge from '../../components/ui/StatusBadge'

export default function CustomerDashboard() {
  const user = getStoredUser()
  const navigate = useNavigate()
  const customerId = user?.customer_id

  const { data: summary } = useQuery({
    queryKey: ['customer-summary', customerId],
    queryFn: () => customersApi.summary(customerId!).then(r => r.data),
    enabled: !!customerId,
  })

  const { data: subs } = useQuery({
    queryKey: ['my-subscriptions'],
    queryFn: () => subscriptionsApi.list({ per_page: 5 }).then(r => r.data),
  })

  const { data: invoices } = useQuery({
    queryKey: ['my-invoices'],
    queryFn: () => invoicesApi.list({ per_page: 5 }).then(r => r.data),
  })

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-6 text-white">
        <h1 className="text-2xl font-bold">Welcome back, {user?.first_name}! 👋</h1>
        <p className="text-blue-200 mt-1">Here's an overview of your account with Brightloop Software.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Active Subscriptions', value: summary?.active_subscriptions ?? '—', icon: RefreshCw, color: 'text-blue-600', bg: 'bg-blue-100' },
          { label: 'Total Subscriptions', value: summary?.total_subscriptions ?? '—', icon: RefreshCw, color: 'text-gray-600', bg: 'bg-gray-100' },
          { label: 'Outstanding Amount', value: `₹${(summary?.outstanding_amount ?? 0).toFixed(0)}`, icon: DollarSign, color: 'text-amber-600', bg: 'bg-amber-100' },
          { label: 'Overdue Invoices', value: summary?.overdue_invoices ?? '—', icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-100' },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="card p-5">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 ${bg} rounded-lg flex items-center justify-center`}>
                <Icon size={18} className={color} />
              </div>
              <div>
                <p className="text-xl font-bold text-gray-900">{value}</p>
                <p className="text-xs text-gray-500">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Active Subscriptions */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">My Subscriptions</h3>
            <button onClick={() => navigate('/portal/subscriptions')} className="text-xs text-blue-600 hover:underline">View all</button>
          </div>
          <div className="divide-y divide-gray-100">
            {(subs?.items ?? []).length === 0
              ? <p className="text-sm text-gray-400 p-4 text-center">No subscriptions yet.</p>
              : (subs?.items ?? []).map((s: any) => (
                <div key={s.id} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium font-mono text-blue-600">{s.subscription_number}</p>
                    <p className="text-xs text-gray-500">{s.plan_name} · ₹{s.total_amount?.toFixed(0)}/period</p>
                    {s.next_billing_date && <p className="text-xs text-gray-400">Next: {s.next_billing_date}</p>}
                  </div>
                  <StatusBadge status={s.status} />
                </div>
              ))
            }
          </div>
        </div>

        {/* Recent Invoices */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Recent Invoices</h3>
            <button onClick={() => navigate('/portal/invoices')} className="text-xs text-blue-600 hover:underline">View all</button>
          </div>
          <div className="divide-y divide-gray-100">
            {(invoices?.items ?? []).length === 0
              ? <p className="text-sm text-gray-400 p-4 text-center">No invoices yet.</p>
              : (invoices?.items ?? []).map((i: any) => (
                <div key={i.id} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium font-mono text-blue-600">{i.invoice_number}</p>
                    <p className="text-xs text-gray-500">₹{i.grand_total?.toFixed(0)} · Due {i.due_date}</p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={i.status} />
                    {i.is_overdue && <p className="text-xs text-red-500 mt-0.5">{i.overdue_days}d overdue</p>}
                  </div>
                </div>
              ))
            }
          </div>
        </div>
      </div>
    </div>
  )
}

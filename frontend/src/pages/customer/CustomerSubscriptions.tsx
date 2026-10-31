import { useQuery } from '@tanstack/react-query'
import { subscriptionsApi } from '../../api'
import StatusBadge from '../../components/ui/StatusBadge'

export default function CustomerSubscriptions() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-subscriptions-all'],
    queryFn: () => subscriptionsApi.list({ per_page: 50 }).then(r => r.data),
  })

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">My Subscriptions</h1>
      <div className="space-y-3">
        {(data?.items ?? []).map((s: any) => (
          <div key={s.id} className="card p-6">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-mono text-blue-600 font-semibold">{s.subscription_number}</p>
                <p className="text-lg font-bold text-gray-900 mt-0.5">{s.plan_name}</p>
                <p className="text-sm text-gray-500 capitalize">{s.billing_frequency} billing</p>
              </div>
              <StatusBadge status={s.status} />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {[
                ['Amount', `₹${s.total_amount?.toFixed(2)}`],
                ['Start Date', s.start_date || '—'],
                ['Next Billing', s.next_billing_date || '—'],
                ['Payment Terms', s.payment_terms],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-gray-400">{k}</p>
                  <p className="font-medium text-gray-800">{v}</p>
                </div>
              ))}
            </div>
            {s.status === 'active' && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-400">
                  To pause or cancel this subscription, please contact support at support@brightloop.in
                </p>
              </div>
            )}
          </div>
        ))}
        {(data?.items ?? []).length === 0 && (
          <div className="card p-12 text-center text-gray-400">
            <p className="text-lg">No subscriptions yet.</p>
            <p className="text-sm mt-1">Contact us to get started with a plan.</p>
          </div>
        )}
      </div>
    </div>
  )
}

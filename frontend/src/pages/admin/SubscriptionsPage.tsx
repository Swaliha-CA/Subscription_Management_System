import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { subscriptionsApi } from '../../api'
import Table from '../../components/ui/Table'
import Pagination from '../../components/ui/Pagination'
import StatusBadge from '../../components/ui/StatusBadge'

const STATUS_OPTIONS = ['', 'active', 'paused', 'confirmed', 'closed', 'draft', 'expired']

export default function SubscriptionsPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['subscriptions', page, search, status],
    queryFn: () => subscriptionsApi.list({ page, per_page: 20, search, status: status || undefined }).then(r => r.data),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Subscriptions</h1>
        <span className="text-sm text-gray-500">{data?.total ?? 0} total</span>
      </div>

      <div className="card">
        <div className="card-header flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-48 max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className="input pl-9" placeholder="Search subscription number…" value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }} />
          </div>
          <select className="input w-40" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}>
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
          </select>
        </div>

        <Table
          loading={isLoading}
          data={data?.items ?? []}
          keyExtractor={r => r.id}
          onRowClick={r => navigate(`/subscriptions/${r.id}`)}
          columns={[
            { header: '#', render: r => <span className="font-mono text-xs text-blue-600">{r.subscription_number}</span> },
            { header: 'Customer', key: 'customer_name' },
            { header: 'Plan', key: 'plan_name' },
            { header: 'Frequency', render: r => <span className="capitalize">{r.billing_frequency}</span> },
            { header: 'Amount', render: r => <span className="font-medium">₹{r.total_amount?.toFixed(2)}</span> },
            { header: 'Next Billing', key: 'next_billing_date' },
            { header: 'Status', render: r => <StatusBadge status={r.status} /> },
          ]}
        />
        <Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} perPage={20} onPageChange={setPage} />
      </div>
    </div>
  )
}

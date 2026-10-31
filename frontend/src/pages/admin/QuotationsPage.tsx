import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { quotationsApi } from '../../api'
import Table from '../../components/ui/Table'
import Pagination from '../../components/ui/Pagination'
import StatusBadge from '../../components/ui/StatusBadge'

export default function QuotationsPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['quotations', page, search, status],
    queryFn: () => quotationsApi.list({ page, per_page: 20, search, status: status || undefined }).then(r => r.data),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Quotations</h1>
        <span className="text-sm text-gray-500">{data?.total ?? 0} total</span>
      </div>

      <div className="card">
        <div className="card-header flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-48 max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className="input pl-9" placeholder="Search quotation…" value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }} />
          </div>
          <select className="input w-40" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}>
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="confirmed">Confirmed</option>
            <option value="expired">Expired</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <Table
          loading={isLoading}
          data={data?.items ?? []}
          keyExtractor={r => r.id}
          onRowClick={r => navigate(`/quotations/${r.id}`)}
          columns={[
            { header: '#', render: r => <span className="font-mono text-xs text-blue-600">{r.quotation_number}</span> },
            { header: 'Customer', key: 'customer_name' },
            { header: 'Plan', key: 'plan_name' },
            { header: 'Total', render: r => <span className="font-medium">₹{r.grand_total?.toFixed(2)}</span> },
            { header: 'Expires', key: 'expiry_date' },
            { header: 'Status', render: r => <StatusBadge status={r.status} /> },
            { header: 'Subscription', render: r => r.subscription_id
              ? <button onClick={e => { e.stopPropagation(); navigate(`/subscriptions/${r.subscription_id}`) }}
                  className="text-xs text-blue-600 hover:underline">View Sub</button>
              : <span className="text-gray-300">—</span>
            },
          ]}
        />
        <Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} perPage={20} onPageChange={setPage} />
      </div>
    </div>
  )
}

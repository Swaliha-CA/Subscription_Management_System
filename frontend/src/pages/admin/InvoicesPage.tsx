import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search, AlertTriangle } from 'lucide-react'
import { invoicesApi } from '../../api'
import Table from '../../components/ui/Table'
import Pagination from '../../components/ui/Pagination'
import StatusBadge from '../../components/ui/StatusBadge'

export default function InvoicesPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [overdue, setOverdue] = useState(false)
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', page, search, status, overdue],
    queryFn: () => invoicesApi.list({ page, per_page: 20, search, status: status || undefined, overdue: overdue ? 'true' : undefined }).then(r => r.data),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
        <span className="text-sm text-gray-500">{data?.total ?? 0} total</span>
      </div>

      <div className="card">
        <div className="card-header flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-48 max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className="input pl-9" placeholder="Search invoice number…" value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }} />
          </div>
          <select className="input w-44" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}>
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="confirmed">Confirmed</option>
            <option value="paid">Paid</option>
            <option value="partially_paid">Partially Paid</option>
            <option value="overdue">Overdue</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <label className="flex items-center gap-2 text-sm cursor-pointer text-red-600">
            <input type="checkbox" checked={overdue} onChange={e => { setOverdue(e.target.checked); setPage(1) }} />
            <AlertTriangle size={14} /> Overdue only
          </label>
        </div>

        <Table
          loading={isLoading}
          data={data?.items ?? []}
          keyExtractor={r => r.id}
          onRowClick={r => navigate(`/invoices/${r.id}`)}
          columns={[
            { header: 'Invoice #', render: r => <span className="font-mono text-xs text-blue-600">{r.invoice_number}</span> },
            { header: 'Customer', key: 'customer_name' },
            { header: 'Date', key: 'invoice_date' },
            { header: 'Due Date', render: r => (
              <span className={r.is_overdue ? 'text-red-600 font-medium' : ''}>{r.due_date}</span>
            )},
            { header: 'Total', render: r => <span className="font-medium">₹{r.grand_total?.toFixed(2)}</span> },
            { header: 'Outstanding', render: r => (
              <span className={r.outstanding_amount > 0 ? 'text-red-600 font-medium' : 'text-gray-500'}>
                ₹{r.outstanding_amount?.toFixed(2)}
              </span>
            )},
            { header: 'Status', render: r => (
              <div className="flex items-center gap-1">
                <StatusBadge status={r.status} />
                {r.is_overdue && <span className="badge-overdue ml-1">+{r.overdue_days}d</span>}
              </div>
            )},
          ]}
        />
        <Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} perPage={20} onPageChange={setPage} />
      </div>
    </div>
  )
}

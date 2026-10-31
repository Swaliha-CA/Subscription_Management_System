import { useQuery } from '@tanstack/react-query'
import { invoicesApi } from '../../api'
import StatusBadge from '../../components/ui/StatusBadge'

export default function CustomerInvoices() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-invoices-all'],
    queryFn: () => invoicesApi.list({ per_page: 50 }).then(r => r.data),
  })

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">My Invoices</h1>
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                {['Invoice #', 'Date', 'Due Date', 'Period', 'Total', 'Paid', 'Outstanding', 'Status'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((i: any) => (
                <tr key={i.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-blue-600">{i.invoice_number}</td>
                  <td className="px-4 py-3">{i.invoice_date}</td>
                  <td className="px-4 py-3">
                    <span className={i.is_overdue ? 'text-red-600 font-medium' : ''}>{i.due_date}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {i.billing_period_start && `${i.billing_period_start} – ${i.billing_period_end}`}
                  </td>
                  <td className="px-4 py-3 font-medium">₹{i.grand_total?.toFixed(2)}</td>
                  <td className="px-4 py-3 text-emerald-600">₹{i.paid_amount?.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span className={i.outstanding_amount > 0 ? 'text-red-600 font-medium' : 'text-gray-400'}>
                      ₹{i.outstanding_amount?.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <StatusBadge status={i.status} />
                      {i.is_overdue && <p className="text-xs text-red-500">{i.overdue_days}d overdue</p>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(data?.items ?? []).length === 0 && (
            <p className="text-center py-12 text-gray-400">No invoices yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}

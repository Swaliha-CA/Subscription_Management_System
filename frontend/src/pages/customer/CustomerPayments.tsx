import { useQuery } from '@tanstack/react-query'
import { paymentsApi } from '../../api'

export default function CustomerPayments() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-payments'],
    queryFn: () => paymentsApi.list({ per_page: 50 }).then(r => r.data),
  })

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Payment History</h1>
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                {['Payment #', 'Date', 'Method', 'Amount', 'Reference', 'Applied To'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((p: any) => (
                <tr key={p.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-blue-600">{p.payment_number}</td>
                  <td className="px-4 py-3">{p.payment_date}</td>
                  <td className="px-4 py-3 capitalize">{p.payment_method.replace('_', ' ')}</td>
                  <td className="px-4 py-3 font-semibold text-emerald-600">₹{p.amount?.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-500">{p.reference_number || '—'}</td>
                  <td className="px-4 py-3 text-xs">
                    {p.allocations.map((a: any) => (
                      <span key={a.invoice_id} className="text-blue-600 font-mono">{a.invoice_number} </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(data?.items ?? []).length === 0 && (
            <p className="text-center py-12 text-gray-400">No payment history.</p>
          )}
        </div>
      </div>
    </div>
  )
}

import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle, ArrowRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { quotationsApi } from '../../api'
import StatusBadge from '../../components/ui/StatusBadge'

export default function QuotationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: q, isLoading } = useQuery({
    queryKey: ['quotation', id],
    queryFn: () => quotationsApi.get(id!).then(r => r.data),
  })

  async function confirm() {
    try {
      await quotationsApi.confirm(id!)
      toast.success('Quotation confirmed!')
      qc.invalidateQueries({ queryKey: ['quotation', id] })
    } catch (err: any) { toast.error(err.response?.data?.error || 'Failed.') }
  }

  async function convert() {
    try {
      const { data } = await quotationsApi.convert(id!)
      toast.success('Subscription created!')
      navigate(`/subscriptions/${data.id}`)
    } catch (err: any) { toast.error(err.response?.data?.error || 'Failed.') }
  }

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />
  if (!q) return <p>Quotation not found.</p>

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={() => navigate(-1)} className="btn-ghost p-2"><ArrowLeft size={18} /></button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 font-mono">{q.quotation_number}</h1>
          <p className="text-sm text-gray-500">{q.customer_name}</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <StatusBadge status={q.status} />
          {q.status === 'draft' && (
            <button onClick={confirm} className="btn-success"><CheckCircle size={14} /> Confirm</button>
          )}
          {q.status === 'confirmed' && !q.subscription_id && (
            <button onClick={convert} className="btn-primary"><ArrowRight size={14} /> Convert to Subscription</button>
          )}
          {q.subscription_id && (
            <button onClick={() => navigate(`/subscriptions/${q.subscription_id}`)} className="btn-secondary">
              View Subscription
            </button>
          )}
        </div>
      </div>

      <div className="card p-8">
        <div className="flex justify-between mb-8">
          <div>
            <h2 className="text-xl font-bold text-gray-900">QUOTATION</h2>
            <p className="font-mono text-blue-600 font-semibold">{q.quotation_number}</p>
          </div>
          <div className="text-right text-sm text-gray-600 space-y-1">
            <p><span className="text-gray-400">Expires: </span>{q.expiry_date}</p>
            <p><span className="text-gray-400">Terms: </span>{q.payment_terms}</p>
            {q.plan_name && <p><span className="text-gray-400">Plan: </span>{q.plan_name}</p>}
          </div>
        </div>

        <div className="mb-6">
          <p className="text-xs text-gray-400 uppercase font-semibold mb-1">Prepared For</p>
          <p className="font-semibold text-gray-900">{q.customer_name}</p>
        </div>

        <table className="w-full text-sm mb-6">
          <thead>
            <tr className="bg-gray-50 border-b">
              <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500">Product</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Qty</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Unit Price</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Discount</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Tax</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Total</th>
            </tr>
          </thead>
          <tbody>
            {q.lines.map((l: any) => (
              <tr key={l.id} className="border-b border-gray-100">
                <td className="px-3 py-2">{l.product_name}{l.variant_name ? ` — ${l.variant_name}` : ''}</td>
                <td className="px-3 py-2 text-right">{l.quantity}</td>
                <td className="px-3 py-2 text-right">₹{l.unit_price?.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{l.discount_pct}%</td>
                <td className="px-3 py-2 text-right">{l.tax_pct}%</td>
                <td className="px-3 py-2 text-right font-medium">₹{l.total?.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex justify-end">
          <div className="w-64 space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>₹{q.subtotal?.toFixed(2)}</span></div>
            {q.discount_amount > 0 && <div className="flex justify-between text-emerald-600"><span>Discount</span><span>-₹{q.discount_amount?.toFixed(2)}</span></div>}
            <div className="flex justify-between"><span className="text-gray-500">Tax</span><span>₹{q.tax_amount?.toFixed(2)}</span></div>
            <div className="flex justify-between font-bold text-base border-t pt-2 mt-2"><span>Grand Total</span><span>₹{q.grand_total?.toFixed(2)}</span></div>
          </div>
        </div>
      </div>
    </div>
  )
}

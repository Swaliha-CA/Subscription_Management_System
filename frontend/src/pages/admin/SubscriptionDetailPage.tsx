import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Play, Pause, RotateCcw, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { subscriptionsApi } from '../../api'
import StatusBadge from '../../components/ui/StatusBadge'

export default function SubscriptionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: sub, isLoading } = useQuery({
    queryKey: ['subscription', id],
    queryFn: () => subscriptionsApi.get(id!).then(r => r.data),
  })

  async function action(fn: () => Promise<any>, msg: string) {
    try {
      await fn()
      toast.success(msg)
      qc.invalidateQueries({ queryKey: ['subscription', id] })
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Action failed.')
    }
  }

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />
  if (!sub) return <p className="text-gray-500">Subscription not found.</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={() => navigate(-1)} className="btn-ghost p-2"><ArrowLeft size={18} /></button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 font-mono">{sub.subscription_number}</h1>
          <p className="text-sm text-gray-500">{sub.customer_name} · {sub.plan_name}</p>
        </div>
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          <StatusBadge status={sub.status} />
          {sub.status === 'confirmed' && (
            <button onClick={() => action(() => subscriptionsApi.activate(id!), 'Subscription activated!')} className="btn-success">
              <Play size={14} /> Activate
            </button>
          )}
          {sub.status === 'active' && (
            <button onClick={() => action(() => subscriptionsApi.pause(id!), 'Subscription paused.')} className="btn-secondary">
              <Pause size={14} /> Pause
            </button>
          )}
          {sub.status === 'paused' && (
            <button onClick={() => action(() => subscriptionsApi.resume(id!), 'Subscription resumed!')} className="btn-success">
              <Play size={14} /> Resume
            </button>
          )}
          {['active', 'paused', 'expired', 'closed'].includes(sub.status) && (
            <button onClick={() => action(() => subscriptionsApi.renew(id!), 'Subscription renewed!')} className="btn-primary">
              <RotateCcw size={14} /> Renew
            </button>
          )}
          {sub.status !== 'closed' && (
            <button onClick={() => { if (confirm('Cancel this subscription?')) action(() => subscriptionsApi.cancel(id!), 'Subscription cancelled.') }} className="btn-danger">
              <XCircle size={14} /> Cancel
            </button>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <div className="card p-6 space-y-3">
          <h3 className="font-semibold text-gray-800">Subscription Details</h3>
          {[
            ['Customer', sub.customer_name],
            ['Plan', sub.plan_name],
            ['Billing Frequency', sub.billing_frequency],
            ['Start Date', sub.start_date],
            ['Next Billing', sub.next_billing_date],
            ['Payment Terms', sub.payment_terms],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between text-sm">
              <span className="text-gray-500">{k}</span>
              <span className="font-medium capitalize">{v || '—'}</span>
            </div>
          ))}
        </div>

        <div className="card p-6 space-y-3">
          <h3 className="font-semibold text-gray-800">Financials</h3>
          {[
            ['Unit Price', `₹${sub.unit_price?.toFixed(2)}`],
            ['Quantity', sub.quantity],
            ['Discount', `${sub.discount_pct}%`],
            ['Tax', `${sub.tax_pct}%`],
            ['Subtotal', `₹${sub.subtotal?.toFixed(2)}`],
            ['Tax Amount', `₹${sub.tax_amount?.toFixed(2)}`],
            ['Total', `₹${sub.total_amount?.toFixed(2)}`],
          ].map(([k, v]) => (
            <div key={k} className={`flex justify-between text-sm ${k === 'Total' ? 'font-bold text-base border-t pt-2' : ''}`}>
              <span className="text-gray-500">{k}</span>
              <span>{v}</span>
            </div>
          ))}
        </div>
      </div>

      {sub.lines.length > 0 && (
        <div className="card">
          <div className="card-header"><h3 className="font-semibold text-gray-800">Subscription Lines</h3></div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500">Product</th>
                <th className="text-right px-4 py-2 text-xs font-semibold text-gray-500">Qty</th>
                <th className="text-right px-4 py-2 text-xs font-semibold text-gray-500">Price</th>
                <th className="text-right px-4 py-2 text-xs font-semibold text-gray-500">Tax</th>
                <th className="text-right px-4 py-2 text-xs font-semibold text-gray-500">Total</th>
              </tr>
            </thead>
            <tbody>
              {sub.lines.map((l: any) => (
                <tr key={l.id} className="border-b border-gray-50">
                  <td className="px-4 py-2">{l.product_name}{l.variant_name ? ` — ${l.variant_name}` : ''}</td>
                  <td className="px-4 py-2 text-right">{l.quantity}</td>
                  <td className="px-4 py-2 text-right">₹{l.unit_price?.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right">{l.tax_pct}%</td>
                  <td className="px-4 py-2 text-right font-medium">₹{l.total?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

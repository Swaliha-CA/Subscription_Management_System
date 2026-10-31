import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle, XCircle, Bell } from 'lucide-react'
import toast from 'react-hot-toast'
import { invoicesApi } from '../../api'
import StatusBadge from '../../components/ui/StatusBadge'

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: inv, isLoading } = useQuery({
    queryKey: ['invoice', id],
    queryFn: () => invoicesApi.get(id!).then(r => r.data),
  })

  async function action(fn: () => Promise<any>, msg: string) {
    try {
      await fn()
      toast.success(msg)
      qc.invalidateQueries({ queryKey: ['invoice', id] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed.')
    }
  }

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />
  if (!inv) return <p>Invoice not found.</p>

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={() => navigate(-1)} className="btn-ghost p-2"><ArrowLeft size={18} /></button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 font-mono">{inv.invoice_number}</h1>
          <p className="text-sm text-gray-500">{inv.customer_name}</p>
        </div>
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          <StatusBadge status={inv.status} />
          {inv.is_overdue && <span className="badge-overdue">{inv.overdue_days} days overdue</span>}
          {inv.status === 'draft' && (
            <button onClick={() => action(() => invoicesApi.confirm(id!), 'Invoice confirmed.')} className="btn-success">
              <CheckCircle size={14} /> Confirm
            </button>
          )}
          {['confirmed', 'partially_paid'].includes(inv.status) && (
            <button onClick={() => action(() => invoicesApi.sendReminder(id!), 'Reminder sent.')} className="btn-secondary">
              <Bell size={14} /> Send Reminder
            </button>
          )}
          {inv.status !== 'paid' && inv.status !== 'cancelled' && (
            <button onClick={() => { if (confirm('Cancel this invoice?')) action(() => invoicesApi.cancel(id!), 'Invoice cancelled.') }} className="btn-danger">
              <XCircle size={14} /> Cancel
            </button>
          )}
        </div>
      </div>

      {/* Invoice body */}
      <div className="card p-8">
        {/* Header */}
        <div className="flex justify-between mb-8">
          <div>
            <h2 className="text-xl font-bold text-gray-900">INVOICE</h2>
            <p className="font-mono text-blue-600 font-semibold">{inv.invoice_number}</p>
          </div>
          <div className="text-right text-sm text-gray-600 space-y-1">
            <p><span className="text-gray-400">Date: </span>{inv.invoice_date}</p>
            <p><span className="text-gray-400">Due: </span><span className={inv.is_overdue ? 'text-red-600 font-semibold' : ''}>{inv.due_date}</span></p>
            {inv.subscription_number && <p><span className="text-gray-400">Sub: </span><span className="font-mono">{inv.subscription_number}</span></p>}
            {inv.billing_period_start && (
              <p><span className="text-gray-400">Period: </span>{inv.billing_period_start} to {inv.billing_period_end}</p>
            )}
          </div>
        </div>

        {/* Bill to */}
        <div className="mb-6">
          <p className="text-xs text-gray-400 uppercase font-semibold mb-1">Bill To</p>
          <p className="font-semibold text-gray-900">{inv.customer_name}</p>
        </div>

        {/* Lines */}
        <table className="w-full text-sm mb-6">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500">Description</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Qty</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Unit Price</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Discount</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Tax</th>
              <th className="text-right px-3 py-2 text-xs font-semibold text-gray-500">Total</th>
            </tr>
          </thead>
          <tbody>
            {inv.lines.map((l: any) => (
              <tr key={l.id} className="border-b border-gray-100">
                <td className="px-3 py-2">{l.description}</td>
                <td className="px-3 py-2 text-right">{l.quantity}</td>
                <td className="px-3 py-2 text-right">₹{l.unit_price?.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{l.discount_pct}%</td>
                <td className="px-3 py-2 text-right">{l.tax_pct}%</td>
                <td className="px-3 py-2 text-right font-medium">₹{l.total?.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Totals */}
        <div className="flex justify-end">
          <div className="w-64 space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Subtotal</span><span>₹{inv.subtotal?.toFixed(2)}</span></div>
            {inv.discount_amount > 0 && <div className="flex justify-between text-emerald-600"><span>Discount</span><span>-₹{inv.discount_amount?.toFixed(2)}</span></div>}
            <div className="flex justify-between"><span className="text-gray-500">Tax</span><span>₹{inv.tax_amount?.toFixed(2)}</span></div>
            <div className="flex justify-between font-bold text-base border-t pt-2 mt-2"><span>Grand Total</span><span>₹{inv.grand_total?.toFixed(2)}</span></div>
            <div className="flex justify-between text-emerald-600"><span>Paid</span><span>₹{inv.paid_amount?.toFixed(2)}</span></div>
            {inv.outstanding_amount > 0 && (
              <div className="flex justify-between font-semibold text-red-600"><span>Outstanding</span><span>₹{inv.outstanding_amount?.toFixed(2)}</span></div>
            )}
          </div>
        </div>

        {/* Payments */}
        {inv.payments.length > 0 && (
          <div className="mt-6 border-t pt-4">
            <p className="text-sm font-semibold text-gray-700 mb-2">Payment History</p>
            <div className="space-y-1">
              {inv.payments.map((p: any) => (
                <div key={p.id} className="flex justify-between text-sm text-gray-600">
                  <span className="font-mono text-xs">{p.payment_number}</span>
                  <span className="capitalize">{p.method}</span>
                  <span>{p.date}</span>
                  <span className="font-medium text-emerald-600">₹{p.amount?.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

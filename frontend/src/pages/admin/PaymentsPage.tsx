import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { paymentsApi, customersApi, invoicesApi } from '../../api'
import Table from '../../components/ui/Table'
import Pagination from '../../components/ui/Pagination'

export default function PaymentsPage() {
  const [page, setPage] = useState(1)
  const [showAdd, setShowAdd] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState('')
  const [customerInvoices, setCustomerInvoices] = useState<any[]>([])
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['payments', page],
    queryFn: () => paymentsApi.list({ page, per_page: 20 }).then(r => r.data),
  })
  const { data: customers } = useQuery({
    queryKey: ['customers-all'],
    queryFn: () => customersApi.list({ per_page: 100 }).then(r => r.data),
  })

  const [form, setForm] = useState({
    customer_id: '', payment_method: 'upi', amount: '',
    payment_date: new Date().toISOString().split('T')[0],
    reference_number: '', notes: '',
    invoice_id: '',
  })

  async function loadCustomerInvoices(custId: string) {
    if (!custId) return
    const { data } = await invoicesApi.list({ customer_id: custId, status: 'confirmed', per_page: 50 })
    setCustomerInvoices(data.items)
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    const payload: any = { ...form, amount: Number(form.amount) }
    if (form.invoice_id) {
      payload.allocations = [{ invoice_id: form.invoice_id, amount: Number(form.amount) }]
    }
    delete payload.invoice_id
    try {
      await paymentsApi.record(payload)
      toast.success('Payment recorded!')
      qc.invalidateQueries({ queryKey: ['payments'] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
      setShowAdd(false)
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed.')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Payments</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary"><Plus size={16} /> Record Payment</button>
      </div>

      <div className="card">
        <Table
          loading={isLoading}
          data={data?.items ?? []}
          keyExtractor={r => r.id}
          columns={[
            { header: '#', render: r => <span className="font-mono text-xs text-blue-600">{r.payment_number}</span> },
            { header: 'Customer', key: 'customer_name' },
            { header: 'Method', render: r => <span className="capitalize">{r.payment_method.replace('_', ' ')}</span> },
            { header: 'Amount', render: r => <span className="font-medium text-emerald-600">₹{r.amount?.toFixed(2)}</span> },
            { header: 'Date', key: 'payment_date' },
            { header: 'Reference', key: 'reference_number' },
            { header: 'Unallocated', render: r => <span className={r.unallocated_amount > 0 ? 'text-amber-600' : 'text-gray-400'}>₹{r.unallocated_amount?.toFixed(2)}</span> },
          ]}
        />
        <Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} perPage={20} onPageChange={setPage} />
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="p-6 border-b"><h2 className="text-lg font-semibold">Record Payment</h2></div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div>
                <label className="label">Customer</label>
                <select className="input" value={form.customer_id} required
                  onChange={e => {
                    setForm(f => ({...f, customer_id: e.target.value}))
                    loadCustomerInvoices(e.target.value)
                  }}>
                  <option value="">Select customer…</option>
                  {(customers?.items ?? []).map((c: any) => (
                    <option key={c.id} value={c.id}>{c.full_name} ({c.customer_code})</option>
                  ))}
                </select>
              </div>
              {customerInvoices.length > 0 && (
                <div>
                  <label className="label">Apply to Invoice (optional)</label>
                  <select className="input" value={form.invoice_id} onChange={e => setForm(f => ({...f, invoice_id: e.target.value}))}>
                    <option value="">Don't allocate yet</option>
                    {customerInvoices.map((i: any) => (
                      <option key={i.id} value={i.id}>{i.invoice_number} — ₹{i.outstanding_amount?.toFixed(0)} outstanding</option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label className="label">Method</label>
                <select className="input" value={form.payment_method} onChange={e => setForm(f => ({...f, payment_method: e.target.value}))}>
                  <option value="cash">Cash</option>
                  <option value="upi">UPI</option>
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="card">Card</option>
                  <option value="cheque">Cheque</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Amount (₹)</label><input type="number" min="0.01" step="0.01" className="input" value={form.amount} onChange={e => setForm(f => ({...f, amount: e.target.value}))} required /></div>
                <div><label className="label">Date</label><input type="date" className="input" value={form.payment_date} onChange={e => setForm(f => ({...f, payment_date: e.target.value}))} required /></div>
              </div>
              <div><label className="label">Reference / UTR #</label><input className="input" value={form.reference_number} onChange={e => setForm(f => ({...f, reference_number: e.target.value}))} /></div>
              <div><label className="label">Notes</label><input className="input" value={form.notes} onChange={e => setForm(f => ({...f, notes: e.target.value}))} /></div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="btn-primary flex-1 justify-center">Record</button>
                <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

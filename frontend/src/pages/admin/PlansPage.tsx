import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { plansApi, productsApi } from '../../api'
import Table from '../../components/ui/Table'

export default function PlansPage() {
  const [showAdd, setShowAdd] = useState(false)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: () => plansApi.list({ per_page: 50 }).then(r => r.data),
  })
  const { data: products } = useQuery({
    queryKey: ['products-list'],
    queryFn: () => productsApi.list({ per_page: 50 }).then(r => r.data),
  })

  const [form, setForm] = useState({
    name: '', product_id: '', billing_frequency: 'monthly',
    base_price: '', min_quantity: '1', description: '',
    allow_pause: true, allow_renewal: true, allow_early_cancellation: true,
  })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await plansApi.create({ ...form, base_price: Number(form.base_price), min_quantity: Number(form.min_quantity) })
      toast.success('Plan created!')
      qc.invalidateQueries({ queryKey: ['plans'] })
      setShowAdd(false)
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed.')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Subscription Plans</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary"><Plus size={16} /> Add Plan</button>
      </div>

      <div className="card">
        <Table
          loading={isLoading}
          data={data?.items ?? []}
          keyExtractor={r => r.id}
          columns={[
            { header: 'Plan Name', render: r => <span className="font-medium">{r.name}</span> },
            { header: 'Product', key: 'product_name' },
            { header: 'Frequency', render: r => <span className="capitalize">{r.billing_frequency}</span> },
            { header: 'Price', render: r => <span className="font-medium">₹{r.base_price?.toFixed(2)}</span> },
            { header: 'Status', render: r => r.is_active
              ? <span className="badge-active">Active</span>
              : <span className="badge-closed">Inactive</span>
            },
            { header: 'Features', render: r => (
              <div className="flex gap-1">
                {r.allow_pause && <span className="badge bg-blue-50 text-blue-600">Pause</span>}
                {r.allow_renewal && <span className="badge bg-emerald-50 text-emerald-600">Renew</span>}
                {r.allow_early_cancellation && <span className="badge bg-amber-50 text-amber-600">Cancel</span>}
              </div>
            )},
          ]}
        />
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
            <div className="p-6 border-b"><h2 className="text-lg font-semibold">Add Plan</h2></div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div><label className="label">Plan Name</label><input className="input" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} required /></div>
              <div>
                <label className="label">Product</label>
                <select className="input" value={form.product_id} onChange={e => setForm(f => ({...f, product_id: e.target.value}))} required>
                  <option value="">Select product…</option>
                  {(products?.items ?? []).map((p: any) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Billing Frequency</label>
                  <select className="input" value={form.billing_frequency} onChange={e => setForm(f => ({...f, billing_frequency: e.target.value}))}>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="yearly">Yearly</option>
                  </select>
                </div>
                <div><label className="label">Base Price (₹)</label><input type="number" min="0" step="0.01" className="input" value={form.base_price} onChange={e => setForm(f => ({...f, base_price: e.target.value}))} required /></div>
              </div>
              <div><label className="label">Description</label><input className="input" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} /></div>
              <div className="flex gap-4">
                {(['allow_pause', 'allow_renewal', 'allow_early_cancellation'] as const).map(k => (
                  <label key={k} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" checked={form[k]} onChange={e => setForm(f => ({...f, [k]: e.target.checked}))} />
                    {k.replace('allow_', '').replace('_', ' ')}
                  </label>
                ))}
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="btn-primary flex-1 justify-center">Create</button>
                <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

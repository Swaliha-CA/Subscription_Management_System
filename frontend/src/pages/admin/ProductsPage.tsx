import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, ChevronDown, ChevronUp, Package } from 'lucide-react'
import toast from 'react-hot-toast'
import { productsApi, taxesApi } from '../../api'

export default function ProductsPage() {
  const [showAdd, setShowAdd] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => productsApi.list({ per_page: 50 }).then(r => r.data),
  })
  const { data: taxes } = useQuery({
    queryKey: ['taxes'],
    queryFn: () => taxesApi.list().then(r => r.data),
  })

  const [form, setForm] = useState({
    name: '', product_type: 'software', description: '', notes: '',
    sales_price: '', cost_price: '', tax_ids: [] as string[],
  })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await productsApi.create({ ...form, sales_price: Number(form.sales_price), cost_price: Number(form.cost_price) })
      toast.success('Product created!')
      qc.invalidateQueries({ queryKey: ['products'] })
      setShowAdd(false)
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed.')
    }
  }

  const toggleTax = (id: string) =>
    setForm(f => ({ ...f, tax_ids: f.tax_ids.includes(id) ? f.tax_ids.filter(x => x !== id) : [...f.tax_ids, id] }))

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Products</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary"><Plus size={16} /> Add Product</button>
      </div>

      <div className="space-y-3">
        {(data?.items ?? []).map((p: any) => (
          <div key={p.id} className="card">
            <div
              className="px-6 py-4 flex items-center justify-between cursor-pointer"
              onClick={() => setExpanded(expanded === p.id ? null : p.id)}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Package size={18} className="text-blue-600" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900">{p.name}</p>
                  <p className="text-xs text-gray-500 capitalize">{p.product_type} · ₹{p.sales_price?.toFixed(0)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {p.is_active
                  ? <span className="badge-active">Active</span>
                  : <span className="badge-closed">Archived</span>}
                {expanded === p.id ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
              </div>
            </div>

            {expanded === p.id && (
              <div className="border-t border-gray-100 px-6 py-4">
                <p className="text-sm text-gray-600 mb-3">{p.description}</p>
                <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                  <div><span className="text-gray-500">Sales Price:</span> <span className="font-medium">₹{p.sales_price}</span></div>
                  <div><span className="text-gray-500">Cost Price:</span> <span className="font-medium">₹{p.cost_price}</span></div>
                  <div><span className="text-gray-500">Taxes:</span> <span>{p.taxes?.map((t: any) => t.name).join(', ') || 'None'}</span></div>
                </div>
                {p.variants.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-gray-700 mb-2">Variants</p>
                    <div className="space-y-1">
                      {p.variants.map((v: any) => (
                        <div key={v.id} className="flex items-center justify-between text-sm bg-gray-50 px-3 py-2 rounded-lg">
                          <span className="font-medium">{v.name}</span>
                          <div className="flex items-center gap-3 text-gray-500">
                            <span>+₹{v.price_modifier}</span>
                            <span className="font-medium text-gray-800">= ₹{v.effective_price?.toFixed(2)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-screen overflow-y-auto">
            <div className="p-6 border-b"><h2 className="text-lg font-semibold">Add Product</h2></div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div><label className="label">Product Name</label><input className="input" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} required /></div>
              <div>
                <label className="label">Type</label>
                <select className="input" value={form.product_type} onChange={e => setForm(f => ({...f, product_type: e.target.value}))}>
                  <option value="software">Software</option>
                  <option value="service">Service</option>
                  <option value="addon">Add-on</option>
                  <option value="hardware">Hardware</option>
                </select>
              </div>
              <div><label className="label">Description</label><input className="input" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Sales Price (₹)</label><input type="number" min="0" step="0.01" className="input" value={form.sales_price} onChange={e => setForm(f => ({...f, sales_price: e.target.value}))} required /></div>
                <div><label className="label">Cost Price (₹)</label><input type="number" min="0" step="0.01" className="input" value={form.cost_price} onChange={e => setForm(f => ({...f, cost_price: e.target.value}))} /></div>
              </div>
              <div>
                <label className="label">Taxes</label>
                <div className="space-y-1">
                  {(taxes ?? []).map((t: any) => (
                    <label key={t.id} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input type="checkbox" checked={form.tax_ids.includes(t.id)} onChange={() => toggleTax(t.id)} className="rounded" />
                      {t.name} ({t.percentage}%)
                    </label>
                  ))}
                </div>
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

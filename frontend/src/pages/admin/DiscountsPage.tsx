import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { discountsApi } from '../../api'
import { getStoredUser } from '../../hooks/useAuth'

export default function DiscountsPage() {
  const [showAdd, setShowAdd] = useState(false)
  const qc = useQueryClient()
  const user = getStoredUser()
  const isAdmin = user?.role === 'admin'

  const { data, isLoading } = useQuery({
    queryKey: ['discounts'],
    queryFn: () => discountsApi.list().then(r => r.data),
  })

  const [form, setForm] = useState({
    name: '', code: '', discount_type: 'percentage', value: '',
    min_purchase_amount: '0', min_quantity: '1',
    start_date: '', end_date: '', max_usage_count: '', notes: '',
  })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await discountsApi.create({
        ...form,
        value: Number(form.value),
        min_purchase_amount: Number(form.min_purchase_amount),
        min_quantity: Number(form.min_quantity),
        max_usage_count: form.max_usage_count ? Number(form.max_usage_count) : null,
      })
      toast.success('Discount created!')
      qc.invalidateQueries({ queryKey: ['discounts'] })
      setShowAdd(false)
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed.')
    }
  }

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Discounts</h1>
        {isAdmin && <button onClick={() => setShowAdd(true)} className="btn-primary"><Plus size={16} /> Add Discount</button>}
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                {['Name','Code','Type','Value','Min Amount','Usage','Dates','Status'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((d: any) => (
                <tr key={d.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{d.name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-blue-600">{d.code || '—'}</td>
                  <td className="px-4 py-3 capitalize">{d.discount_type}</td>
                  <td className="px-4 py-3">{d.discount_type === 'percentage' ? `${d.value}%` : `₹${d.value}`}</td>
                  <td className="px-4 py-3">₹{d.min_purchase_amount}</td>
                  <td className="px-4 py-3">{d.current_usage_count}{d.max_usage_count ? `/${d.max_usage_count}` : ''}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{d.start_date} → {d.end_date || '∞'}</td>
                  <td className="px-4 py-3">{d.is_active ? <span className="badge-active">Active</span> : <span className="badge-closed">Inactive</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showAdd && isAdmin && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-screen overflow-y-auto">
            <div className="p-6 border-b"><h2 className="text-lg font-semibold">Add Discount</h2></div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div><label className="label">Name</label><input className="input" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} required /></div>
              <div><label className="label">Code (optional)</label><input className="input uppercase" value={form.code} onChange={e => setForm(f => ({...f, code: e.target.value.toUpperCase()}))} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Type</label>
                  <select className="input" value={form.discount_type} onChange={e => setForm(f => ({...f, discount_type: e.target.value}))}>
                    <option value="percentage">Percentage</option>
                    <option value="fixed">Fixed Amount</option>
                  </select>
                </div>
                <div><label className="label">Value</label><input type="number" min="0" step="0.01" className="input" value={form.value} onChange={e => setForm(f => ({...f, value: e.target.value}))} required /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Min Purchase (₹)</label><input type="number" min="0" className="input" value={form.min_purchase_amount} onChange={e => setForm(f => ({...f, min_purchase_amount: e.target.value}))} /></div>
                <div><label className="label">Max Uses</label><input type="number" min="1" className="input" value={form.max_usage_count} onChange={e => setForm(f => ({...f, max_usage_count: e.target.value}))} placeholder="Unlimited" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">Start Date</label><input type="date" className="input" value={form.start_date} onChange={e => setForm(f => ({...f, start_date: e.target.value}))} /></div>
                <div><label className="label">End Date</label><input type="date" className="input" value={form.end_date} onChange={e => setForm(f => ({...f, end_date: e.target.value}))} /></div>
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

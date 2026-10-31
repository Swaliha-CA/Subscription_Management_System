import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import toast from 'react-hot-toast'
import { taxesApi } from '../../api'

export default function TaxesPage() {
  const [showAdd, setShowAdd] = useState(false)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['taxes'], queryFn: () => taxesApi.list().then(r => r.data) })
  const [form, setForm] = useState({ name: '', percentage: '', tax_type: 'GST', description: '' })

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await taxesApi.create({ ...form, percentage: Number(form.percentage) })
      toast.success('Tax created!')
      qc.invalidateQueries({ queryKey: ['taxes'] })
      setShowAdd(false)
    } catch (err: any) { toast.error(err.response?.data?.error || 'Failed.') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Taxes</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary"><Plus size={16} /> Add Tax</button>
      </div>
      <div className="card">
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 border-b">{['Name','Type','Rate','Description','Status'].map(h => (
            <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
          ))}</tr></thead>
          <tbody>
            {(data ?? []).map((t: any) => (
              <tr key={t.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{t.name}</td>
                <td className="px-4 py-3">{t.tax_type}</td>
                <td className="px-4 py-3 font-semibold">{t.percentage}%</td>
                <td className="px-4 py-3 text-gray-500">{t.description || '—'}</td>
                <td className="px-4 py-3">{t.is_active ? <span className="badge-active">Active</span> : <span className="badge-closed">Inactive</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm">
            <div className="p-6 border-b"><h2 className="text-lg font-semibold">Add Tax</h2></div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div><label className="label">Name</label><input className="input" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} required /></div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Type</label>
                  <select className="input" value={form.tax_type} onChange={e => setForm(f => ({...f, tax_type: e.target.value}))}>
                    {['GST','CGST','SGST','IGST','VAT'].map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div><label className="label">Rate (%)</label><input type="number" min="0" max="100" step="0.001" className="input" value={form.percentage} onChange={e => setForm(f => ({...f, percentage: e.target.value}))} required /></div>
              </div>
              <div><label className="label">Description</label><input className="input" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} /></div>
              <div className="flex gap-3">
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

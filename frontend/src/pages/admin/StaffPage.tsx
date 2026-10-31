import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, UserX } from 'lucide-react'
import toast from 'react-hot-toast'
import { staffApi } from '../../api'

export default function StaffPage() {
  const [showAdd, setShowAdd] = useState(false)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['staff'], queryFn: () => staffApi.list().then(r => r.data) })
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', phone: '', role: 'staff', password: '' })
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm(f => ({...f, [k]: e.target.value}))

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await staffApi.create(form)
      toast.success('Staff member created!')
      qc.invalidateQueries({ queryKey: ['staff'] })
      setShowAdd(false)
    } catch (err: any) { toast.error(err.response?.data?.error || 'Failed.') }
  }

  async function deactivate(id: string) {
    if (!confirm('Deactivate this staff member?')) return
    try {
      await staffApi.deactivate(id)
      toast.success('Staff member deactivated.')
      qc.invalidateQueries({ queryKey: ['staff'] })
    } catch (err: any) { toast.error(err.response?.data?.error || 'Failed.') }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Staff Management</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary"><Plus size={16} /> Add Staff</button>
      </div>
      <div className="card">
        <table className="w-full text-sm">
          <thead><tr className="bg-gray-50 border-b">{['Name','Email','Phone','Role','Last Login','Status','Actions'].map(h => (
            <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
          ))}</tr></thead>
          <tbody>
            {(data?.items ?? []).map((u: any) => (
              <tr key={u.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{u.full_name}</td>
                <td className="px-4 py-3 text-gray-600">{u.email}</td>
                <td className="px-4 py-3 text-gray-500">{u.phone || '—'}</td>
                <td className="px-4 py-3"><span className={`badge ${u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>{u.role}</span></td>
                <td className="px-4 py-3 text-xs text-gray-400">{u.last_login?.slice(0,10) || 'Never'}</td>
                <td className="px-4 py-3">{u.is_active ? <span className="badge-active">Active</span> : <span className="badge-closed">Inactive</span>}</td>
                <td className="px-4 py-3">
                  {u.is_active && (
                    <button onClick={() => deactivate(u.id)} className="btn-ghost p-1.5 text-red-500 hover:bg-red-50">
                      <UserX size={14} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="p-6 border-b"><h2 className="text-lg font-semibold">Add Staff Member</h2></div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">First Name</label><input className="input" value={form.first_name} onChange={set('first_name')} required /></div>
                <div><label className="label">Last Name</label><input className="input" value={form.last_name} onChange={set('last_name')} required /></div>
              </div>
              <div><label className="label">Email</label><input type="email" className="input" value={form.email} onChange={set('email')} required /></div>
              <div><label className="label">Phone</label><input className="input" value={form.phone} onChange={set('phone')} /></div>
              <div>
                <label className="label">Role</label>
                <select className="input" value={form.role} onChange={set('role')}>
                  <option value="staff">Staff</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label className="label">Password</label>
                <input type="password" className="input" value={form.password} onChange={set('password')} required placeholder="Min 9 chars, upper, lower, special" />
              </div>
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

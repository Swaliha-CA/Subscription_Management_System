import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getStoredUser, setAuth } from '../../hooks/useAuth'
import { authApi, customersApi } from '../../api'
import toast from 'react-hot-toast'

export default function CustomerProfile() {
  const user = getStoredUser()
  const customerId = user?.customer_id
  const qc = useQueryClient()

  const { data: customer, isLoading } = useQuery({
    queryKey: ['my-profile', customerId],
    queryFn: () => customersApi.get(customerId!).then(r => r.data),
    enabled: !!customerId,
  })

  const [editMode, setEditMode] = useState(false)
  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '', company_name: '', city: '' })
  const [pwdForm, setPwdForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [showPwd, setShowPwd] = useState(false)

  function startEdit() {
    if (customer) {
      setForm({
        first_name: customer.first_name || '',
        last_name: customer.last_name || '',
        phone: customer.phone || '',
        company_name: customer.company_name || '',
        city: customer.city || '',
      })
    }
    setEditMode(true)
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    try {
      await customersApi.update(customerId!, form)
      // Update stored user
      const { data: me } = await authApi.me()
      const token = localStorage.getItem('access_token')!
      setAuth(me, token)
      toast.success('Profile updated!')
      qc.invalidateQueries({ queryKey: ['my-profile'] })
      setEditMode(false)
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Update failed.')
    }
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault()
    if (pwdForm.new_password !== pwdForm.confirm) {
      toast.error('Passwords do not match.')
      return
    }
    try {
      await authApi.changePassword(pwdForm.current_password, pwdForm.new_password)
      toast.success('Password changed!')
      setPwdForm({ current_password: '', new_password: '', confirm: '' })
      setShowPwd(false)
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed.')
    }
  }

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>

      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Account Information</h3>
          {!editMode && <button onClick={startEdit} className="btn-secondary text-sm">Edit</button>}
        </div>
        <div className="p-6">
          {!editMode ? (
            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                ['Full Name', customer?.full_name],
                ['Email', customer?.email],
                ['Phone', customer?.phone || '—'],
                ['Company', customer?.company_name || '—'],
                ['City', customer?.city || '—'],
                ['Customer Code', customer?.customer_code],
                ['GSTIN', customer?.gstin || '—'],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-gray-400 text-xs">{k}</p>
                  <p className="font-medium text-gray-800">{v}</p>
                </div>
              ))}
            </div>
          ) : (
            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">First Name</label><input className="input" value={form.first_name} onChange={e => setForm(f => ({...f, first_name: e.target.value}))} /></div>
                <div><label className="label">Last Name</label><input className="input" value={form.last_name} onChange={e => setForm(f => ({...f, last_name: e.target.value}))} /></div>
              </div>
              <div><label className="label">Phone</label><input className="input" value={form.phone} onChange={e => setForm(f => ({...f, phone: e.target.value}))} /></div>
              <div><label className="label">Company</label><input className="input" value={form.company_name} onChange={e => setForm(f => ({...f, company_name: e.target.value}))} /></div>
              <div><label className="label">City</label><input className="input" value={form.city} onChange={e => setForm(f => ({...f, city: e.target.value}))} /></div>
              <div className="flex gap-3">
                <button type="submit" className="btn-primary">Save Changes</button>
                <button type="button" onClick={() => setEditMode(false)} className="btn-secondary">Cancel</button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Change password */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Security</h3>
          {!showPwd && <button onClick={() => setShowPwd(true)} className="btn-secondary text-sm">Change Password</button>}
        </div>
        {showPwd && (
          <form onSubmit={handlePasswordChange} className="p-6 space-y-4">
            <div><label className="label">Current Password</label><input type="password" className="input" value={pwdForm.current_password} onChange={e => setPwdForm(f => ({...f, current_password: e.target.value}))} required /></div>
            <div><label className="label">New Password</label><input type="password" className="input" value={pwdForm.new_password} onChange={e => setPwdForm(f => ({...f, new_password: e.target.value}))} required /></div>
            <div><label className="label">Confirm New Password</label><input type="password" className="input" value={pwdForm.confirm} onChange={e => setPwdForm(f => ({...f, confirm: e.target.value}))} required /></div>
            <div className="flex gap-3">
              <button type="submit" className="btn-primary">Update Password</button>
              <button type="button" onClick={() => setShowPwd(false)} className="btn-secondary">Cancel</button>
            </div>
          </form>
        )}
        {!showPwd && <p className="px-6 pb-4 text-sm text-gray-400">Use a strong password with uppercase, lowercase, and special characters.</p>}
      </div>
    </div>
  )
}

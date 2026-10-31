import { useState, FormEvent } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '../../api'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (password !== confirm) { toast.error('Passwords do not match.'); return }
    setLoading(true)
    try {
      await authApi.resetPassword(token, password)
      toast.success('Password updated! Please log in.')
      navigate('/login')
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Reset failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center">
              <Zap size={20} className="text-white" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">Set New Password</h2>
          </div>
          {!token && (
            <div className="p-3 bg-red-50 rounded-lg text-red-800 text-sm mb-4">
              Invalid or missing reset token. <Link to="/forgot-password" className="underline">Request a new one.</Link>
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">New password</label>
              <input type="password" className="input" value={password} onChange={e => setPassword(e.target.value)} required />
              <p className="text-xs text-gray-400 mt-1">Min 9 chars, uppercase, lowercase, special character</p>
            </div>
            <div>
              <label className="label">Confirm password</label>
              <input type="password" className="input" value={confirm} onChange={e => setConfirm(e.target.value)} required />
            </div>
            <button type="submit" disabled={loading || !token} className="btn-primary w-full justify-center py-2.5">
              {loading ? 'Updating…' : 'Update password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

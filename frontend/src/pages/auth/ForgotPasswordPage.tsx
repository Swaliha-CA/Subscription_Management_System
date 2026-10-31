import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Zap, ArrowLeft } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '../../api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.forgotPassword(email)
      setResult(data)
      toast.success(data.message)
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Request failed.')
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
            <h2 className="text-xl font-bold text-gray-900">Reset Password</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email address</label>
              <input
                type="email"
                className="input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-2.5">
              {loading ? 'Sending…' : 'Send reset link'}
            </button>
          </form>

          {result && (
            <div className="mt-4 p-3 bg-green-50 rounded-lg text-sm text-green-800">
              <p>{result.message}</p>
              {result.dev_token && (
                <div className="mt-2 p-2 bg-amber-50 rounded text-amber-800 text-xs">
                  <p className="font-semibold">Dev mode — use this token:</p>
                  <p className="font-mono break-all mt-1">{result.dev_token}</p>
                </div>
              )}
            </div>
          )}

          <div className="mt-6 text-center">
            <Link to="/login" className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1">
              <ArrowLeft size={14} /> Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

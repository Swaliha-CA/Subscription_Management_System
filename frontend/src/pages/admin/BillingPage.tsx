import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Zap, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { billingApi } from '../../api'

export default function BillingPage() {
  const [running, setRunning] = useState(false)
  const [lastResult, setLastResult] = useState<any>(null)
  const qc = useQueryClient()

  const { data: due } = useQuery({
    queryKey: ['billing-due'],
    queryFn: () => billingApi.dueCount().then(r => r.data),
    refetchInterval: 30_000,
  })

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['billing-logs'],
    queryFn: () => billingApi.logs({ per_page: 20 }).then(r => r.data),
  })

  async function runBilling() {
    setRunning(true)
    try {
      const { data } = await billingApi.run()
      setLastResult(data)
      toast.success(`Billing complete: ${data.invoices_generated} invoices generated`)
      qc.invalidateQueries({ queryKey: ['billing-due'] })
      refetch()
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Billing failed.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Billing Engine</h1>
      </div>

      {/* Status card */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-6">
          <h3 className="font-semibold text-gray-800 mb-4">Current Status</h3>
          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center">
              <Zap size={28} className="text-blue-600" />
            </div>
            <div>
              <p className="text-3xl font-bold text-gray-900">{due?.due_count ?? '—'}</p>
              <p className="text-sm text-gray-500">subscriptions due for billing</p>
            </div>
          </div>
          <button
            onClick={runBilling}
            disabled={running}
            className="btn-primary w-full justify-center"
          >
            {running ? (
              <><RefreshCw size={16} className="animate-spin" /> Running…</>
            ) : (
              <><Zap size={16} /> Run Billing Now</>
            )}
          </button>
          <p className="text-xs text-gray-400 mt-2 text-center">
            Automatic billing runs daily at 00:05 IST
          </p>
        </div>

        {lastResult && (
          <div className="card p-6">
            <h3 className="font-semibold text-gray-800 mb-4">Last Run Result</h3>
            <div className="space-y-2 text-sm">
              {[
                ['Subscriptions Due', lastResult.subscriptions_due],
                ['Invoices Generated', lastResult.invoices_generated],
                ['Invoices Skipped', lastResult.invoices_skipped],
                ['Invoices Failed', lastResult.invoices_failed],
                ['Total Billed', `₹${lastResult.total_billed?.toFixed(2)}`],
                ['Status', lastResult.status],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-gray-500">{k}</span>
                  <span className={`font-medium ${k === 'Invoices Failed' && Number(v) > 0 ? 'text-red-600' : ''}`}>{v}</span>
                </div>
              ))}
            </div>
            {lastResult.errors?.length > 0 && (
              <div className="mt-3 p-3 bg-red-50 rounded-lg text-xs text-red-700">
                <p className="font-semibold mb-1">Errors:</p>
                {lastResult.errors.map((e: any, i: number) => (
                  <p key={i} className="font-mono">{e.subscription_id}: {e.error}</p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Billing logs */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Billing Execution History</h3>
          <button onClick={() => refetch()} className="btn-ghost p-2"><RefreshCw size={15} /></button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                {['Started','Type','Due','Generated','Skipped','Failed','Total Billed','Status'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(logs?.items ?? []).map((l: any) => (
                <tr key={l.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs text-gray-500">{l.started_at?.slice(0, 19).replace('T', ' ')}</td>
                  <td className="px-4 py-2 capitalize"><span className={`badge ${l.run_type === 'manual' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>{l.run_type}</span></td>
                  <td className="px-4 py-2">{l.subscriptions_due}</td>
                  <td className="px-4 py-2 text-emerald-600 font-medium">{l.invoices_generated}</td>
                  <td className="px-4 py-2 text-amber-600">{l.invoices_skipped}</td>
                  <td className="px-4 py-2 text-red-600">{l.invoices_failed}</td>
                  <td className="px-4 py-2 font-medium">₹{l.total_billed?.toFixed(2)}</td>
                  <td className="px-4 py-2">
                    <span className={l.status === 'completed' ? 'badge-active' : 'badge-paused'}>{l.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

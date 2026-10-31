import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Mail, Phone, Building2, MapPin } from 'lucide-react'
import { customersApi, subscriptionsApi, invoicesApi } from '../../api'
import StatusBadge from '../../components/ui/StatusBadge'

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: customer, isLoading } = useQuery({
    queryKey: ['customer', id],
    queryFn: () => customersApi.get(id!).then(r => r.data),
  })
  const { data: subs } = useQuery({
    queryKey: ['customer-subs', id],
    queryFn: () => subscriptionsApi.list({ customer_id: id, per_page: 10 }).then(r => r.data),
  })
  const { data: invoices } = useQuery({
    queryKey: ['customer-invoices', id],
    queryFn: () => invoicesApi.list({ customer_id: id, per_page: 5 }).then(r => r.data),
  })

  if (isLoading) return <div className="skeleton h-64 rounded-xl" />

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="btn-ghost p-2">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{customer?.full_name}</h1>
          <p className="text-sm text-gray-500 font-mono">{customer?.customer_code}</p>
        </div>
        <div className="ml-auto">
          {customer?.is_active
            ? <span className="badge-active">Active</span>
            : <span className="badge-closed">Inactive</span>}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Profile */}
        <div className="card p-6 space-y-3">
          <h3 className="font-semibold text-gray-800 mb-2">Contact Information</h3>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Mail size={15} className="text-gray-400" />
            {customer?.email}
          </div>
          {customer?.phone && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Phone size={15} className="text-gray-400" />
              {customer.phone}
            </div>
          )}
          {customer?.company_name && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Building2 size={15} className="text-gray-400" />
              {customer.company_name}
            </div>
          )}
          {(customer?.city || customer?.state) && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <MapPin size={15} className="text-gray-400" />
              {[customer.city, customer.state, customer.country].filter(Boolean).join(', ')}
            </div>
          )}
          {customer?.gstin && <p className="text-xs text-gray-400">GSTIN: {customer.gstin}</p>}
        </div>

        {/* Subscriptions */}
        <div className="card p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Subscriptions</h3>
          {(subs?.items ?? []).length === 0
            ? <p className="text-sm text-gray-400">No subscriptions.</p>
            : (subs?.items ?? []).map((s: any) => (
              <div key={s.id} onClick={() => navigate(`/subscriptions/${s.id}`)}
                className="flex items-center justify-between py-2 border-b border-gray-100 cursor-pointer hover:bg-gray-50 px-1 rounded">
                <div>
                  <p className="text-sm font-medium text-blue-600 font-mono">{s.subscription_number}</p>
                  <p className="text-xs text-gray-500">{s.plan_name}</p>
                </div>
                <StatusBadge status={s.status} />
              </div>
            ))
          }
        </div>

        {/* Invoices */}
        <div className="card p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Recent Invoices</h3>
          {(invoices?.items ?? []).length === 0
            ? <p className="text-sm text-gray-400">No invoices.</p>
            : (invoices?.items ?? []).map((i: any) => (
              <div key={i.id} onClick={() => navigate(`/invoices/${i.id}`)}
                className="flex items-center justify-between py-2 border-b border-gray-100 cursor-pointer hover:bg-gray-50 px-1 rounded">
                <div>
                  <p className="text-sm font-medium text-blue-600 font-mono">{i.invoice_number}</p>
                  <p className="text-xs text-gray-500">₹{i.grand_total?.toFixed(0)}</p>
                </div>
                <StatusBadge status={i.status} />
              </div>
            ))
          }
        </div>
      </div>
    </div>
  )
}

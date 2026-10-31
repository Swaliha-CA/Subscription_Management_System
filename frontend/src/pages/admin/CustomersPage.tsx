import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import toast from 'react-hot-toast'
import { customersApi } from '../../api'
import Table from '../../components/ui/Table'
import Pagination from '../../components/ui/Pagination'

export default function CustomersPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['customers', page, search],
    queryFn: () => customersApi.list({ page, per_page: 20, search }).then(r => r.data),
  })

  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '',
    company_name: '', city: '', state: '', country: 'India',
    password: 'Customer@123',
  })
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await customersApi.create(form)
      toast.success('Customer created!')
      qc.invalidateQueries({ queryKey: ['customers'] })
      setShowAdd(false)
      setForm({ first_name: '', last_name: '', email: '', phone: '', company_name: '', city: '', state: '', country: 'India', password: 'Customer@123' })
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed to create customer.')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary">
          <Plus size={16} /> Add Customer
        </button>
      </div>

      <div className="card">
        <div className="card-header flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="input pl-9"
              placeholder="Search customers…"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
            />
          </div>
          <span className="text-sm text-gray-500">{data?.total ?? 0} customers</span>
        </div>

        <Table
          loading={isLoading}
          data={data?.items ?? []}
          keyExtractor={r => r.id}
          onRowClick={r => navigate(`/customers/${r.id}`)}
          columns={[
            { header: 'Code', render: r => <span className="font-mono text-xs text-blue-600">{r.customer_code}</span> },
            { header: 'Name', render: r => <span className="font-medium">{r.full_name}</span> },
            { header: 'Email', key: 'email' },
            { header: 'Company', key: 'company_name' },
            { header: 'City', key: 'city' },
            { header: 'Status', render: r => r.is_active
              ? <span className="badge-active">Active</span>
              : <span className="badge-closed">Inactive</span>
            },
          ]}
        />
        <Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} perPage={20} onPageChange={setPage} />
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-screen overflow-y-auto">
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold">Add Customer</h2>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">First name</label><input className="input" value={form.first_name} onChange={set('first_name')} required /></div>
                <div><label className="label">Last name</label><input className="input" value={form.last_name} onChange={set('last_name')} required /></div>
              </div>
              <div><label className="label">Email</label><input type="email" className="input" value={form.email} onChange={set('email')} required /></div>
              <div><label className="label">Phone</label><input className="input" value={form.phone} onChange={set('phone')} /></div>
              <div><label className="label">Company</label><input className="input" value={form.company_name} onChange={set('company_name')} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="label">City</label><input className="input" value={form.city} onChange={set('city')} /></div>
                <div><label className="label">State</label><input className="input" value={form.state} onChange={set('state')} /></div>
              </div>
              <div><label className="label">Initial password</label><input className="input" value={form.password} onChange={set('password')} required /></div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="btn-primary flex-1 justify-center">Create Customer</button>
                <button type="button" onClick={() => setShowAdd(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

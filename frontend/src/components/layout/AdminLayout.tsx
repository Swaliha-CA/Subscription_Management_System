import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Users, Package, CreditCard, FileText,
  BarChart3, Settings, LogOut, ChevronLeft, ChevronRight,
  Zap, Tag, Receipt, RefreshCw, Shield, DollarSign, Menu, X, Percent
} from 'lucide-react'
import { getStoredUser, logout } from '../../hooks/useAuth'

const adminNav = [
  { to: '/dashboard',     icon: LayoutDashboard, label: 'Overview' },
  { to: '/customers',     icon: Users,            label: 'Customers' },
  { to: '/products',      icon: Package,          label: 'Products' },
  { to: '/plans',         icon: CreditCard,       label: 'Plans' },
  { to: '/quotations',    icon: FileText,         label: 'Quotations' },
  { to: '/subscriptions', icon: RefreshCw,        label: 'Subscriptions' },
  { to: '/invoices',      icon: Receipt,          label: 'Invoices' },
  { to: '/payments',      icon: DollarSign,       label: 'Payments' },
  { to: '/discounts',     icon: Tag,              label: 'Discounts' },
  { to: '/taxes',         icon: Percent,          label: 'Taxes' },
  { to: '/billing',       icon: Zap,              label: 'Billing Engine' },
  { to: '/reports',       icon: BarChart3,        label: 'Reports' },
]

const adminOnlyNav = [
  { to: '/staff', icon: Shield, label: 'Staff' },
]

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const user = getStoredUser()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const navItems = user?.role === 'admin'
    ? [...adminNav, ...adminOnlyNav]
    : adminNav

  const Sidebar = ({ mobile = false }) => (
    <div className={`flex flex-col h-full bg-slate-900 text-white transition-all duration-200 ${
      mobile ? 'w-64' : collapsed ? 'w-16' : 'w-64'
    }`}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-700">
        <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        {(!collapsed || mobile) && (
          <div>
            <div className="font-bold text-white text-sm">SubscriptIQ</div>
            <div className="text-slate-400 text-xs">Revenue Platform</div>
          </div>
        )}
        {!mobile && (
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="ml-auto text-slate-400 hover:text-white p-1 rounded"
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        )}
      </div>

      {/* User info */}
      {(!collapsed || mobile) && (
        <div className="px-4 py-3 border-b border-slate-700">
          <div className="text-xs text-slate-400 uppercase font-semibold tracking-wider mb-1">Signed in as</div>
          <div className="text-sm font-medium text-white truncate">{user?.full_name}</div>
          <div className="text-xs text-slate-400 capitalize">{user?.role}</div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              isActive ? 'sidebar-link-active' : 'sidebar-link'
            }
            title={collapsed && !mobile ? label : undefined}
          >
            <Icon size={18} className="flex-shrink-0" />
            {(!collapsed || mobile) && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="px-2 py-3 border-t border-slate-700">
        <button
          onClick={handleLogout}
          className="sidebar-link w-full"
          title={collapsed && !mobile ? 'Logout' : undefined}
        >
          <LogOut size={18} className="flex-shrink-0" />
          {(!collapsed || mobile) && <span>Logout</span>}
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex flex-col flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0">
            <Sidebar mobile />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar (mobile) */}
        <div className="lg:hidden flex items-center px-4 py-3 border-b border-gray-200 bg-white">
          <button onClick={() => setMobileOpen(true)} className="text-gray-600">
            <Menu size={22} />
          </button>
          <div className="ml-3 font-semibold text-gray-800">SubscriptIQ</div>
        </div>

        <main className="flex-1 overflow-auto bg-gray-50 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

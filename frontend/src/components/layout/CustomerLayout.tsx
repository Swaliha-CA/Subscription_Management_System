import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, RefreshCw, Receipt, DollarSign, User, LogOut, Zap } from 'lucide-react'
import { getStoredUser, logout } from '../../hooks/useAuth'

const nav = [
  { to: '/portal',               icon: LayoutDashboard, label: 'Home',          exact: true },
  { to: '/portal/subscriptions', icon: RefreshCw,       label: 'Subscriptions' },
  { to: '/portal/invoices',      icon: Receipt,         label: 'Invoices' },
  { to: '/portal/payments',      icon: DollarSign,      label: 'Payments' },
  { to: '/portal/profile',       icon: User,            label: 'Profile' },
]

export default function CustomerLayout() {
  const user = getStoredUser()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top navigation */}
      <nav className="bg-slate-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <Zap size={16} />
              </div>
              <div>
                <div className="font-bold text-sm">SubscriptIQ</div>
                <div className="text-slate-400 text-xs">Customer Portal</div>
              </div>
            </div>

            {/* Nav links */}
            <div className="hidden sm:flex items-center gap-1">
              {nav.map(({ to, icon: Icon, label, exact }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={exact}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-300 hover:text-white hover:bg-slate-700'
                    }`
                  }
                >
                  <Icon size={16} />
                  {label}
                </NavLink>
              ))}
            </div>

            {/* User + logout */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-300 hidden md:block">{user?.full_name}</span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-slate-400 hover:text-white px-3 py-2 rounded-lg hover:bg-slate-700 text-sm transition-colors"
              >
                <LogOut size={16} />
                <span className="hidden sm:block">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile nav */}
      <div className="sm:hidden bg-slate-800 border-t border-slate-700">
        <div className="flex overflow-x-auto">
          {nav.map(({ to, icon: Icon, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                `flex flex-col items-center gap-1 px-4 py-3 text-xs font-medium whitespace-nowrap flex-shrink-0 ${
                  isActive ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-400'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}

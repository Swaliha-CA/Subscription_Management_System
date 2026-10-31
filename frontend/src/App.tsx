import { Routes, Route, Navigate } from 'react-router-dom'
import { getStoredUser } from './hooks/useAuth'

// Auth pages
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage'
import ResetPasswordPage from './pages/auth/ResetPasswordPage'

// Admin/Staff layout
import AdminLayout from './components/layout/AdminLayout'
import DashboardPage from './pages/admin/DashboardPage'
import CustomersPage from './pages/admin/CustomersPage'
import CustomerDetailPage from './pages/admin/CustomerDetailPage'
import ProductsPage from './pages/admin/ProductsPage'
import PlansPage from './pages/admin/PlansPage'
import QuotationsPage from './pages/admin/QuotationsPage'
import QuotationDetailPage from './pages/admin/QuotationDetailPage'
import SubscriptionsPage from './pages/admin/SubscriptionsPage'
import SubscriptionDetailPage from './pages/admin/SubscriptionDetailPage'
import InvoicesPage from './pages/admin/InvoicesPage'
import InvoiceDetailPage from './pages/admin/InvoiceDetailPage'
import PaymentsPage from './pages/admin/PaymentsPage'
import DiscountsPage from './pages/admin/DiscountsPage'
import ReportsPage from './pages/admin/ReportsPage'
import StaffPage from './pages/admin/StaffPage'
import BillingPage from './pages/admin/BillingPage'
import TaxesPage from './pages/admin/TaxesPage'

// Customer portal
import CustomerLayout from './components/layout/CustomerLayout'
import CustomerDashboard from './pages/customer/CustomerDashboard'
import CustomerSubscriptions from './pages/customer/CustomerSubscriptions'
import CustomerInvoices from './pages/customer/CustomerInvoices'
import CustomerPayments from './pages/customer/CustomerPayments'
import CustomerProfile from './pages/customer/CustomerProfile'

function ProtectedRoute({ children, roles }: { children: JSX.Element; roles?: string[] }) {
  const user = getStoredUser()
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) {
    return user.role === 'customer'
      ? <Navigate to="/portal" replace />
      : <Navigate to="/dashboard" replace />
  }
  return children
}

export default function App() {
  const user = getStoredUser()

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {/* Admin / Staff */}
      <Route path="/" element={
        <ProtectedRoute roles={['admin', 'staff']}>
          <AdminLayout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="customers" element={<CustomersPage />} />
        <Route path="customers/:id" element={<CustomerDetailPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="plans" element={<PlansPage />} />
        <Route path="quotations" element={<QuotationsPage />} />
        <Route path="quotations/:id" element={<QuotationDetailPage />} />
        <Route path="subscriptions" element={<SubscriptionsPage />} />
        <Route path="subscriptions/:id" element={<SubscriptionDetailPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route path="invoices/:id" element={<InvoiceDetailPage />} />
        <Route path="payments" element={<PaymentsPage />} />
        <Route path="discounts" element={<DiscountsPage />} />
        <Route path="taxes" element={<TaxesPage />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="staff" element={
          <ProtectedRoute roles={['admin']}>
            <StaffPage />
          </ProtectedRoute>
        } />
      </Route>

      {/* Customer portal */}
      <Route path="/portal" element={
        <ProtectedRoute roles={['customer']}>
          <CustomerLayout />
        </ProtectedRoute>
      }>
        <Route index element={<CustomerDashboard />} />
        <Route path="subscriptions" element={<CustomerSubscriptions />} />
        <Route path="invoices" element={<CustomerInvoices />} />
        <Route path="payments" element={<CustomerPayments />} />
        <Route path="profile" element={<CustomerProfile />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={
        user
          ? <Navigate to={user.role === 'customer' ? '/portal' : '/dashboard'} replace />
          : <Navigate to="/login" replace />
      } />
    </Routes>
  )
}

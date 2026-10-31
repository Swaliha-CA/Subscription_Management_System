import api from './client'

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: object) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  forgotPassword: (email: string) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token: string, password: string) =>
    api.post('/auth/reset-password', { token, password }),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password', { current_password, new_password }),
}

// ── Customers ────────────────────────────────────────────────────────────────
export const customersApi = {
  list: (params?: object) => api.get('/customers', { params }),
  get: (id: string) => api.get(`/customers/${id}`),
  create: (data: object) => api.post('/customers', data),
  update: (id: string, data: object) => api.put(`/customers/${id}`, data),
  summary: (id: string) => api.get(`/customers/${id}/summary`),
}

// ── Products ─────────────────────────────────────────────────────────────────
export const productsApi = {
  list: (params?: object) => api.get('/products', { params }),
  get: (id: string) => api.get(`/products/${id}`),
  create: (data: object) => api.post('/products', data),
  update: (id: string, data: object) => api.put(`/products/${id}`, data),
  addVariant: (productId: string, data: object) => api.post(`/products/${productId}/variants`, data),
  updateVariant: (productId: string, variantId: string, data: object) =>
    api.put(`/products/${productId}/variants/${variantId}`, data),
}

// ── Plans ────────────────────────────────────────────────────────────────────
export const plansApi = {
  list: (params?: object) => api.get('/plans', { params }),
  get: (id: string) => api.get(`/plans/${id}`),
  create: (data: object) => api.post('/plans', data),
  update: (id: string, data: object) => api.put(`/plans/${id}`, data),
}

// ── Quotations ───────────────────────────────────────────────────────────────
export const quotationsApi = {
  list: (params?: object) => api.get('/quotations', { params }),
  get: (id: string) => api.get(`/quotations/${id}`),
  create: (data: object) => api.post('/quotations', data),
  update: (id: string, data: object) => api.put(`/quotations/${id}`, data),
  confirm: (id: string) => api.post(`/quotations/${id}/confirm`),
  convert: (id: string, data?: object) => api.post(`/quotations/${id}/convert`, data || {}),
  listTemplates: () => api.get('/quotations/templates'),
  createTemplate: (data: object) => api.post('/quotations/templates', data),
}

// ── Subscriptions ────────────────────────────────────────────────────────────
export const subscriptionsApi = {
  list: (params?: object) => api.get('/subscriptions', { params }),
  get: (id: string) => api.get(`/subscriptions/${id}`),
  create: (data: object) => api.post('/subscriptions', data),
  activate: (id: string) => api.post(`/subscriptions/${id}/activate`),
  pause: (id: string) => api.post(`/subscriptions/${id}/pause`),
  resume: (id: string) => api.post(`/subscriptions/${id}/resume`),
  renew: (id: string, data?: object) => api.post(`/subscriptions/${id}/renew`, data || {}),
  close: (id: string) => api.post(`/subscriptions/${id}/close`),
  cancel: (id: string) => api.post(`/subscriptions/${id}/cancel`),
}

// ── Billing ──────────────────────────────────────────────────────────────────
export const billingApi = {
  run: () => api.post('/billing/run'),
  dueCount: () => api.get('/billing/due-count'),
  logs: (params?: object) => api.get('/billing/logs', { params }),
}

// ── Invoices ─────────────────────────────────────────────────────────────────
export const invoicesApi = {
  list: (params?: object) => api.get('/invoices', { params }),
  get: (id: string) => api.get(`/invoices/${id}`),
  create: (data: object) => api.post('/invoices', data),
  confirm: (id: string) => api.post(`/invoices/${id}/confirm`),
  cancel: (id: string) => api.post(`/invoices/${id}/cancel`),
  sendReminder: (id: string) => api.post(`/invoices/${id}/send-reminder`),
}

// ── Payments ─────────────────────────────────────────────────────────────────
export const paymentsApi = {
  list: (params?: object) => api.get('/payments', { params }),
  get: (id: string) => api.get(`/payments/${id}`),
  record: (data: object) => api.post('/payments', data),
}

// ── Discounts ────────────────────────────────────────────────────────────────
export const discountsApi = {
  list: (params?: object) => api.get('/discounts', { params }),
  get: (id: string) => api.get(`/discounts/${id}`),
  create: (data: object) => api.post('/discounts', data),
  update: (id: string, data: object) => api.put(`/discounts/${id}`, data),
  validate: (data: object) => api.post('/discounts/validate', data),
}

// ── Taxes ────────────────────────────────────────────────────────────────────
export const taxesApi = {
  list: () => api.get('/taxes'),
  create: (data: object) => api.post('/taxes', data),
  update: (id: string, data: object) => api.put(`/taxes/${id}`, data),
}

// ── Reports ──────────────────────────────────────────────────────────────────
export const reportsApi = {
  dashboard: () => api.get('/reports/dashboard'),
  overdue: (params?: object) => api.get('/reports/overdue', { params }),
  mrrArr: () => api.get('/reports/mrr-arr'),
  subscriptions: (params?: object) => api.get('/reports/subscriptions', { params }),
  revenue: (params?: object) => api.get('/reports/revenue', { params }),
  auditLogs: (params?: object) => api.get('/reports/audit-logs', { params }),
  forecast: () => api.get('/reports/forecast'),
}

// ── Staff ────────────────────────────────────────────────────────────────────
export const staffApi = {
  list: (params?: object) => api.get('/staff', { params }),
  create: (data: object) => api.post('/staff', data),
  update: (id: string, data: object) => api.put(`/staff/${id}`, data),
  deactivate: (id: string) => api.post(`/staff/${id}/deactivate`),
}

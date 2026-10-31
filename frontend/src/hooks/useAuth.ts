// localStorage-based auth helpers

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: 'admin' | 'staff' | 'customer'
  is_active: boolean
  customer_id?: string
}

export function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function getToken(): string | null {
  return localStorage.getItem('access_token')
}

export function setAuth(user: User, token: string) {
  localStorage.setItem('access_token', token)
  localStorage.setItem('user', JSON.stringify(user))
}

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
}

export function isAuthenticated(): boolean {
  return !!getToken() && !!getStoredUser()
}

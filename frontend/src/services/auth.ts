
import api from '../lib/api'
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
} from '../types/auth'

const TOKEN_KEY = 'ledgerline_access_token'
const USER_KEY = 'ledgerline_user'

export async function loginUser(
  credentials: LoginRequest,
): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>(
    '/auth/login',
    credentials,
  )

  const data = response.data

  sessionStorage.setItem(TOKEN_KEY, data.access_token)
  sessionStorage.setItem(USER_KEY, JSON.stringify(data.user))

  return data
}

export async function registerUser(
  details: RegisterRequest,
): Promise<User> {
  const response = await api.post<User>(
    '/auth/register',
    details,
  )

  return response.data
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get<User>('/auth/me')

  sessionStorage.setItem(USER_KEY, JSON.stringify(response.data))

  return response.data
}

export function logoutUser(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function getStoredUser(): User | null {
  const storedUser = sessionStorage.getItem(USER_KEY)

  if (!storedUser) return null

  try {
    return JSON.parse(storedUser) as User
  } catch {
    sessionStorage.removeItem(USER_KEY)
    return null
  }
}


export type UserRole = 'ADMIN' | 'ACCOUNT_HOLDER' | 'AUDITOR'

export interface User {
  id: string
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  full_name: string
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

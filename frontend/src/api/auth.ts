import http from './http'

export interface LoginPayload {
  id: string
  password: string
}

export interface RegisterPayload {
  id: string
  name: string
  password: string
  role: string
  major?: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: { id: string; name: string; role: string; major?: string }
}

export function login(data: LoginPayload) {
  return http.post<any, LoginResult>('/token', data)
}

export function register(data: RegisterPayload) {
  return http.post<any, { success: boolean; message: string }>('/register', data)
}

export function getMe() {
  return http.get<any, { id: string; name: string; role: string; major?: string }>('/me')
}

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
  user: { id: string; name: string; role: string; major?: string; needs_password_change?: boolean }
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

// 修改密码（需登录态，旧密码 + 新密码）
export function changePassword(data: { old_password: string; new_password: string }) {
  return http.put<any, { message: string }>('/change-password', data)
}

// 忘记密码（直接用学号/工号重置，无需登录）
export function forgotPassword(data: { id: string; new_password: string }) {
  return http.post<any, { message: string }>('/password/forgot', data)
}

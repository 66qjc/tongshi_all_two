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
  return http.put<any, { message: string; access_token: string }>('/change-password', data)
}

// ── 密保问题管理（需登录）─────────────────────────────────────────────

export interface SecurityQuestionItem {
  id: number
  question: string
}

export function getSecurityQuestions() {
  return http.get<any, SecurityQuestionItem[]>('/security-questions')
}

export function updateSecurityQuestions(data: { questions: { question: string; answer: string }[] }) {
  return http.put<any, SecurityQuestionItem[]>('/security-questions', data)
}

// ── 忘记密码新流程（无需登录）─────────────────────────────────────────

/** 获取指定用户的密保问题列表（只返回问题文本） */
export function getForgotPasswordQuestions(userId: string) {
  return http.get<any, SecurityQuestionItem[]>(`/password/forgot/questions?user_id=${encodeURIComponent(userId)}`)
}

/** 提交答案并重置密码 */
export function resetPasswordWithAnswers(data: {
  user_id: string
  answers: { question_id: number; answer: string }[]
  new_password: string
}) {
  return http.post<any, { message: string }>('/password/forgot/reset', data)
}

/** 提交人工密码重置申请 */
export function submitPasswordResetRequest(data: { user_id: string; message: string }) {
  return http.post<any, { message: string }>('/password/forgot/request', data)
}

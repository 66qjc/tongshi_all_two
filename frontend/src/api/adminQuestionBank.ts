import http from './http'
import type { Question } from './question'

export interface AdminQuestionBankPayload {
  type: 'choice' | 'fill' | 'multi_choice'
  stem: string
  options: string[]
  answer: string
  explanation: string
  tags: string[]
  star_rating: number
}

export interface AdminQuestionBankContribution {
  id: number
  public_course_id: number | null
  public_course_name: string
  operator_id: string
  operator_name: string
  operator_role: string
  action: string
  question_count: number
  created_at: string
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getAdminQuestionBank(params?: {
  type?: string
  keyword?: string
  tag?: string
  page?: number
  page_size?: number
}) {
  return http.get<any, PaginatedResult<Question>>('/admin/question-bank', { params })
}

export function createAdminQuestionBankItem(data: AdminQuestionBankPayload, mountCourseId?: number | null) {
  return http.post<any, Question>('/admin/question-bank', data, {
    params: mountCourseId ? { mount_course_id: mountCourseId } : undefined,
  })
}

export function updateAdminQuestionBankItem(id: number, data: Partial<AdminQuestionBankPayload>) {
  return http.put<any, Question>(`/admin/question-bank/${id}`, data)
}

export function deleteAdminQuestionBankItem(id: number) {
  return http.delete<any, any>(`/admin/question-bank/${id}`)
}

export function batchDeleteAdminQuestionBank(questionIds: number[]) {
  return http.post<any, { deleted_count: number; deleted_ids: number[]; missing_ids: number[] }>(
    '/admin/question-bank/batch-delete',
    { question_ids: questionIds },
  )
}

export function importAdminQuestionBank(file: File, mountCourseId?: number | null) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<any, {
    success_count: number
    fail_count: number
    skip_count: number
    errors: { row: number; reason: string }[]
    skips: { row: number; reason: string }[]
  }>('/admin/question-bank/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params: mountCourseId ? { mount_course_id: mountCourseId } : undefined,
  })
}

export async function downloadAdminQuestionBankTemplate(type: 'all' | 'choice' | 'fill' | 'multi_choice' = 'all') {
  const token = localStorage.getItem('auth_token')
  const response = await fetch(`/api/admin/question-bank/import/template?template_type=${type}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!response.ok) throw new Error('模板下载失败')
  return response.blob()
}

export function getAdminQuestionBankContributions(page = 1, pageSize = 20) {
  return http.get<any, PaginatedResult<AdminQuestionBankContribution>>('/admin/question-bank/contributions', {
    params: { page, page_size: pageSize },
  })
}

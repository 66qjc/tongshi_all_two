import http, { fetchWithAuth } from './http'
import type { Project } from './project'

export interface TeacherStats {
  total_students: number
  my_courses: number
  pending_reviews: number
  weekly_exercises: number
}

export interface StudentTaskScore {
  announcement_id: number
  title: string
  score: number | null
  is_completed: boolean
}

export interface Student {
  serial_no: number
  id: string
  name: string
  major: string
  class_id: number | null
  class_name: string
  completed_tasks: number
  incomplete_tasks: number
  task_completion_rate: number
  task_scores: StudentTaskScore[]
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getTeacherStats() {
  return http.get<any, TeacherStats>('/teacher/stats')
}

export function getStudents(classId?: number, page = 1, pageSize = 20, keyword?: string, courseId?: number) {
  const params: Record<string, any> = { page, page_size: pageSize }
  if (classId) params.class_id = classId
  if (keyword) params.keyword = keyword
  if (courseId) params.course_id = courseId
  return http.get<any, PaginatedResult<Student>>('/teacher/students', { params })
}

export function batchDeleteStudents(studentIds: string[]) {
  return http.post<any, { deleted_count: number; failed_ids: string[] }>('/teacher/students/batch-delete', studentIds)
}

export function getAllProjects(status?: string | null, keyword?: string, page = 1, pageSize = 20) {
  const params: Record<string, any> = { page, page_size: pageSize }
  if (status) params.status = status
  if (keyword) params.keyword = keyword
  return http.get<any, PaginatedResult<Project>>('/teacher/projects', { params })
}

export function approveProject(projectId: number) {
  return http.post<any, any>(`/teacher/projects/${projectId}/approve`)
}

export function rejectProject(projectId: number, reason: string) {
  return http.post<any, any>(`/teacher/projects/${projectId}/reject`, { reason })
}

export function deleteProject(projectId: number) {
  return http.delete<any, any>(`/teacher/projects/${projectId}`)
}

function resolveDownloadFilename(disposition: string | null) {
  if (!disposition) return 'project_reports.zip'
  const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i)
  const encoded = match?.[1] || match?.[2]
  if (!encoded) return 'project_reports.zip'
  try {
    return decodeURIComponent(encoded)
  } catch {
    return encoded
  }
}

export async function downloadProjectReportsZip() {
  const response = await fetchWithAuth('/api/teacher/projects/batch-download')

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    const payload = await response.json()
    if (payload?.code !== 0) {
      throw new Error(payload?.message || '批量下载失败')
    }
    throw new Error('批量下载失败')
  }

  if (!response.ok) {
    throw new Error('批量下载失败')
  }

  const blob = await response.blob()
  const filename = resolveDownloadFilename(response.headers.get('content-disposition'))
  return { blob, filename }
}

// ── 密码重置申请管理 ──────────────────────────────────────────────────

export interface PasswordResetRequest {
  id: number
  user_id: string
  user_name: string
  message: string
  status: string
  resolved_by: string | null
  resolved_by_name: string
  temp_password: string
  resolved_at: string
  created_at: string
}

export function getPasswordResetRequests(status?: string) {
  const params = status ? `?status=${encodeURIComponent(status)}` : ''
  return http.get<any, PasswordResetRequest[]>(`/teacher/password-reset-requests${params}`)
}

export function approvePasswordResetRequest(requestId: number) {
  return http.post<any, { message: string; temp_password: string }>(`/teacher/password-reset-requests/${requestId}/approve`)
}

export function rejectPasswordResetRequest(requestId: number, reason: string = '') {
  return http.post<any, { message: string }>(`/teacher/password-reset-requests/${requestId}/reject`, { reason })
}

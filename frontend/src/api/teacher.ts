import http from './http'
import type { Project } from './project'

export interface TeacherStats {
  total_students: number
  published_chapters: number
  pending_reviews: number
  weekly_exercises: number
}

export interface Student {
  id: string
  name: string
  major: string
  class_id: number | null
  class_name: string
  progress: number
  exercises: number
  accuracy: number
}

export function getTeacherStats() {
  return http.get<any, TeacherStats>('/teacher/stats')
}

export function getStudents(classId?: number) {
  return http.get<any, Student[]>('/teacher/students', {
    params: classId ? { class_id: classId } : undefined,
  })
}

export function getAllProjects(status?: string) {
  return http.get<any, Project[]>('/teacher/projects', { params: status ? { status } : {} })
}

export function approveProject(projectId: number) {
  return http.post<any, any>(`/teacher/projects/${projectId}/approve`)
}

export function rejectProject(projectId: number, reason: string) {
  return http.post<any, any>(`/teacher/projects/${projectId}/reject`, { reason })
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
  const token = localStorage.getItem('auth_token')
  if (!token) {
    throw new Error('请先登录后再下载')
  }

  const response = await fetch('/api/teacher/projects/batch-download', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

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

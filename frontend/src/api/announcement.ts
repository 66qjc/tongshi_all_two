import http from './http'

export interface Announcement {
  id: number
  course_id: number
  course_name: string
  class_ids: number[]
  class_names: string[]
  teacher_id: string
  teacher_name: string
  type: 'quiz'
  title: string
  content: string
  question_ids: number[]
  start_time: string | null
  end_time: string | null
  created_at: string
  is_read: boolean
}

export interface CompletionReport {
  announcement_id: number
  announcement_title: string
  course_id: number
  class_names: string[]
  total_students: number
  completed_count: number
  completed_students: { id: string; name: string; class_id: number; class_name: string }[]
  incomplete_students: { id: string; name: string; class_id: number; class_name: string }[]
  per_class: { class_id: number; class_name: string; total: number; completed: number }[]
  is_expired: boolean
}

export function getAnnouncements() {
  return http.get<any, Announcement[]>('/announcements')
}

export function getAnnouncement(id: number) {
  return http.get<any, Announcement>(`/announcements/${id}`)
}

export function createAnnouncement(data: {
  course_id: number
  class_ids: number[]
  title: string
  question_ids?: number[]
  start_time?: string
  end_time?: string
}) {
  return http.post<any, { id: number }>('/announcements', data)
}

export function deleteAnnouncement(id: number) {
  return http.delete<any, any>(`/announcements/${id}`)
}

export function getUnreadCount() {
  return http.get<any, { count: number }>('/announcements/unread-count')
}

export function markAsRead(id: number) {
  return http.post<any, any>(`/announcements/${id}/read`)
}

export function recordCompletion(id: number) {
  return http.post<any, any>(`/announcements/${id}/complete`)
}

export function getCompletionReport(id: number) {
  return http.get<any, CompletionReport>(`/announcements/${id}/completion-report`)
}

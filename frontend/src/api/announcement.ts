import http from './http'
import type { Question } from './question'

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
  is_completed: boolean
}

export interface StudentInfo {
  id: string
  name: string
  major: string
  class_id: number
  class_name: string
  score: number
  total_questions: number
}

export interface PaginatedStudents {
  items: StudentInfo[]
  total: number
  page: number
  page_size: number
}

export interface CompletionReport {
  announcement_id: number
  announcement_title: string
  course_id: number
  class_names: string[]
  total_students: number
  completed_count: number
  completed_students: PaginatedStudents
  incomplete_students: PaginatedStudents
  per_class: { class_id: number; class_name: string; total: number; completed: number }[]
  is_expired: boolean
  deadline: string | null
  created_at: string
  total_questions: number
}

export interface TaskOverview {
  total_tasks: number
  total_completed: number
  total_incomplete: number
  tasks: {
    id: number
    title: string
    class_names: string[]
    total_students: number
    completed_count: number
    is_expired: boolean
    created_at: string
  }[]
}

export interface AnnouncementQuestions {
  announcement: {
    id: number
    course_id: number
    title: string
    question_ids: number[]
  }
  questions: Question[]
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

export function getAnnouncementQuestions(id: number) {
  return http.get<any, AnnouncementQuestions>(`/announcements/${id}/questions`)
}

export function getCompletionReport(id: number, params?: {
  class_id?: number
  completed_page?: number
  completed_page_size?: number
  incomplete_page?: number
  incomplete_page_size?: number
}) {
  return http.get<any, CompletionReport>(`/announcements/${id}/completion-report`, { params })
}

export function getTaskOverview() {
  return http.get<any, TaskOverview>('/announcements/task-overview')
}

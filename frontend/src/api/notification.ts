import http from './http'

export interface StudentNotification {
  id: number
  type: string
  category: string
  priority: 'low' | 'normal' | 'high' | string
  title: string
  content: string
  project_id: number | null
  action_url: string
  extra_data: Record<string, unknown>
  expires_at?: string | null
  sent_at?: string | null
  is_read: boolean
  created_at: string
}

export interface NotificationPreferences {
  user_id: string
  enable_assignment_due: boolean
  enable_grade_published: boolean
  enable_course_update: boolean
  enable_project_review: boolean
  updated_at?: string | null
}

export type NotificationPreferencePayload = Partial<Pick<
  NotificationPreferences,
  'enable_assignment_due' | 'enable_grade_published' | 'enable_course_update' | 'enable_project_review'
>>

export interface NotificationQueryParams {
  category?: string
  unread_only?: boolean
}

export function getNotifications(params?: NotificationQueryParams) {
  return http.get<any, StudentNotification[]>('/notifications', { params })
}

export function getNotificationUnreadCount() {
  return http.get<any, { count: number }>('/notifications/unread-count')
}

export function markNotificationRead(id: number) {
  return http.post<any, any>(`/notifications/${id}/read`)
}

export function markAllNotificationsRead() {
  return http.post<any, { updated_count: number }>('/notifications/read-all')
}

export function getNotificationPreferences() {
  return http.get<any, NotificationPreferences>('/notifications/preferences')
}

export function updateNotificationPreferences(data: NotificationPreferencePayload) {
  return http.put<any, NotificationPreferences>('/notifications/preferences', data)
}

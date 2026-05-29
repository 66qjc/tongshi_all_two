import http from './http'

export interface UserNotification {
  id: number
  user_id: string
  type: 'project_rejected' | string
  title: string
  content: string
  related_type: string
  related_id: number | null
  is_read: boolean
  created_at: string
}

export function getNotifications() {
  return http.get<any, UserNotification[]>('/notifications')
}

export function getNotificationUnreadCount() {
  return http.get<any, { count: number }>('/notifications/unread-count')
}

export function markNotificationAsRead(id: number) {
  return http.post<any, any>(`/notifications/${id}/read`)
}

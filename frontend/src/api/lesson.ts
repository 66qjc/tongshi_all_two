import http from './http'

export interface Lesson {
  id: number
  course_id: number
  title: string
  content: string
  status: 'draft' | 'published'
  sort_order: number
  created_at: string
  updated_at: string
}

export interface LessonCreatePayload {
  title: string
  content?: string
  status?: 'draft' | 'published'
  sort_order?: number
}

export interface LessonUpdatePayload {
  title?: string
  content?: string
  status?: 'draft' | 'published'
  sort_order?: number
}

export function getLessons(courseId: number) {
  return http.get<any, Lesson[]>(`/courses/${courseId}/lessons`)
}

export function createLesson(courseId: number, data: LessonCreatePayload) {
  return http.post<any, Lesson>(`/courses/${courseId}/lessons`, data)
}

export function getLesson(lessonId: number) {
  return http.get<any, Lesson>(`/lessons/${lessonId}`)
}

export function updateLesson(lessonId: number, data: LessonUpdatePayload) {
  return http.put<any, Lesson>(`/lessons/${lessonId}`, data)
}

export function deleteLesson(lessonId: number) {
  return http.delete<any, { id: number }>(`/lessons/${lessonId}`)
}

export function reorderLessons(
  courseId: number,
  items: { id: number; sort_order: number }[],
) {
  return http.post<any, Lesson[]>(`/courses/${courseId}/lessons/reorder`, items)
}

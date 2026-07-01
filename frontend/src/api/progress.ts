import http from './http'

export interface CourseProgress {
  last_lesson_id: number | null
}

export function getCourseProgress(courseId: number) {
  return http.get<any, CourseProgress>(`/courses/${courseId}/progress`)
}

export function saveCourseProgress(courseId: number, lessonId: number) {
  return http.post<any, CourseProgress>(`/courses/${courseId}/progress`, { lesson_id: lessonId })
}

import http from './http'

export interface Course {
  id: number
  name: string
  created_at: string
  material_count: number
  question_count: number
  class_count: number
}

export type CourseDetail = Course

export function getCourses() {
  return http.get<any, Course[]>('/questions/courses')
}

export function getCourseDetail(id: number) {
  return http.get<any, CourseDetail>(`/questions/courses/${id}`)
}

export function createCourse(data: { name: string }) {
  return http.post<any, { id: number }>('/questions/courses', data)
}

export function updateCourse(id: number, data: { name: string }) {
  return http.put<any, any>(`/questions/courses/${id}`, data)
}

export function deleteCourse(id: number) {
  return http.delete<any, any>(`/questions/courses/${id}`)
}

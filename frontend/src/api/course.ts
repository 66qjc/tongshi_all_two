import http from './http'
import type { Chapter } from './chapter'

export interface Course {
  id: number
  name: string
  created_at: string
  chapter_count: number
  material_count: number
}

export interface CourseDetail extends Course {
  chapters: Chapter[]
}

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

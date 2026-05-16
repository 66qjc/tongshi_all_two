import http from './http'

export interface Course {
  id: number
  name: string
}

export function getCourses() {
  return http.get<any, Course[]>('/courses')
}

export function createCourse(name: string) {
  return http.post<any, Course>('/courses', { name })
}

export function updateCourse(id: number, name: string) {
  return http.put<any, any>(`/courses/${id}`, { name })
}

export function deleteCourse(id: number) {
  return http.delete<any, any>(`/courses/${id}`)
}

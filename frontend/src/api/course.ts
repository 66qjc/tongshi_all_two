import http from './http'
import type { Material } from './material'
import type { PaginatedResult } from './question'

export interface Course {
  id: number
  name: string
  description: string
  created_at: string
  created_by?: string
  is_public?: boolean
  is_owner?: boolean
  material_count: number
  question_count: number
  class_count: number
}

export interface CourseStage {
  id: number
  course_id: number
  source_stage_id?: number | null
  name: string
  sort_order: number
  created_at?: string
  materials: Material[]
}

export type CourseDetail = Course & {
  stages: CourseStage[]
  uncategorized_materials: Material[]
}
export interface CourseListResult {
  courses: Course[]
  hint: string | null
}

export function getCourseList(keyword?: string) {
  return http.get<any, Course[] | CourseListResult>('/courses', {
    params: keyword ? { keyword } : undefined,
  }).then(data => {
    if (Array.isArray(data)) return { courses: data, hint: null }
    return data
  })
}

export function getCourses(keyword?: string) {
  return getCourseList(keyword).then(data => data.courses)
}

export function getCoursesPage(params: {
  keyword?: string
  page?: number
  page_size?: number
  scope?: 'owned' | 'public' | 'all'
}) {
  return http.get<any, PaginatedResult<Course>>('/courses', { params })
}

export function getCourseDetail(id: number) {
  return http.get<any, CourseDetail>(`/courses/${id}`)
}

export function createCourse(data: { name: string; description?: string }) {
  return http.post<any, { id: number }>('/courses', data)
}

export function getCourseStages(courseId: number) {
  return http.get<any, CourseStage[]>(`/courses/${courseId}/stages`)
}

export function createCourseStage(courseId: number, data: { name: string; sort_order: number }) {
  return http.post<any, CourseStage>(`/courses/${courseId}/stages`, data)
}

export function updateCourseStage(stageId: number, data: { name?: string; sort_order?: number }) {
  return http.put<any, CourseStage>(`/stages/${stageId}`, data)
}

export function deleteCourseStage(stageId: number) {
  return http.delete<any, any>(`/stages/${stageId}`)
}

export function addPublicCourse(id: number) {
  return http.post<any, { id: number }>(`/questions/courses/${id}/add`)
}

export function updateCourse(id: number, data: { name?: string; description?: string }) {
  return http.put<any, any>(`/courses/${id}`, data)
}

export function deleteCourse(id: number) {
  return http.delete<any, any>(`/courses/${id}`)
}

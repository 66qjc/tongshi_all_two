import http from './http'
import type { Project } from './project'

export interface TeacherStats {
  total_students: number
  published_chapters: number
  pending_reviews: number
  weekly_exercises: number
}

export interface Student {
  id: string
  name: string
  major: string
  progress: number
  exercises: number
  accuracy: number
}

export function getTeacherStats() {
  return http.get<any, TeacherStats>('/teacher/stats')
}

export function getStudents() {
  return http.get<any, Student[]>('/teacher/students')
}

export function getAllProjects(status?: string) {
  return http.get<any, Project[]>('/teacher/projects', { params: status ? { status } : {} })
}

export function approveProject(projectId: number) {
  return http.post<any, any>(`/teacher/projects/${projectId}/approve`)
}

export function rejectProject(projectId: number, reason: string) {
  return http.post<any, any>(`/teacher/projects/${projectId}/reject`, { reason })
}

import http from './http'

export interface ClassInfo {
  id: number
  name: string
  course_id: number
  course_name: string
  student_count: number
  created_at: string
}

export interface ClassStudent {
  id: string
  name: string
  major: string
  enrolled_at?: string
}

export function getClasses(params?: { course_id?: number; keyword?: string }) {
  return http.get<any, ClassInfo[]>('/classes', { params })
}

export function createClass(data: { name: string; course_id: number }) {
  return http.post<any, ClassInfo>('/classes', data)
}

export function deleteClass(id: number) {
  return http.delete<any, any>(`/classes/${id}`)
}

export function getClassStudents(classId: number) {
  return http.get<any, ClassStudent[]>(`/classes/${classId}/students`)
}

export function enrollStudent(classId: number, studentId: string, name: string = '') {
  return http.post<any, any>(`/classes/${classId}/enroll`, { student_id: studentId, name })
}

export function unenrollStudent(classId: number, studentId: string) {
  return http.delete<any, any>(`/classes/${classId}/enroll/${studentId}`)
}

export function importStudents(file: File, classId?: number) {
  const formData = new FormData()
  formData.append('file', file)
  if (classId !== undefined) {
    formData.append('class_id', String(classId))
  }
  return http.post<any, { success_count: number; skip_count: number; fail_count: number; errors: string[] }>('/classes/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

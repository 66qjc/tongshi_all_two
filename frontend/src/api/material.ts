import http from './http'

export interface Material {
  id: number
  course_id: number
  course_name: string
  type: 'video' | 'pdf'
  title: string
  url: string
  duration: string
  pages: number
  size: string
  date: string
  file_id?: number
}

export interface MaterialCreatePayload {
  course_id: number
  type: 'video' | 'pdf'
  title: string
  url: string
  size: string
  file_id?: number
}

export function getAllMaterials(params?: { course_id?: number }) {
  return http.get<any, Material[]>('/materials', { params })
}

export function getCourseContents(courseId: number) {
  return http.get<any, Material[]>(`/courses/${courseId}/contents`)
}

export function createMaterial(data: MaterialCreatePayload) {
  return http.post<any, { id: number }>('/materials', data)
}

export function deleteMaterial(id: number) {
  return http.delete<any, any>(`/materials/${id}`)
}

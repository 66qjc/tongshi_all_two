import http from './http'
import type { PaginatedResult } from './question'

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
  source_material_id?: number | null
  is_synced?: boolean
  stage_id?: number | null
}

export interface MaterialCreatePayload {
  course_id: number
  type: 'video' | 'pdf'
  title: string
  url: string
  size: string
  file_id?: number
  stage_id?: number | null
}

export function getAllMaterials(params?: {
  course_id?: number
  keyword?: string
  page?: number
  page_size?: number
}) {
  return http.get<any, PaginatedResult<Material>>('/materials', { params })
}

export function getCourseContents(courseId: number, keyword?: string) {
  return http.get<any, Material[]>(`/courses/${courseId}/contents`, {
    params: keyword ? { keyword } : undefined,
  })
}

export function createMaterial(data: MaterialCreatePayload) {
  return http.post<any, { id: number }>('/materials', data)
}

export function updateMaterial(id: number, data: { title?: string; stage_id?: number | null }) {
  return http.put<any, any>(`/materials/${id}`, data)
}

export function deleteMaterial(id: number) {
  return http.delete<any, any>(`/materials/${id}`)
}

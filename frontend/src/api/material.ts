import http from './http'

export interface Material {
  id: number
  chapter_id: number
  chapter: string
  type: 'video' | 'pdf'
  title: string
  url: string
  duration: string
  pages: number
  size: string
  date: string
}

export interface MaterialCreatePayload {
  chapter_id: number
  type: 'video' | 'pdf'
  title: string
  url: string
  size: string
}

export function getAllMaterials() {
  return http.get<any, Material[]>('/materials')
}

export function createMaterial(data: MaterialCreatePayload) {
  return http.post<any, { id: number }>('/materials', data)
}

export function deleteMaterial(id: number) {
  return http.delete<any, any>(`/materials/${id}`)
}

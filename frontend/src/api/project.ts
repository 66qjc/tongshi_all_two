import http from './http'

export interface ProjectImage {
  id?: number
  image_url: string
  sort_order?: number
  file_id?: number
}

export interface Project {
  id: number
  title: string
  author_id: string
  author_name: string
  course_id?: number | null
  course_name?: string
  major: string
  description: string
  tags: string[]
  likes: number
  is_liked: boolean
  featured: boolean
  video_url: string
  report_url: string
  image_url: string
  images?: ProjectImage[]
  link_url: string
  status: string
  reject_reason: string
  date: string
  report_file_id?: number
  cover_file_id?: number
}

export interface ProjectPayload {
  course_id: number
  title: string
  description: string
  tags: string[]
  video_url?: string
  report_url?: string
  image_url?: string
  image_urls?: string[]
  link_url?: string
  report_file_id?: number
  cover_file_id?: number
  image_file_ids?: number[]
}

export interface PaginatedProjects {
  items: Project[]
  total: number
  page: number
  page_size: number
}

export function getProjects(page = 1, pageSize = 12) {
  return http.get<any, PaginatedProjects>('/projects', { params: { page, page_size: pageSize } })
}

export function getProject(id: number) {
  return http.get<any, Project>(`/projects/${id}`)
}

export function getMyProjects(page = 1, pageSize = 12) {
  return http.get<any, PaginatedProjects>('/projects/mine', { params: { page, page_size: pageSize } })
}

export function createProject(data: ProjectPayload) {
  return http.post<any, { id: number }>('/projects', data)
}

export function updateProject(id: number, data: ProjectPayload) {
  return http.put<any, { id: number }>(`/projects/${id}`, data)
}

export function toggleLike(projectId: number) {
  return http.post<any, { liked: boolean; likes: number }>(`/projects/${projectId}/like`)
}

export function deleteMyProject(projectId: number) {
  return http.delete<any, { id?: number }>(`/projects/${projectId}`)
}

export function guestLikeProject(projectId: number) {
  return http.post<any, { liked: boolean; likes: number }>(`/projects/${projectId}/guest-like`)
}

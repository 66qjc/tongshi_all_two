import http from './http'

export interface Project {
  id: number
  title: string
  author_id: string
  author_name: string
  major: string
  description: string
  tags: string[]
  likes: number
  featured: boolean
  video_url: string
  report_url: string
  image_url: string
  link_url: string
  status: string
  reject_reason: string
  date: string
}

export function getProjects() {
  return http.get<any, Project[]>('/projects')
}

export function getProject(id: number) {
  return http.get<any, Project>(`/projects/${id}`)
}

export function getMyProjects() {
  return http.get<any, Project[]>('/projects/mine')
}

export function createProject(data: { title: string; description: string; tags: string[]; video_url?: string; report_url?: string; image_url?: string; link_url?: string }) {
  return http.post<any, { id: number }>('/projects', data)
}

export function toggleLike(projectId: number) {
  return http.post<any, { liked: boolean; likes: number }>(`/projects/${projectId}/like`)
}

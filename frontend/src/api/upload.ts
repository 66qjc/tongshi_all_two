import http from './http'

export interface UploadResult {
  file_id: number
  url: string
  filename: string
  size: number
  content_type: string
  storage_provider: string
}

export function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<any, UploadResult>('/upload', formData)
}

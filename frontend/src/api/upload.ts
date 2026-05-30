import http from './http'

export interface UploadResult {
  file_id: number
  url: string
  filename: string
  size: number
  content_type: string
  storage_provider: string
}

export function uploadFile(file: File, bizType: string = 'upload') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('biz_type', bizType)
  return http.post<any, UploadResult>('/upload', formData)
}

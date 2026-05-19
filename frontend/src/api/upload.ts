import http from './http'

export function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<any, { url: string; filename: string; size: number }>('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

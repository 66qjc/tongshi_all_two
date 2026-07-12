import http from './http'

export interface FileAccessUrl {
  url: string
  expires_in: number
}

export function getFileAccessUrl(fileId: number, signal?: AbortSignal) {
  return http.post<any, FileAccessUrl>(`/files/${fileId}/access-url`, undefined, {
    signal,
    silentError: true,
  })
}

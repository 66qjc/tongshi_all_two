import http from './http'
import type { AxiosProgressEvent } from 'axios'

export interface UploadResult {
  file_id: number
  url: string
  filename: string
  size: number
  content_type: string
  storage_provider: string
}

export const MAX_VIDEO_UPLOAD_SIZE = 1024 * 1024 * 1024
const VIDEO_UPLOAD_TIMEOUT = 60 * 60 * 1000
const VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']

function isVideoUpload(file: File) {
  const filename = file.name.toLowerCase()
  return file.type.startsWith('video/') || VIDEO_EXTENSIONS.some((extension) => filename.endsWith(extension))
}

export function validateCourseMaterialUpload(file: File) {
  if (isVideoUpload(file) && file.size > MAX_VIDEO_UPLOAD_SIZE) {
    return '视频文件不能超过 1GiB'
  }
  return ''
}

export function uploadFile(
  file: File,
  bizType: string = 'upload',
  onProgress?: (percent: number) => void,
  videoUpload: boolean = false,
) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('biz_type', bizType)
  const isVideo = videoUpload && isVideoUpload(file)
  if (isVideo) {
    formData.append('expected_size', String(file.size))
  }
  return http.post<any, UploadResult>('/upload', formData, {
    timeout: isVideo ? VIDEO_UPLOAD_TIMEOUT : undefined,
    onUploadProgress: onProgress
      ? (e: AxiosProgressEvent) => {
          if (e.total) {
            onProgress(Math.round((e.loaded / e.total) * 100))
          }
        }
      : undefined,
  })
}

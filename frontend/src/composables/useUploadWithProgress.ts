/** 上传进度封装，包装 uploadFile 支持 onProgress 回调。 */
import { ref } from 'vue'
import { uploadFile, type UploadResult } from '@/api/upload'

export function useUploadWithProgress() {
  const uploading = ref(false)
  const percent = ref(0)

  async function upload(file: File, bizType: string = 'upload'): Promise<UploadResult> {
    uploading.value = true
    percent.value = 0
    try {
      const result = await uploadFile(
        file,
        bizType,
        (p) => {
          percent.value = p
        },
        true,
      )
      percent.value = 100
      return result
    } finally {
      uploading.value = false
    }
  }

  return { uploading, percent, upload }
}

import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { getFileAccessUrl } from '@/api/file'
import { resolveFileUrl } from '@/utils/url'

interface UseAuthenticatedFileUrlOptions {
  enabled?: Ref<boolean>
}

interface SignedUrlRequestOptions {
  preserveCurrentUrl?: boolean
  silentFailure?: boolean
}

const PRIVATE_FILE_PATH = /^\/api\/files\/([1-9]\d*)\/?$/
const PUBLIC_MATERIAL_PATH = /^\/api\/public\/learning\/materials\/[1-9]\d*\/file\/?$/
const MAX_BACKGROUND_RENEWAL_RETRIES = 1
const BACKGROUND_RENEWAL_RETRY_DELAY_MS = 5000

function isRelativeFileSource(source: string) {
  return !/^[a-z][a-z\d+.-]*:/i.test(source) && !source.startsWith('//')
}

function getAllowedFileOrigins() {
  const allowedOrigins = new Set<string>()
  const browserOrigin = typeof window !== 'undefined' ? window.location.origin : ''
  if (browserOrigin) allowedOrigins.add(browserOrigin)

  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined)?.trim()
  if (apiBase) {
    try {
      const apiUrl = /^[a-z][a-z\d+.-]*:/i.test(apiBase)
        ? new URL(apiBase)
        : browserOrigin
          ? new URL(apiBase, browserOrigin)
          : null
      if (apiUrl) allowedOrigins.add(apiUrl.origin)
    } catch {
      // 配置无法解析时不扩大私有文件 origin 白名单。
    }
  }
  return allowedOrigins
}

function getPrivateFileId(source: string): number | null {
  try {
    const isRelativeSource = isRelativeFileSource(source)
    const browserOrigin = typeof window !== 'undefined' ? window.location.origin : ''
    const parsed = new URL(source, browserOrigin || 'http://relative.invalid')
    const allowedOrigins = getAllowedFileOrigins()
    if (!isRelativeSource && !allowedOrigins.has(parsed.origin)) return null
    if (PUBLIC_MATERIAL_PATH.test(parsed.pathname)) return null
    const match = parsed.pathname.match(PRIVATE_FILE_PATH)
    return match ? Number(match[1]) : null
  } catch {
    return null
  }
}

function isCanceledRequest(error: unknown) {
  if (!error || typeof error !== 'object') return false
  const requestError = error as { code?: string; name?: string }
  return requestError.code === 'ERR_CANCELED' || requestError.name === 'CanceledError'
}

export function useAuthenticatedFileUrl(
  sourceUrl: Ref<string>,
  options: UseAuthenticatedFileUrlOptions = {},
) {
  const resolvedUrl = ref('')
  const loading = ref(false)
  const error = ref('')
  let activeController: AbortController | null = null
  let renewalTimer: ReturnType<typeof setTimeout> | null = null
  let requestVersion = 0
  let retrySource = ''
  let retryCount = 0
  let retryInFlight: Promise<void> | null = null
  let retryInFlightSource = ''
  let renewalRetryCount = 0

  function clearRenewalTimer() {
    if (renewalTimer !== null) {
      clearTimeout(renewalTimer)
      renewalTimer = null
    }
  }

  function abortActiveRequest() {
    if (activeController) {
      activeController.abort()
      activeController = null
    }
  }

  function stopActiveWork() {
    requestVersion += 1
    abortActiveRequest()
    clearRenewalTimer()
    retryInFlight = null
    retryInFlightSource = ''
    renewalRetryCount = 0
  }

  function isCurrentRequest(version: number, source: string) {
    return (
      version === requestVersion &&
      source === sourceUrl.value &&
      (options.enabled?.value ?? true)
    )
  }

  function scheduleRenewal(source: string, fileId: number, expiresIn: number) {
    clearRenewalTimer()
    renewalRetryCount = 0
    const delayMs = Math.max(expiresIn - 30, 1) * 1000
    renewalTimer = setTimeout(() => {
      if (source === sourceUrl.value && (options.enabled?.value ?? true)) {
        void requestSignedUrl(source, fileId, {
          preserveCurrentUrl: true,
          silentFailure: true,
        })
      }
    }, delayMs)
  }

  function scheduleRenewalRetry(source: string, fileId: number) {
    clearRenewalTimer()
    if (renewalRetryCount >= MAX_BACKGROUND_RENEWAL_RETRIES) return
    renewalRetryCount += 1
    renewalTimer = setTimeout(() => {
      if (source === sourceUrl.value && (options.enabled?.value ?? true)) {
        void requestSignedUrl(source, fileId, {
          preserveCurrentUrl: true,
          silentFailure: true,
        })
      }
    }, BACKGROUND_RENEWAL_RETRY_DELAY_MS)
  }

  async function requestSignedUrl(
    source: string,
    fileId: number,
    requestOptions: SignedUrlRequestOptions,
  ) {
    const {
      preserveCurrentUrl = false,
      silentFailure = false,
    } = requestOptions
    abortActiveRequest()
    clearRenewalTimer()

    const controller = new AbortController()
    const version = ++requestVersion
    activeController = controller
    error.value = ''
    if (!preserveCurrentUrl || !resolvedUrl.value) loading.value = true

    try {
      const result = await getFileAccessUrl(fileId, controller.signal)
      if (!isCurrentRequest(version, source)) return
      error.value = ''
      resolvedUrl.value = resolveFileUrl(result.url)
      scheduleRenewal(source, fileId, result.expires_in)
    } catch (requestError) {
      if (!isCurrentRequest(version, source) || isCanceledRequest(requestError)) return
      if (silentFailure && resolvedUrl.value) {
        scheduleRenewalRetry(source, fileId)
        return
      }
      error.value = preserveCurrentUrl
        ? '文件访问地址续签失败，请稍后重试。'
        : '文件访问地址获取失败，请稍后重试。'
    } finally {
      if (version === requestVersion) {
        activeController = null
        loading.value = false
      }
    }
  }

  async function loadFile(preserveCurrentUrl = false) {
    const source = sourceUrl.value
    const enabled = options.enabled?.value ?? true
    const fileId = getPrivateFileId(source)

    if (!source || !enabled) {
      stopActiveWork()
      resolvedUrl.value = ''
      loading.value = false
      error.value = ''
      return
    }

    if (fileId === null) {
      stopActiveWork()
      resolvedUrl.value = resolveFileUrl(source)
      loading.value = false
      error.value = ''
      return
    }

    if (!preserveCurrentUrl) resolvedUrl.value = ''
    await requestSignedUrl(source, fileId, { preserveCurrentUrl })
  }

  async function retryOnce(failedUrl: string) {
    const source = sourceUrl.value
    const enabled = options.enabled?.value ?? true
    const fileId = getPrivateFileId(source)

    if (!failedUrl || failedUrl !== resolvedUrl.value) return

    if (!source || !enabled || fileId === null) {
      error.value = '当前文件无法自动刷新，请重新打开后再试。'
      return
    }

    if (source !== retrySource) {
      retrySource = source
      retryCount = 0
    }
    if (retryInFlight && retryInFlightSource === source) return retryInFlight
    if (retryCount >= 1) {
      error.value = '文件再次加载失败，请稍后重试。'
      return
    }

    retryCount += 1
    const request = requestSignedUrl(source, fileId, {
      preserveCurrentUrl: Boolean(resolvedUrl.value),
    })
    retryInFlight = request
    retryInFlightSource = source
    try {
      await request
    } finally {
      if (retryInFlight === request) {
        retryInFlight = null
        retryInFlightSource = ''
      }
    }
  }

  watch(
    () => [sourceUrl.value, options.enabled?.value ?? true] as const,
    ([source]) => {
      if (source !== retrySource) {
        retrySource = source
        retryCount = 0
      }
      stopActiveWork()
      void loadFile()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    stopActiveWork()
    resolvedUrl.value = ''
  })

  return { resolvedUrl, loading, error, reload: loadFile, retryOnce }
}

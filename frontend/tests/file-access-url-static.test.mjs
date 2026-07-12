import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  const path = resolve(root, relativePath)
  return existsSync(path) ? readFileSync(path, 'utf8') : ''
}

function readFunctionBody(source, functionName) {
  const signature = new RegExp(`(?:async\\s+)?function\\s+${functionName}\\s*\\(`)
  const match = signature.exec(source)
  if (!match) return ''

  const openingBrace = source.indexOf('{', match.index)
  if (openingBrace < 0) return ''

  let depth = 0
  for (let index = openingBrace; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') {
      depth -= 1
      if (depth === 0) return source.slice(openingBrace + 1, index)
    }
  }
  return ''
}

const fileApi = read('src/api/file.ts')
const fileUrlComposable = read('src/composables/useAuthenticatedFileUrl.ts')
const urlUtil = read('src/utils/url.ts')
const http = read('src/api/http.ts')

const failures = []

function check(name, assertion) {
  try {
    assertion()
  } catch (error) {
    failures.push(`${name}: ${error instanceof Error ? error.message : String(error)}`)
  }
}

check('文件 URL API 使用 POST、AbortSignal 与静默错误配置', () => {
  assert.match(fileApi, /export interface FileAccessUrl/)
  assert.match(fileApi, /getFileAccessUrl\s*\(\s*fileId:\s*number,\s*signal\?:\s*AbortSignal/)
  assert.match(fileApi, /http\.post<[^>]+>\(\s*`\/files\/\$\{fileId\}\/access-url`/)
  assert.match(fileApi, /\{\s*signal,\s*silentError:\s*true,?\s*\}/)
  assert.match(fileApi, /expires_in:\s*number/)
})

check('取消签名请求不会 Toast 或清理登录态', () => {
  assert.match(http, /axios\.isCancel\(error\)|error\?\.code\s*===\s*['"]ERR_CANCELED['"]|error\.code\s*===\s*['"]ERR_CANCELED['"]/)
  const cancelIndex = http.search(/axios\.isCancel\(error\)|ERR_CANCELED/)
  const unauthorizedIndex = http.indexOf("error.response?.status === 401")
  assert.ok(cancelIndex >= 0 && unauthorizedIndex >= 0 && cancelIndex < unauthorizedIndex)
})

check('组合式函数可取消旧请求并清理续签计时器', () => {
  assert.match(fileUrlComposable, /new AbortController\(\)/)
  assert.match(fileUrlComposable, /\.abort\(\)/)
  assert.match(fileUrlComposable, /clearTimeout\(/)
  assert.match(fileUrlComposable, /onBeforeUnmount/)
  assert.match(fileUrlComposable, /getFileAccessUrl\([^,]+,\s*[^)]+\.signal\)/)

  const currentRequestBody = readFunctionBody(fileUrlComposable, 'isCurrentRequest')
  assert.match(currentRequestBody, /version\s*===\s*requestVersion/)
  assert.match(currentRequestBody, /source\s*===\s*sourceUrl\.value/)
  assert.match(currentRequestBody, /options\.enabled\?\.value\s*\?\?\s*true/)

  const stopActiveWorkBody = readFunctionBody(fileUrlComposable, 'stopActiveWork')
  assert.match(stopActiveWorkBody, /requestVersion\s*\+=\s*1/)
  assert.match(stopActiveWorkBody, /abortActiveRequest\(\)/)
  assert.match(stopActiveWorkBody, /clearRenewalTimer\(\)/)

  const watchIndex = fileUrlComposable.indexOf('\n  watch(')
  const unmountIndex = fileUrlComposable.indexOf('\n  onBeforeUnmount(', watchIndex)
  const watchBlock = fileUrlComposable.slice(watchIndex, unmountIndex)
  assert.match(watchBlock, /sourceUrl\.value/)
  assert.match(watchBlock, /options\.enabled\?\.value\s*\?\?\s*true/)
  assert.match(watchBlock, /stopActiveWork\(\)/)
  assert.match(fileUrlComposable.slice(unmountIndex), /onBeforeUnmount\(\(\) => \{[\s\S]*?stopActiveWork\(\)/)
})

check('组合式函数按过期时间提前 30 秒续签', () => {
  assert.match(fileUrlComposable, /result\.expires_in/)
  assert.match(fileUrlComposable, /Math\.max\([^\n;]*expiresIn\s*-\s*30[^\n;]*,\s*1\)/)
  assert.match(fileUrlComposable, /setTimeout\(/)
  assert.match(fileUrlComposable, /resolveFileUrl\(result\.url\)/)
})

check('后台续签失败保留仍有效的当前地址', () => {
  assert.match(fileUrlComposable, /const MAX_BACKGROUND_RENEWAL_RETRIES\s*=\s*1/)
  const scheduleBody = readFunctionBody(fileUrlComposable, 'scheduleRenewal')
  assert.match(
    scheduleBody,
    /requestSignedUrl\(\s*source,\s*fileId,\s*\{[\s\S]*?preserveCurrentUrl:\s*true[\s\S]*?silentFailure:\s*true[\s\S]*?\}\s*\)/,
    '定时续签必须显式使用静默失败模式，不能因一次瞬时失败中断仍有效的预览。',
  )

  const retryScheduleBody = readFunctionBody(fileUrlComposable, 'scheduleRenewalRetry')
  const retryLimitIndex = retryScheduleBody.indexOf('renewalRetryCount >= MAX_BACKGROUND_RENEWAL_RETRIES')
  const retryIncrementIndex = retryScheduleBody.indexOf('renewalRetryCount += 1')
  const retryTimerIndex = retryScheduleBody.indexOf('setTimeout(')
  assert.ok(
    retryLimitIndex >= 0 && retryIncrementIndex > retryLimitIndex && retryTimerIndex > retryIncrementIndex,
    '后台续签失败只能安排一次有上限的短退避重试。',
  )
  assert.match(
    retryScheduleBody,
    /requestSignedUrl\(\s*source,\s*fileId,\s*\{[\s\S]*?preserveCurrentUrl:\s*true[\s\S]*?silentFailure:\s*true[\s\S]*?\}\s*\)/,
  )

  const requestBody = readFunctionBody(fileUrlComposable, 'requestSignedUrl')
  assert.match(
    requestBody,
    /if\s*\(silentFailure\s*&&\s*resolvedUrl\.value\)\s*\{[\s\S]*?scheduleRenewalRetry\(source,\s*fileId\)[\s\S]*?return[\s\S]*?\}[\s\S]*?error\.value\s*=\s*preserveCurrentUrl/,
    '静默续签失败应保留当前地址并安排一次短退避，不能进入可见错误态。',
  )
})

check('重复媒体错误共享同一在途重试并忽略旧地址事件', () => {
  assert.match(fileUrlComposable, /let retryInFlight:\s*Promise<void>\s*\|\s*null\s*=\s*null/)
  assert.match(fileUrlComposable, /let retryInFlightSource\s*=\s*['"]/)

  const retryBody = readFunctionBody(fileUrlComposable, 'retryOnce')
  assert.match(
    retryBody,
    /!failedUrl\s*\|\|\s*failedUrl\s*!==\s*resolvedUrl\.value[\s\S]*?return/,
    '空地址和旧加载代次的错误事件必须在申请新签名前被忽略。',
  )
  const failedUrlGuardIndex = retryBody.indexOf('!failedUrl || failedUrl !== resolvedUrl.value')
  const unsupportedSourceIndex = retryBody.indexOf('!source || !enabled || fileId === null')
  assert.ok(
    failedUrlGuardIndex >= 0 && unsupportedSourceIndex > failedUrlGuardIndex,
    '旧加载代次必须在公开/外链无法续签分支之前被忽略，避免污染新来源。',
  )
  const inFlightGuardIndex = retryBody.indexOf('retryInFlight && retryInFlightSource === source')
  const retryLimitIndex = retryBody.indexOf('retryCount >= 1')
  assert.ok(
    inFlightGuardIndex >= 0 && retryLimitIndex > inFlightGuardIndex,
    '同一来源的重复错误必须先复用在途重试，不能被误判为第二次失败。',
  )
  assert.match(retryBody, /finally\s*\{[\s\S]*?retryInFlight\s*=\s*null/)

  const requestBody = readFunctionBody(fileUrlComposable, 'requestSignedUrl')
  const currentRequestIndex = requestBody.indexOf('if (!isCurrentRequest(version, source)) return')
  const successClearIndex = requestBody.indexOf("error.value = ''", currentRequestIndex)
  const resolvedUrlIndex = requestBody.indexOf('resolvedUrl.value = resolveFileUrl(result.url)', currentRequestIndex)
  assert.ok(
    currentRequestIndex >= 0 &&
      successClearIndex > currentRequestIndex &&
      resolvedUrlIndex > successClearIndex,
    '当前重试成功提交新地址前必须清除并发错误状态。',
  )
})

check('源变化重置一次重试限制，第二次失败只显示中文错误', () => {
  const retryBody = readFunctionBody(fileUrlComposable, 'retryOnce')
  const resetBlockMatch = retryBody.match(
    /if\s*\(source\s*!==\s*retrySource\)\s*\{([\s\S]*?)\}/,
  )
  assert.ok(resetBlockMatch, '重试计数只能在源变化时进入重置分支。')
  const resetBlock = resetBlockMatch[1]
  const retrySourceAssignment = resetBlock.indexOf('retrySource = source')
  const retryCountReset = resetBlock.indexOf('retryCount = 0')
  assert.ok(
    retrySourceAssignment >= 0 && retryCountReset > retrySourceAssignment,
    '源变化时必须先记录新源，再重置该源的重试次数。',
  )
  assert.match(retryBody, /if\s*\(retryCount\s*>=\s*1\)\s*\{[\s\S]*?[\u4e00-\u9fff]{4,}[\s\S]*?return[\s\S]*?\}/)

  const guardIndex = retryBody.indexOf('retryCount >= 1')
  const returnIndex = retryBody.indexOf('return', guardIndex)
  const incrementIndex = retryBody.indexOf('retryCount += 1')
  const requestIndex = retryBody.indexOf('requestSignedUrl(', incrementIndex)
  assert.ok(
    guardIndex >= 0 &&
      returnIndex > guardIndex &&
      incrementIndex > returnIndex &&
      requestIndex > incrementIndex,
    '第二次加载失败必须先返回，只有首次重试才能自增并申请新签名。',
  )
})

check('私有文件 ID 只接受相对地址、当前页面同源或 API 基址同源', () => {
  const relativeSourceBody = readFunctionBody(fileUrlComposable, 'isRelativeFileSource')
  assert.match(relativeSourceBody, /\^\[a-z\]\[a-z\\d\+\.\-\]\*:/i)
  assert.match(relativeSourceBody, /source\.startsWith\(['"]\/\/['"]\)/)

  const allowedOriginsBody = readFunctionBody(fileUrlComposable, 'getAllowedFileOrigins')
  assert.match(allowedOriginsBody, /typeof window\s*!==\s*['"]undefined['"]/)
  assert.match(allowedOriginsBody, /window\.location\.origin/)
  assert.match(allowedOriginsBody, /import\.meta\.env\.VITE_API_BASE/)
  assert.match(allowedOriginsBody, /allowedOrigins\.add\([^\n;]*\.origin\)/)

  const privateFileIdBody = readFunctionBody(fileUrlComposable, 'getPrivateFileId')
  assert.match(privateFileIdBody, /const parsed\s*=\s*new URL\(/)
  assert.match(privateFileIdBody, /allowedOrigins\.has\(parsed\.origin\)/)
  assert.match(
    privateFileIdBody,
    /if\s*\(\s*!isRelativeSource\s*&&\s*!allowedOrigins\.has\(parsed\.origin\)\s*\)\s*return null/,
  )
  const originGuardIndex = privateFileIdBody.indexOf('allowedOrigins.has(parsed.origin)')
  const privatePathIndex = privateFileIdBody.indexOf('PRIVATE_FILE_PATH')
  assert.ok(
    originGuardIndex >= 0 && privatePathIndex > originGuardIndex,
    '`https://cdn.example/api/files/42` 和 `//cdn.example/api/files/42` 必须先被 origin 白名单拦截，再决定是否匹配私有路径。',
  )
})

check('私有文件只申请签名 URL，不下载 Blob 或读取登录令牌', () => {
  assert.ok(fileUrlComposable.includes('const PRIVATE_FILE_PATH = /^\\/api\\/files\\/'))
  assert.match(fileUrlComposable, /getFileAccessUrl\(/)
  assert.doesNotMatch(fileUrlComposable, /\bfetch\s*\(/)
  assert.doesNotMatch(fileUrlComposable, /response\.blob\s*\(/)
  assert.doesNotMatch(fileUrlComposable, /URL\.createObjectURL\s*\(/)
  assert.doesNotMatch(fileUrlComposable, /localStorage|auth_token|[?&](?:token|access_token)=/)
})

check('公开、外链和非私有地址直接解析，不申请签名', () => {
  assert.match(fileUrlComposable, /fileId\s*===\s*null/)
  assert.match(fileUrlComposable, /resolveFileUrl\(/)
  assert.ok(fileUrlComposable.includes('const PUBLIC_MATERIAL_PATH = /^\\/api\\/public\\/learning\\/materials\\/'))
  assert.match(
    fileUrlComposable,
    /if \(fileId === null\) \{[\s\S]*?resolvedUrl\.value = resolveFileUrl\(source\)[\s\S]*?return[\s\S]*?\}[\s\S]*?await requestSignedUrl\(/,
  )
})

check('URL 工具只拼接基址，不读取存储或追加认证参数', () => {
  assert.match(urlUtil, /VITE_API_BASE/)
  assert.match(urlUtil, /\^https\?:/i)
  assert.match(urlUtil, /startsWith\(['"]\/\/['"]\)/)
  assert.match(
    urlUtil,
    /if\s*\(\/\^\[a-z\][^\n]+\.test\(url\)\)\s*return\s*['"]['"]/,
    '`javascript:`、HTML `data:` 等非 HTTP 协议必须被拒绝。',
  )
  const safeExternalIndex = urlUtil.search(/\^https\?:/i)
  const unsafeSchemeIndex = urlUtil.indexOf("return ''", safeExternalIndex)
  const baseIndex = urlUtil.indexOf('VITE_API_BASE', unsafeSchemeIndex)
  assert.ok(
    safeExternalIndex >= 0 && unsafeSchemeIndex > safeExternalIndex && baseIndex > unsafeSchemeIndex,
    'URL 工具必须先放行 HTTP(S)，再拒绝其他显式协议，最后才拼接 API 基址。',
  )
  assert.doesNotMatch(urlUtil, /localStorage|auth_token|encodeURIComponent|[?&](?:token|access_token)=/)
})

if (failures.length > 0) {
  throw new assert.AssertionError({
    message: `文件访问 URL 层仍有 ${failures.length} 项契约未满足：\n- ${failures.join('\n- ')}`,
  })
}

console.log('file access URL static checks passed')

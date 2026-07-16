import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function readFunctionBody(source, functionName) {
  const match = new RegExp(`function\\s+${functionName}\\s*\\(`).exec(source)
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

const materialApi = read('src/api/material.ts')
const card = read('src/components/common/MaterialRichCard.vue')
const dialog = read('src/components/common/MaterialPreviewDialog.vue')
const courseDetail = read('src/views/CourseDetailView.vue')
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')

assert.match(materialApi, /interface MaterialPreview/, '资料 API 应定义 MaterialPreview 类型。')
assert.match(materialApi, /preview\?: MaterialPreview/, 'Material 类型应包含 preview 字段。')
assert.match(materialApi, /\/materials\/\$\{materialId\}\/file/, '资料文件 URL 应使用资料专用文件接口。')
assert.match(materialApi, /preview\/rebuild/, '资料 API 应提供重建预览接口。')

assert.match(card, /AuthenticatedFileImage/, '图文资料卡片应通过认证图片组件展示封面。')
assert.match(card, /:file-id="material\.preview\?\.cover_file_id"/, '图文资料卡片封面应优先使用 cover_file_id。')
assert.match(card, /summaryText/, '图文资料卡片应展示摘要。')
assert.match(card, /预览生成中/, '图文资料卡片应展示预览生成中状态。')
assert.match(card, /预览生成失败/, '图文资料卡片应展示预览失败状态。')

assert.match(dialog, /<video/, '统一预览弹窗应支持视频。')
assert.match(dialog, /pdf/, '统一预览弹窗应支持 PDF。')
assert.match(dialog, /在新窗口打开/, '统一预览弹窗应保留新窗口打开入口。')
assert.match(dialog, /useAuthenticatedFileUrl/, '统一预览弹窗应通过组合式函数申请短时文件地址。')
assert.match(dialog, /resolvedUrl/, '统一预览弹窗应消费短时解析地址。')
assert.match(dialog, /retryOnce/, '统一预览弹窗的媒体加载失败应只续签重试一次。')
assert.doesNotMatch(dialog, /\bblobUrl\b|response\.blob\s*\(|URL\.createObjectURL\s*\(|\bfetch\s*\(/, '统一预览弹窗不得完整下载文件或继续使用 Blob URL。')
assert.match(dialog, /function handlePreviewError\(event:\s*Event\)[\s\S]*?getAttribute\(['"](?:src|data)['"]\)[\s\S]*?retryOnce\(failedUrl\)/, '预览错误应从实际媒体实例读取失败地址，避免旧事件污染新签名。')
assert.match(dialog, /<video[\s\S]*:key="resolvedUrl"/, '视频预览切换地址时应替换媒体实例以固化加载代次。')
assert.match(dialog, /<object[\s\S]*:key="resolvedUrl"/, 'PDF object 切换地址时应替换实例以固化加载代次。')
assert.match(dialog, /<video[\s\S]*:src="resolvedUrl"[\s\S]*@error="handlePreviewError"/, '视频预览应使用解析地址，并在加载失败时续签一次。')
assert.match(dialog, /<object[\s\S]*:data="resolvedUrl"[\s\S]*@error="handlePreviewError"/, 'PDF object 降级入口应使用解析地址，并在加载失败时续签一次。')
assert.match(dialog, /window\.open\(resolvedUrl\.value/, '新窗口入口应与站内预览使用同一个解析地址。')

const previewSourceBody = readFunctionBody(dialog, 'resolvePreviewSource')
const explicitPreviewIndex = previewSourceBody.indexOf('props.previewUrl')
const privateFileIndex = previewSourceBody.indexOf('props.material.file_id')
const externalUrlIndex = previewSourceBody.indexOf('props.material.url')
assert.ok(
  explicitPreviewIndex >= 0 &&
    privateFileIndex > explicitPreviewIndex &&
    externalUrlIndex > privateFileIndex,
  '预览源顺序必须是显式公开 previewUrl、私有 file_id、资料外链。',
)
assert.doesNotMatch(dialog, /getMaterialFileUrl/, '预览弹窗不得回退到旧资料文件接口。')

const inlineReader = read('src/components/learn/MaterialInlineReader.vue')
assert.doesNotMatch(inlineReader, /useAuthenticatedFileUrl|\bblobUrl\b|response\.blob\s*\(|URL\.createObjectURL\s*\(|\bfetch\s*\(/, '课程资料直读器只消费父级解析地址，不得再次申请或下载文件。')
assert.match(inlineReader, /fileLoading\??:\s*boolean/, '课程资料直读器应接收父级文件加载状态。')
assert.match(inlineReader, /fileError\??:\s*string/, '课程资料直读器应接收父级文件错误状态。')
assert.match(inlineReader, /defineEmits<[\s\S]*file-error/, '课程资料直读器应把媒体错误交给父级续签。')
assert.match(inlineReader, /\(e:\s*['"]file-error['"],\s*failedUrl:\s*string\)/, '直读器错误事件应携带实际失败地址。')
assert.match(inlineReader, /const pdfFailureHandler\s*=\s*computed\(\(\)\s*=>\s*\{[\s\S]*?const failedUrl\s*=\s*props\.fileUrl[\s\S]*?handlePdfFailed\(error,\s*failedUrl\)/, 'PDF.js 失败处理器应固化创建时的文件地址。')
assert.match(inlineReader, /if\s*\(!failedUrl\s*\|\|\s*failedUrl\s*!==\s*props\.fileUrl\)\s*return/, '旧 PDF 实例的延迟错误不得污染当前资料状态。')
assert.match(inlineReader, /emit\(['"]file-error['"],\s*failedUrl\)/, '直读器应把实际失败地址交给父级去重。')
assert.match(inlineReader, /<VuePdfEmbed[\s\S]*:key="fileUrl"[\s\S]*@loading-failed="pdfFailureHandler"[\s\S]*@rendering-failed="pdfFailureHandler"/, 'PDF.js 每个地址应使用独立实例和固化的失败处理器。')
assert.match(inlineReader, /<video[\s\S]*:key="fileUrl"[\s\S]*@error="handleVideoError"/, '视频直读应从独立媒体实例报告实际失败地址。')
assert.match(inlineReader, /<VuePdfEmbed[\s\S]*:source="fileUrl"/, 'PDF.js 应直接使用父级解析地址。')
assert.match(inlineReader, /<object\s+v-else-if="fileUrl && !fileError && pdfStatus === 'error'"[\s\S]*:data="fileUrl"/, 'PDF object 降级入口应只在 PDF.js 失败后使用同一解析地址。')
assert.doesNotMatch(inlineReader, /\.pdf-object-fallback\s*\{[\s\S]*?width:\s*1px[\s\S]*?opacity:\s*0/, 'PDF object 降级入口必须可见，不能隐藏后仍发起重复请求。')
assert.match(inlineReader, /<video[\s\S]*:src="fileUrl"[\s\S]*@error="handleVideoError"/, '视频直读应使用同一解析地址，并从媒体实例上报加载错误。')
assert.doesNotMatch(inlineReader, /:href="(?:material\.url|fileUrl\s*\|\|)/, '打开原资料不得绕过父级解析地址。')

assert.match(courseDetail, /useAuthenticatedFileUrl/, '课程详情应只在父级解析当前资料地址。')
assert.match(courseDetail, /activeMaterialResolvedUrl/, '课程详情应维护当前资料唯一解析地址。')
assert.match(courseDetail, /:file-url="activeMaterialResolvedUrl"/, '直读器应接收父级解析地址。')
assert.match(courseDetail, /:href="activeMaterialResolvedUrl"/, '右侧打开原资料应复用同一解析地址。')
assert.match(courseDetail, /:file-loading="activeMaterialFileLoading"/, '直读器应接收父级加载状态。')
assert.match(courseDetail, /:file-error="activeMaterialFileError"/, '直读器应接收父级错误状态。')
assert.match(courseDetail, /function handleActiveMaterialFileError\(failedUrl:\s*string\)[\s\S]*?retryActiveMaterialFileOnce\(failedUrl\)/, '父级应把失败地址传给单次续签去重。')
assert.match(courseDetail, /@file-error="handleActiveMaterialFileError"/, '直读器错误应连接到父级单次续签。')

assert.match(courseDetail, /MaterialInlineReader/, '学生课程详情应使用直读式资料阅读器。')
assert.match(courseDetail, /MaterialPreviewDialog/, '学生课程详情应使用统一预览弹窗。')
assert.match(teacherCourseDetail, /MaterialRichCard/, '教师课程详情应使用图文资料卡片。')
assert.match(teacherCourseDetail, /compact/, '教师课程详情阶段资料应使用紧凑扁平展示。')
assert.match(teacherCourseDetail, /material-flat-list/, '教师课程详情阶段资料应使用扁平列表容器。')
assert.match(teacherCourseDetail, /MaterialPreviewDialog/, '教师课程详情应使用统一预览弹窗。')
assert.match(teacherCourseDetail, /rebuildMaterialPreview/, '教师课程详情应提供重建预览入口。')
assert.match(card, /compact\?:/, '图文资料卡片应支持 compact 紧凑模式。')

console.log('material preview static checks passed')

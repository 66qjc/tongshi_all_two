import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  const path = resolve(root, relativePath)
  return existsSync(path) ? readFileSync(path, 'utf8') : ''
}

const pdfPreview = read('src/components/common/PdfPreviewDialog.vue')
const courseDetail = read('src/views/CourseDetailView.vue')
const teacherMaterials = read('src/views/teacher/TeacherMaterials.vue')
const adminPublicCourses = read('src/views/admin/AdminPublicCourses.vue')
const teacherReviews = read('src/views/teacher/TeacherReviews.vue')
const fileUrl = read('src/utils/url.ts')
const lessonReader = read('src/components/lesson/LessonReader.vue')
const authenticatedLessonVideo = read('src/components/lesson/AuthenticatedLessonVideo.vue')

assert.match(fileUrl, /VITE_API_BASE/, '文件 URL 工具应继续把相对地址拼接到 API 基址。')
assert.doesNotMatch(fileUrl, /localStorage|auth_token|[?&](?:token|access_token)=/, '文件 URL 工具不得把普通登录令牌放进 URL。')

assert.doesNotMatch(pdfPreview, /<iframe\b/, '公共 PDF 预览组件不应再依赖 iframe 内嵌预览。')
assert.match(pdfPreview, /openInNewWindow/, '公共 PDF 预览组件应保留新窗口打开入口。')
assert.match(pdfPreview, /在新窗口打开/, '公共 PDF 预览组件应使用清晰的新窗口打开文案。')

assert.match(courseDetail, /MaterialPreviewDialog/, '学生课程资料应通过站内预览弹窗打开。')

const previewDialog = read('src/components/common/MaterialPreviewDialog.vue')
assert.match(previewDialog, /resolvedUrl/, '预览弹窗应使用短时解析地址。')
assert.doesNotMatch(previewDialog, /getMaterialFileUrl|\bblobUrl\b/, '预览弹窗不应再回退旧资料接口或 Blob URL。')

assert.match(lessonReader, /AuthenticatedLessonVideo/, '课时阅读器应使用认证视频组件。')
assert.doesNotMatch(lessonReader, /<video\b/, '课时阅读器不得把原始私有地址直接绑定到 video。')
assert.match(authenticatedLessonVideo, /useAuthenticatedFileUrl/, '认证视频组件应申请短时文件地址。')
assert.match(authenticatedLessonVideo, /:src="resolvedUrl"/, '认证视频组件应把解析地址交给浏览器 Range 播放。')
assert.match(authenticatedLessonVideo, /retryOnce/, '视频加载失败应只续签重试一次。')
assert.match(authenticatedLessonVideo, /beforeUrlRenewalPosition/, '签名续期后应优先恢复续期前的播放位置。')
assert.match(
  authenticatedLessonVideo,
  /watch\(\s*\(\)\s*=>\s*props\.sourceUrl[\s\S]*?beforeUrlRenewalPosition\.value\s*=\s*props\.resumePosition\s*\|\|\s*0/,
  '原始视频源变化时必须重置为新课时的恢复位置，不能继承上一视频进度。',
)
assert.match(authenticatedLessonVideo, /let lastResolvedSource\s*=\s*props\.sourceUrl/, '认证视频组件应记录解析地址对应的原始来源。')
assert.match(
  authenticatedLessonVideo,
  /const sourceUnchanged\s*=\s*lastResolvedSource\s*===\s*props\.sourceUrl[\s\S]*?lastResolvedSource\s*=\s*props\.sourceUrl/,
  '解析地址变化时应先判断原始来源是否仍相同。',
)
assert.match(
  authenticatedLessonVideo,
  /if\s*\(video\s*&&\s*previousUrl\s*&&\s*sourceUnchanged\)/,
  '只有同一原始来源的签名续期才能保存旧视频播放位置。',
)
assert.match(authenticatedLessonVideo, /mediaFailed/, '认证视频组件应记录媒体重试后的最终失败状态。')
assert.match(
  authenticatedLessonVideo,
  /async function handleVideoError\(event:\s*Event\)[\s\S]*?getAttribute\(['"]src['"]\)[\s\S]*?await retryOnce\(failedUrl\)[\s\S]*?if\s*\(failedUrl\s*!==\s*resolvedUrl\.value\)\s*return[\s\S]*?if\s*\(error\.value\)[\s\S]*?mediaFailed\.value\s*=\s*true/,
  '视频续签失败或同源第二次错误后应进入可见失败状态。',
)
assert.match(authenticatedLessonVideo, /<video[\s\S]*:key="resolvedUrl"/, '签名或原始来源变化时应使用独立视频实例固化错误代次。')
assert.match(
  authenticatedLessonVideo,
  /v-if="mediaFailed"[\s\S]*?\{\{\s*error\s*\|\|\s*['"][^'"]*[\u4e00-\u9fff][^'"]*['"]\s*\}\}/,
  '最终失败后应显示中文错误，而不是继续保留失效的视频元素。',
)
assert.match(authenticatedLessonVideo, /video\.pause\(\)/, '卸载时应暂停视频。')
assert.match(authenticatedLessonVideo, /video\.removeAttribute\(['"]src['"]\)/, '卸载时应移除旧视频地址。')
assert.match(authenticatedLessonVideo, /video\.load\(\)/, '卸载时应释放媒体资源。')

assert.match(teacherMaterials, /MaterialPreviewDialog/, '教师资料管理应通过站内预览弹窗打开。')

assert.match(adminPublicCourses, /PdfPreviewDialog/, '管理员公共课程资料应复用公共预览入口。')
assert.match(adminPublicCourses, /previewFileId\.value\s*=\s*row\.file_id/, '管理员公共课程资料应优先传入 file_id。')

assert.doesNotMatch(teacherReviews, /<iframe\b/, '教师作品审核不应再依赖 iframe 内嵌 PDF。')
assert.match(teacherReviews, /reportPreviewUrl/, '教师作品审核应保留报告文件访问地址。')
assert.match(teacherReviews, /在新窗口打开 PDF/, '教师作品审核应提供在新窗口打开 PDF 入口。')

console.log('local file preview static checks passed')

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
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
const adminPublicCourses = read('src/views/admin/AdminPublicCourses.vue')
const teacherReviews = read('src/views/teacher/TeacherReviews.vue')
const fileUrl = read('src/utils/url.ts')
const inlineReader = read('src/components/learn/MaterialInlineReader.vue')

assert.match(fileUrl, /VITE_API_BASE/, '文件 URL 工具应继续把相对地址拼接到 API 基址。')
assert.doesNotMatch(fileUrl, /localStorage|auth_token|[?&](?:token|access_token)=/, '文件 URL 工具不得把普通登录令牌放进 URL。')

assert.doesNotMatch(pdfPreview, /<iframe\b/, '公共 PDF 预览组件不应再依赖 iframe 内嵌预览。')
assert.match(pdfPreview, /openInNewWindow/, '公共 PDF 预览组件应保留新窗口打开入口。')
assert.match(pdfPreview, /在新窗口打开/, '公共 PDF 预览组件应使用清晰的新窗口打开文案。')

assert.match(courseDetail, /MaterialPreviewDialog/, '学生课程资料应通过站内预览弹窗打开。')
assert.match(courseDetail, /MaterialInlineReader/, '学生课程详情应通过资料直读器阅读正文。')
assert.match(courseDetail, /useAuthenticatedFileUrl/, '学生课程详情应解析认证文件地址。')
assert.match(courseDetail, /getPublicMaterialFileUrl/, '公开资料应使用公开文件接口。')
assert.doesNotMatch(courseDetail, /AuthenticatedLessonVideo|LessonReader/, '学生课程详情不得再依赖课时视频组件。')

const previewDialog = read('src/components/common/MaterialPreviewDialog.vue')
assert.match(previewDialog, /resolvedUrl/, '预览弹窗应使用短时解析地址。')
assert.doesNotMatch(previewDialog, /getMaterialFileUrl|\bblobUrl\b/, '预览弹窗不应再回退旧资料接口或 Blob URL。')

assert.match(inlineReader, /VuePdfEmbed/, '资料直读器应使用 vue-pdf-embed 渲染 PDF。')
assert.match(inlineReader, /:source="fileUrl"/, '资料直读器应把父级解析地址交给 PDF 渲染。')
assert.match(inlineReader, /<video[\s\S]*controls/, '资料直读器应支持视频控件播放。')
assert.doesNotMatch(inlineReader, /useAuthenticatedFileUrl|\bblobUrl\b/, '直读器不得自行申请令牌或 Blob。')

assert.match(teacherCourseDetail, /MaterialPreviewDialog/, '教师课程详情应通过站内预览弹窗打开。')

assert.match(adminPublicCourses, /PdfPreviewDialog/, '管理员公共课程资料应复用公共预览入口。')
assert.match(adminPublicCourses, /previewFileId\.value\s*=\s*row\.file_id/, '管理员公共课程资料应优先传入 file_id。')

assert.doesNotMatch(teacherReviews, /<iframe\b/, '教师作品审核不应再依赖 iframe 内嵌 PDF。')
assert.match(teacherReviews, /reportPreviewUrl/, '教师作品审核应保留报告文件访问地址。')
assert.match(teacherReviews, /在新窗口打开 PDF/, '教师作品审核应提供在新窗口打开 PDF 入口。')

console.log('local file preview static checks passed')

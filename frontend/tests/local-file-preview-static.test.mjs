import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const pdfPreview = read('src/components/common/PdfPreviewDialog.vue')
const courseDetail = read('src/views/CourseDetailView.vue')
const teacherMaterials = read('src/views/teacher/TeacherMaterials.vue')
const adminPublicCourses = read('src/views/admin/AdminPublicCourses.vue')
const teacherReviews = read('src/views/teacher/TeacherReviews.vue')
const fileUrl = read('src/utils/url.ts')

assert.match(fileUrl, /url\.startsWith\('\/api\/files\/'\)/, '文件 URL 工具应继续识别统一文件入口。')
assert.match(fileUrl, /token=/, '统一文件入口应为新窗口、iframe、video 等场景追加 URL token。')

assert.doesNotMatch(pdfPreview, /<iframe\b/, '公共 PDF 预览组件不应再依赖 iframe 内嵌预览。')
assert.match(pdfPreview, /openInNewWindow/, '公共 PDF 预览组件应保留新窗口查看入口。')
assert.match(pdfPreview, /新窗口查看/, '公共 PDF 预览组件应使用清晰的新窗口查看文案。')

assert.match(courseDetail, /target="_blank"/, '学生课程资料应通过新窗口打开文件。')
assert.match(courseDetail, /item\.file_id\s*\?\s*`\/api\/files\/\$\{item\.file_id\}`\s*:\s*item\.url/, '学生课程资料应优先使用 file_id 统一入口。')

assert.match(teacherMaterials, /window\.open\(url,\s*'_blank'/, '教师资料管理应通过新窗口打开文件。')
assert.match(teacherMaterials, /row\.file_id\s*\?\s*`\/api\/files\/\$\{row\.file_id\}`\s*:\s*row\.url/, '教师资料管理应优先使用 file_id 统一入口。')

assert.match(adminPublicCourses, /PdfPreviewDialog/, '管理员公共课程资料应复用公共预览入口。')
assert.match(adminPublicCourses, /previewFileId\.value\s*=\s*row\.file_id/, '管理员公共课程资料应优先传入 file_id。')

assert.doesNotMatch(teacherReviews, /<iframe\b/, '教师作品审核不应再依赖 iframe 内嵌 PDF。')
assert.match(teacherReviews, /reportPreviewUrl/, '教师作品审核应保留报告文件访问地址。')
assert.match(teacherReviews, /新窗口查看 PDF/, '教师作品审核应提供新窗口查看 PDF 入口。')

console.log('local file preview static checks passed')

import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  const path = resolve(root, relativePath)
  return existsSync(path) ? readFileSync(path, 'utf8') : ''
}

function countMatches(source, pattern) {
  return [...source.matchAll(pattern)].length
}

const authenticatedImage = read('src/components/common/AuthenticatedFileImage.vue')
const materialRichCard = read('src/components/common/MaterialRichCard.vue')
const pdfPreview = read('src/components/common/PdfPreviewDialog.vue')
const profileApi = read('src/api/profile.ts')
const createView = read('src/views/CreateView.vue')
const profileView = read('src/views/ProfileView.vue')
const projectDetail = read('src/views/ProjectDetailView.vue')
const projectUpload = read('src/views/ProjectUploadView.vue')
const actView = read('src/views/ActView.vue')
const actDetail = read('src/views/ActDetailView.vue')
const teacherReviews = read('src/views/teacher/TeacherReviews.vue')
const teacherMaterials = read('src/views/teacher/TeacherMaterials.vue')
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
const adminPublicCourses = read('src/views/admin/AdminPublicCourses.vue')
const adminShowcase = read('src/views/admin/AdminShowcase.vue')

const failures = []

function check(name, assertion) {
  try {
    assertion()
  } catch (error) {
    failures.push(`${name}: ${error instanceof Error ? error.message : String(error)}`)
  }
}

check('认证图片组件只向真实 img 透传属性并使用短时签名地址', () => {
  assert.ok(authenticatedImage, '缺少 AuthenticatedFileImage.vue')
  assert.match(authenticatedImage, /defineOptions\(\{\s*inheritAttrs:\s*false\s*\}\)/)
  assert.match(authenticatedImage, /fileId\?:\s*number\s*\|\s*null/)
  assert.match(authenticatedImage, /fallbackUrl\?:\s*string/)
  assert.match(authenticatedImage, /props\.fileId\s*\?\s*`\/api\/files\/\$\{props\.fileId\}`\s*:\s*props\.fallbackUrl/)
  assert.match(authenticatedImage, /useAuthenticatedFileUrl\(/)
  assert.match(authenticatedImage, /<img[\s\S]*?v-bind="\$attrs"[\s\S]*?:src="resolvedUrl"/)
  assert.doesNotMatch(authenticatedImage, /<div|<span|<figure/)
  assert.doesNotMatch(authenticatedImage, /\bfetch\s*\(|\.blob\s*\(|createObjectURL|localStorage|auth_token/)
})

check('认证图片失败时使用真实 src 触发一次续签重试', () => {
  assert.match(authenticatedImage, /getAttribute\(['"]src['"]\)/)
  assert.match(authenticatedImage, /retryOnce\(failedUrl\)/)
  assert.match(authenticatedImage, /failedUrl\s*!==\s*resolvedUrl\.value/)
})

check('资料富卡片的预览封面使用认证图片组件', () => {
  assert.match(materialRichCard, /import AuthenticatedFileImage/)
  assert.match(materialRichCard, /<AuthenticatedFileImage/)
  assert.match(materialRichCard, /:file-id="material\.preview\?\.cover_file_id"/)
  assert.doesNotMatch(materialRichCard, /resolveFileUrl/)
})

check('作品列表和收藏列表优先使用 cover_file_id 或首图 file_id', () => {
  for (const [name, source] of [
    ['CreateView', createView],
    ['ProfileView', profileView],
    ['ActView', actView],
  ]) {
    assert.match(source, /import AuthenticatedFileImage/, `${name} 未引入认证图片组件`)
    assert.match(
      source,
      /:file-id="project\.cover_file_id\s*\|\|\s*project\.images\?\.\[0\]\?\.file_id"/,
      `${name} 未优先使用封面或首图 file_id`,
    )
    assert.match(
      source,
      /:fallback-url="project\.images\?\.\[0\]\?\.image_url\s*\|\|\s*project\.image_url"/,
      `${name} 未保留历史 URL 回退`,
    )
  }
})

check('作品详情多图和大图弹窗保留每张图片的 file_id', () => {
  assert.match(projectDetail, /import AuthenticatedFileImage/)
  assert.match(projectDetail, /fileId:\s*item\.file_id/)
  assert.match(projectDetail, /url:\s*item\.image_url/)
  assert.ok(
    countMatches(projectDetail, /<AuthenticatedFileImage\b/g) >= 3,
    '作品详情的主图、图片列表和大图弹窗都应使用认证图片组件',
  )
  assert.match(projectDetail, /:file-id="projectCover\.fileId"/)
  assert.match(projectDetail, /:file-id="image\.fileId"/)
  assert.match(projectDetail, /:file-id="previewImage\.fileId"/)
})

check('作品详情报告优先 report_file_id 并通过组合式函数签名', () => {
  assert.match(projectDetail, /const reportSource\s*=\s*computed/)
  assert.match(projectDetail, /report_file_id[\s\S]*?`\/api\/files\/\$\{[^}]*report_file_id\}`[\s\S]*?report_url/)
  assert.match(projectDetail, /useAuthenticatedFileUrl\(reportSource/)
  assert.match(projectDetail, /v-if="reportSource"/)
  assert.match(projectDetail, /:href="reportResolvedUrl"/)
  assert.match(projectDetail, /resolveFileUrl\(projectLink\)/)
})

check('重新提交页面的历史图片使用认证图片组件', () => {
  assert.match(projectUpload, /import AuthenticatedFileImage/)
  assert.match(projectUpload, /<AuthenticatedFileImage/)
  assert.match(projectUpload, /:file-id="img\.file_id"/)
  assert.match(projectUpload, /:fallback-url="img\.url"/)
  assert.doesNotMatch(projectUpload, /resolveFileUrl/)
})

check('教师审核图片和报告均使用短时签名地址', () => {
  assert.match(teacherReviews, /import AuthenticatedFileImage/)
  assert.match(teacherReviews, /fileId:\s*item\.file_id/)
  assert.ok(
    countMatches(teacherReviews, /<AuthenticatedFileImage\b/g) >= 2,
    '教师审核缩略图和大图弹窗都应使用认证图片组件',
  )
  assert.match(teacherReviews, /const reportSource\s*=\s*computed/)
  assert.match(teacherReviews, /report_file_id[\s\S]*?`\/api\/files\/\$\{[^}]*report_file_id\}`[\s\S]*?report_url/)
  assert.match(teacherReviews, /useAuthenticatedFileUrl\(reportSource/)
  assert.match(teacherReviews, /:href="reportPreviewUrl"/)
})

check('通用 PDF 弹窗使用 resolvedUrl 而非直接解析私有文件路径', () => {
  assert.match(pdfPreview, /useAuthenticatedFileUrl\(/)
  assert.match(pdfPreview, /const sourceUrl\s*=\s*computed/)
  assert.match(pdfPreview, /resolvedUrl/)
  assert.match(pdfPreview, /window\.open\(resolvedUrl\.value/)
  assert.doesNotMatch(pdfPreview, /resolveFileUrl/)
})

check('教师资料页面删除未调用的旧私有文件直开函数', () => {
  assert.doesNotMatch(teacherMaterials, /resolveFileUrl/)
  assert.doesNotMatch(teacherMaterials, /function openMaterial\s*\(/)
  assert.doesNotMatch(teacherCourseDetail, /resolveFileUrl/)
  assert.doesNotMatch(teacherCourseDetail, /function materialUrl\s*\(/)
  assert.doesNotMatch(teacherCourseDetail, /function openMaterial\s*\(/)
})

check('收藏作品类型与后端 format_project 的文件字段一致', () => {
  assert.match(profileApi, /cover_file_id\?:\s*number/)
  assert.match(profileApi, /images:\s*\{[^}]*file_id\?:\s*number[^}]*image_url:\s*string[^}]*\}\[\]/)
})

check('管理员内容管理的封面和内容块图片使用认证图片组件', () => {
  assert.match(adminShowcase, /import AuthenticatedFileImage/)
  assert.ok(
    countMatches(adminShowcase, /<AuthenticatedFileImage\b/g) >= 4,
    '管理员两类列表封面、内容块图片和编辑封面都应使用认证图片组件',
  )
  assert.match(adminShowcase, /:file-id="block\.data\.file_id"/)
  assert.match(adminShowcase, /:file-id="coverFileId"/)
  assert.match(adminShowcase, /:fallback-url="coverPreviewUrl"/)
  assert.doesNotMatch(adminShowcase, /<img\s+:src="`\/api\/files\//)
})

check('管理员公共课程继续把 file_id 传给 PDF 弹窗', () => {
  assert.match(adminPublicCourses, /previewFileId\.value\s*=\s*row\.file_id/)
  assert.match(adminPublicCourses, /<PdfPreviewDialog[\s\S]*?:file-id="previewFileId"/)
})

check('公开活动图片保持匿名直连，登录后作品图片才走签名', () => {
  assert.ok(
    countMatches(actView, /<img\s+:src="item\.cover_url"/g) >= 2,
    '公益课和读书会公开封面必须继续匿名直连',
  )
  assert.match(actView, /<AuthenticatedFileImage[\s\S]*?project\.cover_file_id/)
  assert.doesNotMatch(actDetail, /AuthenticatedFileImage/)
  assert.match(actDetail, /resolveFileUrl\(item\.value\?\.cover_url\)/)
})

if (failures.length > 0) {
  throw new assert.AssertionError({
    message: `受保护文件消费者仍有 ${failures.length} 项契约未满足：\n- ${failures.join('\n- ')}`,
  })
}

console.log('protected file consumer static checks passed')

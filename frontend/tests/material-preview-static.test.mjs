import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const materialApi = read('src/api/material.ts')
const card = read('src/components/common/MaterialRichCard.vue')
const dialog = read('src/components/common/MaterialPreviewDialog.vue')
const courseDetail = read('src/views/CourseDetailView.vue')
const teacherMaterials = read('src/views/teacher/TeacherMaterials.vue')
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')

assert.match(materialApi, /interface MaterialPreview/, '资料 API 应定义 MaterialPreview 类型。')
assert.match(materialApi, /preview\?: MaterialPreview/, 'Material 类型应包含 preview 字段。')
assert.match(materialApi, /\/materials\/\$\{materialId\}\/file/, '资料文件 URL 应使用资料专用文件接口。')
assert.match(materialApi, /preview\/rebuild/, '资料 API 应提供重建预览接口。')

assert.match(card, /coverUrl/, '图文资料卡片应展示封面。')
assert.match(card, /summaryText/, '图文资料卡片应展示摘要。')
assert.match(card, /预览生成中/, '图文资料卡片应展示预览生成中状态。')
assert.match(card, /预览生成失败/, '图文资料卡片应展示预览失败状态。')

assert.match(dialog, /<video/, '统一预览弹窗应支持视频。')
assert.match(dialog, /pdf/, '统一预览弹窗应支持 PDF。')
assert.match(dialog, /在新窗口打开/, '统一预览弹窗应保留新窗口打开入口。')

assert.match(courseDetail, /MaterialRichCard/, '学生课程详情应使用图文资料卡片。')
assert.match(courseDetail, /MaterialPreviewDialog/, '学生课程详情应使用统一预览弹窗。')
assert.match(teacherMaterials, /MaterialRichCard/, '教师资料管理应使用图文资料卡片或混合列表。')
assert.match(teacherMaterials, /rebuildMaterialPreview/, '教师资料管理应提供重建预览入口。')
assert.match(teacherCourseDetail, /MaterialRichCard/, '教师课程详情应使用图文资料卡片。')
assert.match(teacherCourseDetail, /MaterialPreviewDialog/, '教师课程详情应使用统一预览弹窗。')

console.log('material preview static checks passed')

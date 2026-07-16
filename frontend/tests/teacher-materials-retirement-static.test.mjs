import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = relativePath => readFileSync(resolve(root, relativePath), 'utf8')

assert.equal(
  existsSync(resolve(root, 'src/views/teacher/TeacherMaterials.vue')),
  false,
  '独立教师资料管理页面应已删除',
)

const router = read('src/router/index.ts')
assert.doesNotMatch(
  router,
  /path:\s*['"]materials['"]|teacher-materials|TeacherMaterials/,
  '教师子路由不得保留独立资料页、redirect 或组件引用',
)
assert.match(router, /path:\s*['"]\/:pathMatch\(\.\*\)\*['"]/, '全局 404 路由必须保留')

const layout = read('src/views/teacher/TeacherLayout.vue')
const dashboard = read('src/views/teacher/TeacherDashboard.vue')
assert.doesNotMatch(layout, /\/teacher\/materials|资料管理/, '教师侧栏不得生成旧资料地址')
assert.doesNotMatch(dashboard, /\/teacher\/materials/, '教师工作台不得生成旧资料地址')

const materialApi = read('src/api/material.ts')
assert.doesNotMatch(materialApi, /getAllMaterials|PaginatedResult/, '前端应删除旧页专用分页 API')
assert.match(materialApi, /getCourseContents/, '课程详情资料列表 API 必须保留')
assert.match(materialApi, /createMaterial/, '课程详情上传资料 API 必须保留')
assert.match(materialApi, /updateMaterial/, '课程详情编辑资料 API 必须保留')
assert.match(materialApi, /deleteMaterial/, '课程详情删除资料 API 必须保留')
assert.match(materialApi, /rebuildMaterialPreview/, '课程详情预览重建 API 必须保留')

const courseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
for (const pattern of [
  /MaterialRichCard/,
  /MaterialPreviewDialog/,
  /openUploadMaterial/,
  /handleSaveMaterial/,
  /handleDeleteMaterial/,
  /handleRebuildPreview/,
]) {
  assert.match(courseDetail, pattern, '课程详情必须继续承接资料管理能力')
}

console.log('独立教师资料管理页面退役检查通过')

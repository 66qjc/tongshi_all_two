import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const teacher = read('src/views/teacher/TeacherCourseDetail.vue')
const admin = read('src/views/admin/AdminPublicCourses.vue')
const courseApi = read('src/api/course.ts')
const adminApi = read('src/api/adminPublicCourse.ts')

assert.match(courseApi, /cascadeMaterials|cascade_materials/, '教师删阶段 API 应支持级联参数')
assert.match(adminApi, /cascadeMaterials|cascade_materials/, '管理端删阶段 API 应支持级联参数')
assert.match(teacher, /cascadeMaterials:\s*true/, '教师删阶段应请求级联')
assert.match(teacher, /同时删除该阶段下/, '教师确认文案应说明会删阶段下资料')
assert.doesNotMatch(
  teacher,
  /该阶段下仍有资料。请先编辑这些资料，将所属阶段改为「未分类」/,
  '教师不应再仅用旧拦截文案阻断删阶段',
)
assert.match(admin, /cascadeMaterials:\s*true/, '管理端删阶段应请求级联')
assert.match(admin, /同时删除该阶段下/, '管理端确认文案应说明会删阶段下资料')
assert.match(admin, /教师自行新增资料会保留并移至未分类/, '管理端删阶段应说明教师自建资料会保留')
assert.match(
  admin,
  /async function handleDeleteStage[\s\S]*?Promise\.all\(\[fetchContent\(\), fetchCourses\(selectedCourse\.value\.id\)\]\)/,
  '管理端删阶段后应同时刷新详情和课程列表',
)
assert.match(admin, /已同步到教师课程副本的资料会保留/, '单份公共资料删除文案应符合保留副本的语义')

console.log('course-stage-delete-static.test.mjs passed')

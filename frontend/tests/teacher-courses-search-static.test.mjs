import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const teacherCourses = read('src/views/teacher/TeacherCourses.vue')

assert.match(teacherCourses, /const mySearchKeyword = ref\(''\)/, '教师课程页应维护我的课程搜索关键词。')
assert.match(
  teacherCourses,
  /async function loadMyCourses\(\)[\s\S]*keyword:\s*mySearchKeyword\.value\s*\|\|\s*undefined,[\s\S]*scope:\s*'owned'/,
  '我的课程分页请求应把搜索关键词传给后端 owned 列表。'
)
assert.match(
  teacherCourses,
  /function handleMySearch\(\)[\s\S]*myPage\.value = 1[\s\S]*loadMyCourses\(\)/,
  '执行我的课程搜索时应回到第一页并重新加载。'
)
assert.match(
  teacherCourses,
  /v-model="mySearchKeyword"[\s\S]*placeholder="搜索已添加课程"/,
  '教师课程页应渲染已添加课程搜索输入框。'
)
assert.match(
  teacherCourses,
  /@keyup\.enter="handleMySearch"[\s\S]*@clear="handleMySearch"/,
  '已添加课程搜索输入框应支持回车搜索和清空刷新。'
)

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const router = read('src/router/index.ts')
const app = read('src/App.vue')
const teacherLayout = read('src/views/teacher/TeacherLayout.vue')

assert.match(router, /function\s+isStudentBusinessPath\s*\(/, '路由守卫应提供学生端业务路径识别函数。')
assert.match(router, /authStore\.user\?\.role === 'teacher'[\s\S]*isStudentBusinessPath\(to\.path\)[\s\S]*return '\/teacher'/, '教师访问学生端业务路径时应回到教师工作台。')
assert.match(router, /to\.path === '\/'[\s\S]*authStore\.user\?\.role === 'teacher'[\s\S]*return '\/teacher'/, '教师访问首页时应回到教师工作台。')

assert.match(app, /const\s+isWorkbenchRoute\s*=\s*computed\(/, 'App.vue 应识别后台工作台路由。')
assert.match(app, /<AppHeader\s+v-if="!isWorkbenchRoute"\s*\/>/, '教师端和管理端不应渲染学生端全局头部。')
assert.match(app, /<AppFooter\s+v-if="!isWorkbenchRoute"\s*\/>/, '教师端和管理端不应渲染学生端全局底部。')

assert.match(teacherLayout, /<router-link to="\/teacher" class="logo-link">/, '教师工作台 Logo 应指向教师工作台。')
assert.match(teacherLayout, /function\s+handleLogout\s*\(\)[\s\S]*authStore\.logout\(\)[\s\S]*router\.push\('\/login'\)/, '教师工作台应提供退出登录逻辑。')
assert.match(teacherLayout, /<button class="btn-logout" @click="handleLogout">退出登录<\/button>/, '教师工作台应提供退出登录按钮。')
assert.doesNotMatch(teacherLayout, /返回学生端/, '教师工作台不应显示返回学生端文案。')
assert.doesNotMatch(teacherLayout, /回到首页/, '教师工作台不应显示回到首页入口。')
assert.doesNotMatch(teacherLayout, /btn-student-view/, '教师工作台不应保留返回学生端按钮样式。')
assert.doesNotMatch(teacherLayout, /btn-home/, '教师工作台不应保留回到首页按钮样式。')

console.log('teacher workbench only static checks passed')

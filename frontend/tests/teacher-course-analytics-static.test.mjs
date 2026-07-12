import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const root = resolve(import.meta.dirname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const progressApi = read('src/api/progress.ts')
assert.match(progressApi, /export interface CourseAnalytics/, '进度 API 应声明课程学习分析返回类型')
assert.match(progressApi, /student_progress:\s*\{[\s\S]*items:[\s\S]*total:[\s\S]*page:[\s\S]*page_size:/, '课程学习分析应返回学生分页对象')
assert.match(progressApi, /export function getCourseAnalytics\(/, '进度 API 应封装教师端课程学习分析接口')
assert.match(progressApi, /params:\s*\{\s*page,\s*page_size:\s*pageSize\s*\}/, '课程学习分析 API 应传递页码和页大小')

const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
assert.match(teacherCourseDetail, /getCourseAnalytics/, '教师课程详情应加载课程学习分析数据')
assert.match(teacherCourseDetail, /name="analytics"/, '教师课程详情应提供学习分析标签页')
assert.match(teacherCourseDetail, /学习分析/u, '学习分析标签页应使用中文标题')
assert.match(teacherCourseDetail, /疑似刷课/u, '教师端分析应展示疑似刷课指标')
assert.match(teacherCourseDetail, /analytics\.student_progress\.items/, '教师端分析表格应读取服务端分页明细')
assert.match(teacherCourseDetail, /<el-pagination/, '教师端分析应提供 Element Plus 分页器')
assert.match(teacherCourseDetail, /:disabled="analyticsLoading"/, '分析请求期间应禁用分页器，避免重复翻页覆盖结果')
assert.match(teacherCourseDetail, /:total="analytics\.student_progress\.total"/, '分页总数应使用后端返回的学生总数')
assert.match(teacherCourseDetail, /handleAnalyticsPageChange/, '切换页码应重新请求分析接口')
assert.match(teacherCourseDetail, /handleAnalyticsPageSizeChange/, '切换页大小应重置页码并重新请求分析接口')
const studentCourseDetail = read('src/views/CourseDetailView.vue')
assert.match(studentCourseDetail, /pagehide/, '课程详情应在浏览器离页时补报学习进度')
assert.match(studentCourseDetail, /reportLessonProgressKeepalive/, '浏览器离页补报应使用可保持请求的进度 API')
assert.match(progressApi, /keepalive:\s*true/, '离页进度 API 应启用 fetch keepalive')
const mojibakePattern = new RegExp('[\\uFFFD]|\\?{3,}|\\u040e\\u045e|\\u045e|\\u040e')
assert.doesNotMatch(teacherCourseDetail, mojibakePattern, '教师课程详情不能包含乱码文案')

console.log('教师课程学习分析静态检查通过')

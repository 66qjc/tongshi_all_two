import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import assert from 'node:assert/strict'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const taskReport = readFileSync(resolve(root, 'src/views/teacher/TeacherTaskReport.vue'), 'utf8')
const studentGrades = readFileSync(resolve(root, 'src/views/teacher/TeacherStudents.vue'), 'utf8')
const teacherApi = readFileSync(resolve(root, 'src/api/teacher.ts'), 'utf8')

assert.match(taskReport, /getTaskOverview/, '作业完成页应使用作业概览接口展示作业列表')
assert.match(taskReport, /taskSearchQuery/, '作业完成页应保留作业名称搜索能力')
assert.match(taskReport, /goToDetail/, '作业完成页应通过作业卡片进入完成详情')
assert.match(taskReport, /teacher-task-report-detail/, '作业完成页应跳转到任务完成详情路由')
assert.match(taskReport, /route\.query\.task_id/, '作业完成页应保留从教师端其他页面带 task_id 跳转定位')

assert.doesNotMatch(studentGrades, /getTaskOverview/, '学生成绩页不应再加载作业概览')
assert.doesNotMatch(studentGrades, /TeacherTaskDetail/, '学生成绩页不应再展示作业详情抽屉')
assert.doesNotMatch(studentGrades, /task-list/, '学生成绩页不应再渲染作业列表卡片')
assert.match(studentGrades, /filter\(course => course\.is_owner\)/, '学生成绩页课程下拉框只应展示教师自己的课程')
assert.match(taskReport, /filter\(course => course\.is_owner\)/, '作业完成页课程下拉框只应展示教师自己的课程')
assert.match(teacherApi, /task_scores/, '教师端学生类型应包含每次作业成绩')
assert.match(studentGrades, /作业成绩/, '学生成绩页应展示作业成绩列')
assert.match(studentGrades, /visibleTaskScores/, '学生成绩页应只内联展示前三次作业成绩')
assert.match(studentGrades, /scoreDialogVisible/, '学生成绩页应提供完整作业成绩详情弹窗')

console.log('teacher task report migration static checks passed')

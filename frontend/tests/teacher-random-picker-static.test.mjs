import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const picker = readFileSync(resolve(root, 'src/views/teacher/TeacherRandomPicker.vue'), 'utf8')
const classApi = readFileSync(resolve(root, 'src/api/class.ts'), 'utf8')

assert.match(
  picker,
  /import\s*\{[^}]*getClasses[^}]*getClassStudents[^}]*type\s+ClassInfo[^}]*\}\s*from\s*['"]@\/api\/class['"]/,
  '随机点名必须导入真实学生列表接口和 ClassInfo 类型',
)
assert.match(
  picker,
  /await\s+getClassStudents\(selectedClassId\.value\)/,
  '随机点名必须按当前班级 ID 请求学生列表',
)
assert.doesNotMatch(
  picker,
  /classData\.students|\.students\?\s*\)/,
  '随机点名不能读取班级摘要中不存在的 students 字段',
)
assert.doesNotMatch(
  classApi,
  /export\s+type\s+Class\s*=\s*ClassInfo\s*&\s*\{\s*students\?/,
  '班级 API 不应通过可选 students 字段伪装列表契约',
)
assert.match(
  picker,
  /const\s+currentRequestId\s*=\s*\+\+studentRequestId[\s\S]*currentRequestId\s*!==\s*studentRequestId/,
  '学生加载必须用请求序号阻止旧请求覆盖新班级',
)
assert.match(
  picker,
  /function\s+clearStudentState\([\s\S]*students\.value\s*=\s*\[\][\s\S]*availableStudents\.value\s*=\s*\[\][\s\S]*calledStudents\.value\s*=\s*\[\][\s\S]*currentStudent\.value\s*=\s*null/,
  '空班级或切班时必须完整清空点名状态',
)
assert.match(
  picker,
  /let\s+animationTimer[^\n]*ReturnType<typeof setInterval>[\s\S]*function\s+stopAnimation\([\s\S]*clearInterval\(animationTimer\)/,
  '抽取动画必须保存可清理的 interval 句柄',
)
assert.match(
  picker,
  /async\s+function\s+handleClassChange\([\s\S]*stopAnimation\(\)[\s\S]*clearStudentState\(\)[\s\S]*await\s+loadStudents\(\)/,
  '切换班级必须先停止旧动画并清空结果，再加载学生',
)
assert.match(
  picker,
  /onBeforeUnmount\(\(\)\s*=>\s*\{[\s\S]*studentRequestId\+\+[\s\S]*stopAnimation\(\)/,
  '组件卸载必须使旧请求失效并停止动画',
)

console.log('teacher-random-picker-static: ok')

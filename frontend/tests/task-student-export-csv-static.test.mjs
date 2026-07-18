import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const detail = read('src/views/teacher/TeacherTaskDetail.vue')
const report = read('src/views/teacher/TeacherTaskReportDetail.vue')

for (const [name, source] of [
  ['TeacherTaskDetail.vue', detail],
  ['TeacherTaskReportDetail.vue', report],
]) {
  assert.match(
    source,
    /function formatStudentIdForCsv\(id: string \| number\): string/,
    `${name} 应提供学号 CSV 文本格式化函数。`,
  )
  assert.match(
    source,
    /return `="\$\{text\}"`/,
    `${name} 应以 Excel 文本公式导出学号，避免被当成数值。`,
  )
  assert.match(
    source,
    /formatStudentIdForCsv\(s\.id\)/,
    `${name} 导出时应对学号调用文本格式化。`,
  )
  assert.doesNotMatch(
    source,
    /"\$\{s\.id\}"/,
    `${name} 不应再直接把学号作为普通引号字段导出。`,
  )
}

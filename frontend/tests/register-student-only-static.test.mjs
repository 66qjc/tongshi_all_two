import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const registerView = readFileSync(resolve(root, 'src/views/RegisterView.vue'), 'utf8')

assert.doesNotMatch(registerView, /value=["']teacher["']/, '公开注册页不能保留教师注册选项')
assert.doesNotMatch(registerView, /form\.role\s*===\s*['"]teacher['"]/, '公开注册页不能根据教师角色跳转')
assert.match(registerView, /role:\s*['"]student['"]\s+as\s+const/, '公开注册页默认角色应固定为 student')
assert.match(
  registerView,
  /authStore\.register\(\s*form\.id\.trim\(\),\s*form\.name\.trim\(\),\s*form\.password,\s*['"]student['"],\s*form\.major,?\s*\)/,
  '公开注册提交时应固定提交 student 角色',
)

console.log('register student only static checks passed')

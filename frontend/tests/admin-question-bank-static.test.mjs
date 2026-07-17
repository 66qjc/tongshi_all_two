import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const api = fs.readFileSync(path.join(root, 'src/api/adminQuestionBank.ts'), 'utf8')
const page = fs.readFileSync(path.join(root, 'src/views/admin/AdminQuestionBank.vue'), 'utf8')
const layout = fs.readFileSync(path.join(root, 'src/views/admin/AdminLayout.vue'), 'utf8')
const router = fs.readFileSync(path.join(root, 'src/router/index.ts'), 'utf8')

assert.match(api, /\/admin\/question-bank/, '独立题库 API 应指向 /admin/question-bank')
assert.match(api, /batchDeleteAdminQuestionBank/, '应提供批量删除')
assert.match(page, /共享题库/, '独立题库页面应有中文标题')
assert.match(page, /移入回收站/, '删除文案应为回收站语义')
assert.match(page, /原始挂载公共课/, '新增应支持可选挂载公共课')
assert.match(layout, /question-bank/, '管理端导航应包含共享题库')
assert.match(router, /path: 'question-bank'/, '路由应注册 /admin/question-bank')

console.log('admin-question-bank-static.test.mjs passed')

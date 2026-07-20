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
assert.match(page, /以标签、题型、星级组织/, '页面应强调标签维度而非课程挂载')
assert.doesNotMatch(page, /原始挂载公共课/, '新增表单不应再强调挂载公共课')
assert.doesNotMatch(page, /label="原挂载课程"/, '列表应去掉原挂载课程列')
assert.match(page, /\(page\s*-\s*1\)\s*\*\s*pageSize/, '序号应跨页连续')
assert.match(page, /label="标签"/, '列表应展示标签列，与教师端对齐')
assert.match(page, /v-for="tag in row\.tags/, '标签列应渲染题目 tags')
assert.match(page, /选择或输入标签/, '筛选区标签应支持选择或输入')
assert.match(page, /题型、标签、题干、答案必填，课程名称可选/, '管理员导入说明应明确必填字段与课程名称可选')
assert.match(api, /getQuestionBankTags|getAdminQuestionBankTags/, '管理员题库 API 应提供标签聚合方法')
assert.match(api, /\/admin\/question-bank\/tags/, '管理员标签接口应指向 /admin/question-bank/tags')
assert.match(page, /tagOptions/, '管理员题库页应使用 tagOptions')
assert.match(page, /选择已有标签，或输入后回车创建/, '新增/编辑标签占位应提示可选已有或手输')
assert.match(page, /v-for="tag in tagOptions"/, '标签下拉应渲染 tagOptions')
assert.match(page, /allow-create/, '标签选择应保留 allow-create 手输能力')
assert.match(page, /loadTagOptions/, '页面应加载已有标签选项')
assert.match(layout, /question-bank/, '管理端导航应包含共享题库')
assert.match(router, /path: 'question-bank'/, '路由应注册 /admin/question-bank')

console.log('admin-question-bank-static.test.mjs passed')

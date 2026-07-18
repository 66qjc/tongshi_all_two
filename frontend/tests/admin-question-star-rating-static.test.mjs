import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const api = readFileSync(resolve(root, 'src/api/adminQuestionBank.ts'), 'utf8')
const page = readFileSync(resolve(root, 'src/views/admin/AdminQuestionBank.vue'), 'utf8')
const legacyApi = readFileSync(resolve(root, 'src/api/adminPublicCourse.ts'), 'utf8')

assert.match(api, /star_rating:\s*number/, '独立题库请求类型应声明 star_rating')
assert.match(legacyApi, /star_rating:\s*number/, '兼容旧公共课题库请求类型仍应声明 star_rating')
assert.match(page, /label="星级"/, '独立题库列表应显示星级')
assert.match(page, /v-model="form\.star_rating"/, '独立题库题目表单应绑定星级')
assert.match(page, /<el-rate[\s\S]*:max="5"/, '独立题库题目表单应使用 5 星评分控件')
assert.match(page, /:model-value="Number\(row\.star_rating\) \|\| 3"/, '列表应用星标展示星级并默认 3')
assert.doesNotMatch(page, /prop="id"\s+label="ID"/, '列表不应再暴露数据库 ID 列')
assert.doesNotMatch(page, /label="原挂载课程"/, '列表应去掉原挂载课程列')
assert.match(page, /选择题/, '题型应中文展示')
assert.match(page, /\(page\s*-\s*1\)\s*\*\s*pageSize/, '序号应跨页连续计算')

console.log('admin-question-star-rating-static.test.mjs passed')

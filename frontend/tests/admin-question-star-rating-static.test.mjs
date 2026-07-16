import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const api = readFileSync(resolve(root, 'src/api/adminPublicCourse.ts'), 'utf8')
const page = readFileSync(resolve(root, 'src/views/admin/AdminPublicCourses.vue'), 'utf8')

assert.match(api, /star_rating:\s*number/, '管理员题目请求类型应声明 star_rating')
assert.match(page, /label="星级"/, '管理员题库列表应显示星级列')
assert.match(page, /v-model="questionForm\.star_rating"/, '管理员题目表单应绑定星级')
assert.match(page, /<el-rate[\s\S]*:max="5"/, '管理员题目表单应使用 5 星评分控件')

console.log('admin-question-star-rating-static.test.mjs passed')

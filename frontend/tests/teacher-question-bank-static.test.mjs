import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const api = read('src/api/question.ts')
const page = read('src/views/teacher/TeacherQuestions.vue')

assert.match(api, /creator_name\?:\s*string\s*\|\s*null/, 'Question 类型应包含 creator_name')
assert.match(api, /star_rating:\s*number/, 'Question 类型应包含 star_rating')
assert.match(api, /is_owner\?:\s*boolean/, 'Question 类型应包含 is_owner')
assert.match(api, /题目创建人是否为当前教师/, 'is_owner 注释应表示题目创建人归属')

assert.match(page, /label="添加人"/, '题库列表应显示添加人列')
assert.match(page, /label="星级"/, '题库列表应显示星级列')
assert.match(page, /<el-rate[\s\S]*:max="5"/, '编辑表单应使用最大 5 星的 el-rate')
assert.match(page, /v-model="form\.star_rating"/, '编辑表单应绑定 form.star_rating')
assert.match(page, /:disabled="row\.is_owner === false"/, '编辑按钮禁用条件应使用 is_owner === false')
assert.doesNotMatch(page, /row\.is_synced \? '公共' : '私有'/, '全站共享题库不应再显示公共/私有标签')

console.log('teacher-question-bank-static.test.mjs passed')

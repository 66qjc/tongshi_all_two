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
const layout = read('src/views/teacher/TeacherLayout.vue')

assert.match(api, /creator_name\?:\s*string\s*\|\s*null/, 'Question 类型应包含 creator_name')
assert.match(api, /star_rating:\s*number/, 'Question 类型应包含 star_rating')
assert.match(api, /is_owner\?:\s*boolean/, 'Question 类型应包含 is_owner')
assert.match(api, /题目创建人是否为当前教师/, 'is_owner 注释应表示题目创建人归属')

assert.match(page, /共享题库/, '教师端页标题或文案应使用共享题库')
assert.match(layout, /name: '共享题库'/, '教师端菜单应命名为共享题库')
assert.doesNotMatch(page, /label="所属课程"/, '共享题库列表不应再展示所属课程列')
assert.doesNotMatch(page, /请选择所属课程/, '新增不应强制选择所属课程')
assert.match(page, /选择题/, '题型应中文展示')
assert.match(page, /label="添加人"/, '题库列表应显示添加人列')
assert.match(page, /label="星级"/, '题库列表应显示星级列')
assert.match(page, /<el-rate[\s\S]*disabled[\s\S]*:max="5"/, '列表星级应使用只读 el-rate')
assert.match(page, /v-model="form\.star_rating"/, '编辑表单应绑定 form.star_rating')
assert.match(page, /<el-rate[\s\S]*:max="5"/, '编辑表单应使用最大 5 星的 el-rate')
assert.match(page, /\(page\s*-\s*1\)\s*\*\s*pageSize/, '序号应跨页连续计算')
assert.match(page, /:disabled="row\.is_owner === false"/, '编辑按钮禁用条件应使用 is_owner === false')
assert.doesNotMatch(page, /row\.is_synced \? '公共' : '私有'/, '全站共享题库不应再显示公共/私有标签')
assert.match(page, /题型（必填）/, '教师导入说明应明确题型必填')
assert.match(page, /标签（必填）/, '教师导入说明应明确标签必填')
assert.match(page, /题干（必填）/, '教师导入说明应明确题干必填')
assert.match(page, /答案（必填）/, '教师导入说明应明确答案必填')
assert.match(page, /课程名称（可选）/, '教师导入说明应明确课程名称可选')
assert.match(api, /getQuestionTags/, '教师题库 API 应提供 getQuestionTags')
assert.match(api, /\/questions\/tags/, '教师标签接口应指向 /questions/tags')
assert.match(page, /tagOptions/, '教师题库页应使用 tagOptions 作为已有标签选项')
assert.match(page, /选择已有标签，或输入后回车创建/, '新增/编辑标签占位应提示可选已有或手输')
assert.match(page, /选择或输入标签/, '列表标签筛选占位应提示可选或手输')
assert.match(page, /v-for="tag in tagOptions"/, '标签下拉应渲染 tagOptions')
assert.match(page, /allow-create/, '标签选择应保留 allow-create 手输能力')
assert.match(page, /loadTagOptions/, '页面应加载已有标签选项')

console.log('teacher-question-bank-static.test.mjs passed')

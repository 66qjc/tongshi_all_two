import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = (relativePath) => readFileSync(resolve(root, relativePath), 'utf8')

const adminApi = read('src/api/admin.ts')
const recycleBin = read('src/views/admin/AdminRecycleBin.vue')

// API 契约：ID 兼容字符串，仅列表/恢复，不暴露 purge
assert.match(
  adminApi,
  /export interface DeletedResourceItem[\s\S]*id:\s*number\s*\|\s*string/,
  '回收站资源 ID 类型应为 string | number',
)
assert.match(adminApi, /export function getDeletedResources/, '应提供回收站列表 API')
assert.match(adminApi, /export function restoreDeletedResource/, '应提供回收站恢复 API')
assert.match(
  adminApi,
  /encodeURIComponent\(String\(id\)\)/,
  '恢复 URL 应对资源 ID 做 encodeURIComponent(String(id))',
)
assert.doesNotMatch(adminApi, /export function purgeDeletedResource/, '前端 API 不应再导出 purge')
assert.doesNotMatch(adminApi, /\/admin\/purge\//, '前端 API 不应请求 /admin/purge/')

// 页面契约：中文资源类型、删除时间、保留截止、恢复按钮；无彻底删除
for (const label of ['用户', '课程', '班级', '作业', '作品', '资料', '题目']) {
  assert.match(recycleBin, new RegExp(label), `回收站应展示中文资源类型「${label}」`)
}
assert.match(recycleBin, /删除时间/, '回收站应展示删除时间')
assert.match(recycleBin, /保留截止/, '回收站应展示保留截止时间')
assert.match(recycleBin, />\s*恢复\s*</, '回收站应提供恢复按钮')
assert.match(recycleBin, /restoreDeletedResource/, '回收站应调用恢复 API')
assert.match(recycleBin, /getDeletedResources/, '回收站应调用列表 API')
assert.match(recycleBin, /openAuditHistory/, '回收站应保留操作历史入口')
assert.doesNotMatch(recycleBin, /purgeDeletedResource/, '回收站页面不应调用 purge API')
assert.doesNotMatch(recycleBin, /彻底删除/, '回收站页面不应出现“彻底删除”按钮或文案')
assert.doesNotMatch(recycleBin, /提前清理/, '回收站页面不应出现提前清理确认')
assert.doesNotMatch(recycleBin, /handlePurge/, '回收站页面不应保留彻底删除处理函数')
assert.doesNotMatch(recycleBin, /\/admin\/purge\//, '回收站源码不应包含 purge 请求路径')

// 不添加教师恢复入口：该页面仍是管理员路由下的组件
assert.match(recycleBin, /数据回收站/, '页面标题应为数据回收站')

console.log('管理员回收站软删除静态检查通过')

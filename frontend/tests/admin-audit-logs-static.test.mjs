import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import assert from 'node:assert/strict'

const root = resolve(import.meta.dirname, '..')
const read = path => readFileSync(resolve(root, path), 'utf8')

const adminApi = read('src/api/admin.ts')
assert.match(adminApi, /resource_id\?: string/, '\u5ba1\u8ba1\u65e5\u5fd7 API \u53c2\u6570\u5e94\u652f\u6301\u5b57\u7b26\u4e32\u8d44\u6e90 ID')
assert.match(adminApi, /status\?: string/, '\u5ba1\u8ba1\u65e5\u5fd7 API \u53c2\u6570\u5e94\u652f\u6301\u72b6\u6001\u7b5b\u9009')
assert.match(adminApi, /downloadAuditLogs\(params\?: AuditLogQueryParams\)/, '\u5ba1\u8ba1\u65e5\u5fd7\u5bfc\u51fa\u5e94\u652f\u6301\u4f20\u5165\u5f53\u524d\u7b5b\u9009\u6761\u4ef6')
assert.match(adminApi, /URLSearchParams/, '\u5ba1\u8ba1\u65e5\u5fd7\u5bfc\u51fa\u5e94\u5c06\u7b5b\u9009\u6761\u4ef6\u62fc\u63a5\u5230\u5bfc\u51fa URL')

const page = read('src/views/admin/AdminAuditLogs.vue')
assert.match(page, /resource_id: ''/, '\u5ba1\u8ba1\u65e5\u5fd7\u9875\u9762\u5e94\u63d0\u4f9b\u8d44\u6e90 ID \u7b5b\u9009')
assert.match(page, /status: ''/, '\u5ba1\u8ba1\u65e5\u5fd7\u9875\u9762\u5e94\u63d0\u4f9b\u72b6\u6001\u7b5b\u9009')
assert.match(page, /date_range/, '\u5ba1\u8ba1\u65e5\u5fd7\u9875\u9762\u5e94\u63d0\u4f9b\u65e5\u671f\u8303\u56f4\u7b5b\u9009')
assert.match(page, /downloadAuditLogs\(buildQuery\(\)\)/, '\u5ba1\u8ba1\u65e5\u5fd7\u9875\u9762\u5bfc\u51fa\u5e94\u4f7f\u7528\u5f53\u524d\u7b5b\u9009\u6761\u4ef6')
assert.match(page, /hydrateFiltersFromRoute/, '\u5ba1\u8ba1\u65e5\u5fd7\u9875\u5e94\u652f\u6301\u901a\u8fc7 URL \u67e5\u770b\u8d44\u6e90\u64cd\u4f5c\u5386\u53f2')
assert.match(page, /\u652f\u6301\u6570\u5b57ID\u6216\u5b66\u53f7/u, '\u8d44\u6e90 ID \u7b5b\u9009\u63d0\u793a\u5e94\u8bf4\u660e\u652f\u6301\u5b57\u7b26\u4e32\u8d44\u6e90 ID')
assert.match(page, /\u9519\u8bef\u4fe1\u606f/u, '\u5ba1\u8ba1\u65e5\u5fd7\u8868\u683c\u5e94\u5c55\u793a\u5931\u8d25\u9519\u8bef\u4fe1\u606f')
assert.doesNotMatch(page, /[\u7487\u5b6b\u7a0b\u9286\u9359\u9435]|\?\?\?/, '\u5ba1\u8ba1\u65e5\u5fd7\u9875\u9762\u4e0d\u80fd\u5305\u542b\u4e71\u7801\u6587\u6848')

const recycleBin = read('src/views/admin/AdminRecycleBin.vue')
assert.match(recycleBin, /openAuditHistory/, '\u56de\u6536\u7ad9\u5e94\u63d0\u4f9b\u8d44\u6e90\u64cd\u4f5c\u5386\u53f2\u5165\u53e3')
assert.match(recycleBin, /resource_type:\s*resourceType\.value/, '\u8d44\u6e90\u64cd\u4f5c\u5386\u53f2\u5165\u53e3\u5e94\u4f20\u9012\u5f53\u524d\u8d44\u6e90\u7c7b\u578b')

console.log('\u7ba1\u7406\u5458\u5ba1\u8ba1\u65e5\u5fd7\u9759\u6001\u68c0\u67e5\u901a\u8fc7')

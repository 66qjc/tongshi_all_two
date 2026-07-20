/**
 * fetchWithAuth 统一错误识别静态断言测试。
 * 验证 http.ts 中 fetchWithAuth 的关键实现模式。
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import assert from 'node:assert/strict'

const __dirname = dirname(fileURLToPath(import.meta.url))
const httpPath = resolve(__dirname, '../src/api/http.ts')
const source = readFileSync(httpPath, 'utf8')

function test(name, fn) {
  try {
    fn()
    console.log(`✓ ${name}`)
  } catch (error) {
    console.error(`✗ ${name}`)
    throw error
  }
}

test('fetchWithAuth 导出存在', () => {
  assert.match(
    source,
    /export\s+async\s+function\s+fetchWithAuth/,
    'http.ts 应导出 fetchWithAuth 函数',
  )
})

test('fetchWithAuth 附加 Authorization 头', () => {
  assert.match(
    source,
    /headers\['Authorization'\]\s*=\s*`Bearer \$\{token\}`/,
    'fetchWithAuth 应从 localStorage 读取 token 并附加到请求头',
  )
})

test('HTTP 401 清除登录态并跳转', () => {
  assert.match(
    source,
    /if\s*\(\s*response\.status\s*===\s*401\s*\)\s*\{[\s\S]*?clearAuthAndRedirect\(\)/,
    'HTTP 401 应调用 clearAuthAndRedirect 清除登录态',
  )
})

test('使用 response.clone() 探测 JSON 避免消费文件流', () => {
  assert.match(
    source,
    /const\s+cloned\s*=\s*response\.clone\(\)/,
    '应使用 response.clone() 探测 JSON，不消费原始 body',
  )
  assert.match(
    source,
    /const\s+payload\s*=\s*await\s+cloned\.json\(\)/,
    '应从 clone 解析 JSON',
  )
})

test('业务 JSON code=401 也触发登录态清除', () => {
  assert.match(
    source,
    /if\s*\(\s*payload\?\.code\s*===\s*401\s*\)\s*\{[\s\S]*?clearAuthAndRedirect\(\)/,
    '业务 JSON code===401 应同样清除登录态',
  )
})

test('业务 JSON code 非 0 抛出错误', () => {
  assert.match(
    source,
    /if\s*\(\s*payload\?\.code\s*!==\s*undefined\s*&&\s*payload\.code\s*!==\s*0\s*\)\s*\{[\s\S]*?throw\s+new\s+Error\(payload\.message/,
    '业务 code 非 0 应抛出含 message 的错误',
  )
})

test('clearAuthAndRedirect 辅助函数存在', () => {
  assert.match(
    source,
    /function\s+clearAuthAndRedirect\(\)\s*\{[\s\S]*?localStorage\.removeItem\('auth_user'\)[\s\S]*?localStorage\.removeItem\('auth_token'\)[\s\S]*?window\.location\.href\s*=\s*'\/login'/,
    'clearAuthAndRedirect 应清除 auth_user、auth_token 并跳转 /login',
  )
})

// ─── 验证 API 文件使用 fetchWithAuth ───

const questionApi = readFileSync(resolve(__dirname, '../src/api/question.ts'), 'utf8')
const adminQuestionBankApi = readFileSync(resolve(__dirname, '../src/api/adminQuestionBank.ts'), 'utf8')
const teacherApi = readFileSync(resolve(__dirname, '../src/api/teacher.ts'), 'utf8')
const adminApi = readFileSync(resolve(__dirname, '../src/api/admin.ts'), 'utf8')

test('question.ts 导入并使用 fetchWithAuth', () => {
  assert.match(questionApi, /import.*fetchWithAuth.*from.*['"]\.\/http['"]/, 'question.ts 应导入 fetchWithAuth')
  assert.match(questionApi, /fetchWithAuth\(/, 'question.ts 应使用 fetchWithAuth')
})

test('adminQuestionBank.ts 导入并使用 fetchWithAuth', () => {
  assert.match(adminQuestionBankApi, /import.*fetchWithAuth.*from.*['"]\.\/http['"]/, 'adminQuestionBank.ts 应导入 fetchWithAuth')
  assert.match(adminQuestionBankApi, /fetchWithAuth\(/, 'adminQuestionBank.ts 应使用 fetchWithAuth')
})

test('teacher.ts 导入并使用 fetchWithAuth', () => {
  assert.match(teacherApi, /import.*fetchWithAuth.*from.*['"]\.\/http['"]/, 'teacher.ts 应导入 fetchWithAuth')
  assert.match(teacherApi, /fetchWithAuth\(/, 'teacher.ts 应使用 fetchWithAuth')
})

test('admin.ts 导入并使用 fetchWithAuth', () => {
  assert.match(adminApi, /import.*fetchWithAuth.*from.*['"]\.\/http['"]/, 'admin.ts 应导入 fetchWithAuth')
  assert.match(adminApi, /fetchWithAuth\(/, 'admin.ts 应使用 fetchWithAuth')
})

console.log('fetch-auth-static.test.mjs passed')

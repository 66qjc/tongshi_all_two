import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const authStore = readFileSync(resolve(root, 'src/stores/auth.ts'), 'utf8')

assert.match(
  authStore,
  /function\s+parseStoredUser\(/,
  'auth.ts 需要集中安全解析 auth_user，避免畸形 localStorage 数据导致页面启动崩溃',
)

assert.doesNotMatch(
  authStore,
  /storedUser\s*\?\s*JSON\.parse\(storedUser\)/,
  'auth.ts 初始化登录态时不能直接 JSON.parse(storedUser)',
)

assert.match(
  authStore,
  /validRoles\.includes\(parsed\.role\)/,
  'auth.ts 需要校验 auth_user.role 只能是 student、teacher 或 admin',
)

assert.match(
  authStore,
  /localStorage\.removeItem\('auth_user'\)[\s\S]*localStorage\.removeItem\('auth_token'\)/,
  'auth.ts 发现无效本地登录态时需要同时清理 auth_user 和 auth_token',
)

console.log('auth-storage-static: ok')

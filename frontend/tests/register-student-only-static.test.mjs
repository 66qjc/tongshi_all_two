import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const router = read('src/router/index.ts')
const authApi = read('src/api/auth.ts')
const authStore = read('src/stores/auth.ts')
const loginView = read('src/views/LoginView.vue')

assert.equal(
  existsSync(resolve(root, 'src/views/RegisterView.vue')),
  false,
  '学生自助注册下线后不应保留 RegisterView.vue。',
)
assert.doesNotMatch(router, /path:\s*['"]\/register['"]/, '前端路由不应再暴露 /register。')
assert.doesNotMatch(authApi, /RegisterPayload|export function register|['"]\/register['"]/, '认证 API 不应保留注册契约。')
assert.doesNotMatch(authStore, /apiRegister|async function register|\bregister\s*[,}]/, '认证状态仓库不应保留注册动作。')
assert.doesNotMatch(loginView, /to=["']\/register["']|router\.push\(["']\/register["']\)|立即注册|注册账号/, '登录页不应保留自助注册链接。')

console.log('register removal static checks passed')
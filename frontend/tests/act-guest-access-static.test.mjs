import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const router = read('src/router/index.ts')
const actView = read('src/views/ActView.vue')

assert.match(
  router,
  /path:\s*['"]\/act['"][\s\S]*meta:\s*\{[^}]*public:\s*true/,
  '/act 应允许游客访问',
)

assert.match(
  router,
  /path:\s*['"]\/act\/showcase\/:id['"][\s\S]*meta:\s*\{[^}]*public:\s*true/,
  '/act/showcase/:id 应允许游客访问行动图文详情',
)

assert.ok(
  router.indexOf('isStudentBusinessPath(to.path)') < router.indexOf('if (to.meta.public) return true'),
  '教师访问学生端业务路径的拦截必须早于 public 路由放行',
)

assert.match(
  router,
  /isTokenExpired\(authStore\.token\)[\s\S]*authStore\.logout\(\)[\s\S]*if\s*\(\s*to\.meta\.public\s*\|\|\s*to\.path\s*===\s*['"]\/['"]\s*\)\s*return true[\s\S]*return ['"]\/login['"]/,
  '登录态过期后访问公开路由应清除登录态并按游客身份放行',
)

assert.match(
  actView,
  /import\s+\{\s*useAuthStore\s*\}\s+from\s+['"](?:@\/|\.\.\/)stores\/auth['"]/,
  'ActView 应读取现有认证状态',
)

assert.match(
  actView,
  /const\s+authStore\s*=\s*useAuthStore\(\)/,
  'ActView 应创建 authStore',
)

assert.match(
  actView,
  /if\s*\(\s*authStore\.isLoggedIn\s*\)\s*\{[\s\S]*getProjects\(\)[\s\S]*studentProjects\.value\s*=/,
  'ActView 只有登录后才应调用 getProjects 并写入作品列表',
)

assert.doesNotMatch(
  actView,
  /Promise\.all\(\s*\[\s*getShowcase\(\)\s*,\s*getProjects\(\)\s*\]/,
  '游客访问 /act 时不应通过 Promise.all 同时触发作品接口',
)

assert.match(
  actView,
  /登录后可查看同学作品/,
  '游客项目区应展示登录后查看同学作品的中文提示',
)

assert.match(
  actView,
  /router\.push\(['"]\/login['"]\)/,
  '游客项目区应提供去登录按钮',
)

console.log('act guest access static checks passed')

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = (path) => readFileSync(resolve(root, path), 'utf8')

const authApi = read('src/api/auth.ts')
const adminApi = read('src/api/admin.ts')
const authStore = read('src/stores/auth.ts')
const changePasswordView = read('src/views/ChangePasswordView.vue')
const loginView = read('src/views/LoginView.vue')
const profileView = read('src/views/ProfileView.vue')

assert.match(
  authApi,
  /changePassword[\s\S]*http\.put<any,\s*\{\s*message:\s*string;\s*access_token:\s*string\s*\}>\('\/change-password'/,
  'auth API 的改密响应类型必须包含 access_token',
)

assert.match(
  adminApi,
  /changePassword[\s\S]*http\.put<any,\s*\{\s*message:\s*string;\s*access_token:\s*string\s*\}>\('\/change-password'/,
  'admin API 的改密响应类型必须包含 access_token',
)

assert.match(
  authStore,
  /function\s+replaceAccessToken\(accessToken:\s*string\)[\s\S]*token\.value\s*=\s*accessToken[\s\S]*localStorage\.setItem\('auth_token',\s*accessToken\)/,
  'auth store 必须集中替换内存和 localStorage 中的 Token',
)

assert.match(
  authStore,
  /const\s+result\s*=\s*await\s+apiChangePassword[\s\S]*replaceAccessToken\(result\.access_token\)[\s\S]*needs_password_change\s*=\s*false/,
  'store 改密成功后必须先保存新 Token，再清除强制改密标记',
)

assert.doesNotMatch(
  changePasswordView,
  /import\s*\{\s*changePassword\s*\}\s*from\s*['"]\.\.\/api\/admin['"]/,
  '独立改密页不能绕过 auth store 直接调用 admin API',
)

assert.match(
  changePasswordView,
  /await\s+authStore\.changePassword\(\s*form\.value\.old_password,\s*form\.value\.new_password,?\s*\)[\s\S]*showSecurityDialog\.value\s*=\s*true/,
  '独立改密页必须先通过 store 保存新 Token，再打开密保设置',
)

assert.match(
  loginView,
  /await\s+authStore\.changePassword\(changeForm\.oldPassword,\s*changeForm\.newPassword\)/,
  '登录页首次改密必须通过 auth store',
)

assert.match(
  profileView,
  /await\s+authStore\.changePassword\(pwdForm\.value\.oldPassword,\s*pwdForm\.value\.newPassword\)/,
  '个人中心改密必须通过 auth store',
)

console.log('password-rotation-static: ok')

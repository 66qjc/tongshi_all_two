import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const siteIcon = '/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png'

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const filesUsingSiteIcon = [
  'src/views/teacher/TeacherLayout.vue',
  'src/views/admin/AdminLayout.vue',
  'src/views/LoginView.vue',
  'src/views/RegisterView.vue',
  'src/views/PracticeView.vue',
  'src/views/PracticeAssignments.vue',
  'src/views/AboutView.vue',
]

for (const file of filesUsingSiteIcon) {
  assert.match(read(file), new RegExp(siteIcon), `${file} 应使用统一的网站图标资源。`)
}

const legacySingleTextIcons = [
  ['src/views/teacher/TeacherLayout.vue', /<text\b[\s\S]*?>师<\/text>/],
  ['src/views/admin/AdminLayout.vue', /<text\b[\s\S]*?>管<\/text>/],
  ['src/views/LoginView.vue', /<text\b[\s\S]*?>探<\/text>/],
  ['src/views/RegisterView.vue', /<text\b[\s\S]*?>探<\/text>/],
]

for (const [file, pattern] of legacySingleTextIcons) {
  assert.doesNotMatch(read(file), pattern, `${file} 不应继续使用 SVG 单字图标。`)
}

const legacyPageIcons = [
  ['src/views/LearnView.vue', /<div class="hero-icon">\s*学\s*<\/div>/],
  ['src/views/PracticeView.vue', /<div class="hero-icon">\s*思\s*<\/div>/],
  ['src/views/PracticeAssignments.vue', /<div class="hero-icon">\s*思\s*<\/div>/],
  ['src/views/AboutView.vue', /<div class="phil-icon"[^>]*>\s*[探练造行]\s*<\/div>/],
]

for (const [file, pattern] of legacyPageIcons) {
  assert.doesNotMatch(read(file), pattern, `${file} 不应继续使用普通页面单字图标。`)
}

const highContrastIconFrames = [
  ['src/components/AppFooter.vue', /class="footer-logo-mark"[\s\S]*?<img[\s\S]*?class="footer-logo-icon"/],
  ['src/views/LoginView.vue', /class="brand-logo brand-logo-mark"[\s\S]*?<img[\s\S]*?class="brand-logo-image"/],
  ['src/views/RegisterView.vue', /class="brand-logo brand-logo-mark"[\s\S]*?<img[\s\S]*?class="brand-logo-image"/],
]

for (const [file, pattern] of highContrastIconFrames) {
  assert.match(read(file), pattern, `${file} 深色背景中的网站图标应有高对比底托。`)
}

const highContrastFrameStyles = [
  ['src/components/AppFooter.vue', /\.footer-logo-mark\s*\{[\s\S]*?background:\s*rgba\(255,\s*253,\s*248,\s*0\.9/],
  ['src/views/LoginView.vue', /\.brand-logo-mark\s*\{[\s\S]*?background:\s*rgba\(255,\s*253,\s*248,\s*0\.92/],
  ['src/views/RegisterView.vue', /\.brand-logo-mark\s*\{[\s\S]*?background:\s*rgba\(255,\s*253,\s*248,\s*0\.92/],
]

for (const [file, pattern] of highContrastFrameStyles) {
  assert.match(read(file), pattern, `${file} 高对比底托应使用浅色承托背景。`)
}

const legacyFaviconFiles = ['public/favicon.svg', 'public/favicon.ico']

for (const file of legacyFaviconFiles) {
  assert.equal(existsSync(resolve(root, file)), false, `${file} 旧图标文件应删除。`)
}

console.log('site icon replacement static checks passed')

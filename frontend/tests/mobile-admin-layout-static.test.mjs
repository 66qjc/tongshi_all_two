import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function assertContains(file, pattern, message) {
  assert.match(read(file), pattern, message)
}

assertContains(
  'src/views/PortfolioView.vue',
  /axisLabel:\s*\{\s*show:\s*false\s*\}/,
  '成长档案雷达图应隐藏雷达轴刻度标签，避免 ECharts 在 0-100 固定范围下输出可读性警告',
)

assertContains(
  'src/views/admin/AdminLayout.vue',
  /@media\s*\(max-width:\s*480px\)[\s\S]*\.admin-sidebar\s*\{[\s\S]*width:\s*48px[\s\S]*\.admin-main\s*\{[\s\S]*min-width:\s*0/,
  '管理员端窄屏布局应在 480px 下进一步收窄侧栏，并允许主内容按视口收缩',
)

assertContains(
  'src/views/teacher/TeacherLayout.vue',
  /@media\s*\(max-width:\s*480px\)[\s\S]*\.teacher-sidebar\s*\{[\s\S]*width:\s*48px/,
  '教师端窄屏布局应在 480px 下进一步收窄侧栏，给内容区留出可用宽度',
)

assertContains(
  'src/views/teacher/TeacherMaterials.vue',
  /@media\s*\(max-width:\s*640px\)[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/,
  '教师资料管理移动端资料卡片不能保留 360px 最小宽度',
)

assertContains(
  'src/views/admin/AdminPublicCourses.vue',
  /@media\s*\(max-width:\s*640px\)[\s\S]*\.content-panel\s*\{[\s\S]*overflow-x:\s*auto/,
  '管理员公共课程移动端应把宽表格限制在内容面板内部滚动，避免撑开页面',
)

assertContains(
  'src/views/admin/AdminShowcase.vue',
  /@media\s*\(max-width:\s*640px\)[\s\S]*\.item-card\s*\{[\s\S]*flex-direction:\s*column/,
  '管理员公众号内容管理移动端列表卡片应改为纵向布局，避免元信息列撑宽页面',
)

console.log('mobile-admin-layout-static: ok')

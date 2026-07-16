import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const homeView = read('src/views/HomeView.vue')
const hero = read('src/components/home/HeroSection.vue')
const modules = read('src/components/home/ModuleShowcase.vue')
const stats = read('src/components/home/StatsSection.vue')

assert.doesNotMatch(
  homeView,
  /CoursePreview/,
  '首页应先移除旧的六块课程预览，不再导入或渲染 CoursePreview。',
)

for (const route of ['/learn', '/practice', '/create', '/act']) {
  assert.match(
    hero,
    new RegExp(`route:\\s*'${route}'`),
    `首屏应提供 ${route} 的直接入口。`,
  )
}

assert.match(
  hero,
  /router\.push\(entry\.route\)/,
  '首屏入口应通过数据驱动的 entry.route 跳转。',
)

assert.match(
  hero,
  /entry-grid/,
  '首屏四个入口应使用 entry-grid 组织，便于学生快速选择下一步。',
)

assert.doesNotMatch(
  hero,
  /今日建议|suggestion-panel/,
  '首屏已去掉“今日建议”，避免额外行动建议块。',
)

assert.doesNotMatch(
  modules,
  /card-features/,
  '四模块卡片应精简，不再展示长列表功能点。',
)

assert.match(
  modules,
  /module-status/,
  '四模块卡片应展示更短的状态型提示。',
)

assert.match(
  modules,
  /module-actions/,
  '四模块卡片应补充短条目，说明学生可以具体做什么。',
)

assert.match(
  stats,
  /学习路径/,
  '统计区应说明学习路径，避免继续展示过期或静态宣传数字。',
)

assert.doesNotMatch(
  stats,
  /首页只保留稳定路径/,
  '上线文案不应再使用内部说明式标题。',
)

assert.match(
  stats,
  /建议学习顺序/,
  '学习路径区应包含建议学习顺序，增强内容密度。',
)

assert.match(
  stats,
  /flow-line/,
  '学习闭环区应提供横向流程结构。',
)

assert.doesNotMatch(
  stats,
  /setInterval/,
  '统计区不应再使用数字滚动动画。',
)

assert.match(
  hero,
  /@media \(max-width: 768px\)/,
  '首屏应保留移动端布局优化。',
)

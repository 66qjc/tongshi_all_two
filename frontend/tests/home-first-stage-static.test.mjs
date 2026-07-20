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
  '首页应保持移除旧的六块课程预览，不再导入或渲染 CoursePreview。',
)

for (const route of ['/learn', '/practice', '/create', '/act']) {
  assert.match(
    hero,
    new RegExp(`route:\\s*'${route}'`),
    `学习之环应提供 ${route} 的直接入口。`,
  )
}

assert.match(
  hero,
  /router\.push\(m\.route\)/,
  '学习之环节点应通过当前模块的 m.route 跳转。',
)
assert.match(
  hero,
  /<router-link class="p-go" :to="currentModule\.route">/,
  '学习之环信息板应提供当前模块的明确进入链接。',
)

for (const structure of ['hero-grid', 'hero-orbit', 'orbit-wrap', 'orbit-panel']) {
  assert.match(hero, new RegExp(structure), `学习之环首屏应保留 ${structure} 结构。`)
}

assert.match(hero, /v-for="\(m, i\) in modules"/, '学习之环节点应由四模块数据统一驱动。')
assert.match(hero, /@click="onNodeClick\(i\)"/, '学习之环节点应支持鼠标和触摸点击。')
assert.match(hero, /学习之环持续流转/, '首屏应说明学习之环的操作方式。')
assert.doesNotMatch(hero, /今日建议|suggestion-panel/, '首屏不应恢复额外的“今日建议”块。')

assert.doesNotMatch(modules, /card-features/, '四模块卡片应精简，不再展示长列表功能点。')
assert.match(modules, /module-status/, '四模块卡片应展示更短的状态型提示。')
assert.match(modules, /module-actions/, '四模块卡片应说明学生可以具体做什么。')
assert.match(stats, /学习路径/, '学习路径区不应退回过期或静态宣传数字。')
assert.doesNotMatch(stats, /首页只保留稳定路径/, '上线文案不应使用内部说明式标题。')
assert.match(stats, /建议学习顺序/, '学习路径区应包含建议学习顺序。')
assert.match(stats, /flow-line/, '学习闭环区应提供横向流程结构。')
assert.doesNotMatch(stats, /setInterval/, '学习路径区不应使用数字滚动动画。')
assert.match(hero, /@media \(max-width: 899px\)/, '学习之环首屏应保留移动端布局优化。')

console.log('home first stage static checks passed')
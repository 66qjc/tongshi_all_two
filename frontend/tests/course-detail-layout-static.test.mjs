import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function styleBlock(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\n\\s*\\}`, 'm'))
  assert.ok(match, `应找到 ${selector} 的样式块。`)
  return match[1]
}

function mediaBlock(source, query) {
  const start = source.indexOf(query)
  assert.notEqual(start, -1, `应找到 ${query} 媒体查询。`)
  const open = source.indexOf('{', start)
  let depth = 0
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) {
      return source.slice(open + 1, index)
    }
  }
  assert.fail(`未能解析 ${query} 媒体查询。`)
}

const courseDetail = read('src/views/CourseDetailView.vue')

assert.match(courseDetail, /class="booksite-layout"/, '课程阅读区应使用稳定的书站网格容器。')
assert.match(courseDetail, /class="reader-sidebar"/, '课程阅读区应包含目录侧栏。')
assert.match(courseDetail, /class="reader-main"/, '课程阅读区应包含主阅读内容。')

const pageStyle = styleBlock(courseDetail, '.course-detail-page')
assert.match(pageStyle, /--app-header-height:\s*60px;/, '课程详情页应统一声明固定顶栏高度。')
assert.match(pageStyle, /padding-top:\s*var\(--app-header-height\);/, '课程详情页应为固定顶栏预留顶部空间。')

const desktopLayout = styleBlock(courseDetail, '.booksite-layout')
assert.match(desktopLayout, /display:\s*grid;/, '桌面端课程阅读区应使用网格布局。')
assert.match(desktopLayout, /grid-template-columns:\s*260px\s+minmax\(0,\s*1fr\)\s+300px;/, '桌面端应稳定保留目录、正文和资料栏三列。')

assert.match(courseDetail, /\.reader-sidebar,\s*\.resource-rail\s*\{[\s\S]*?position:\s*sticky;/, '桌面端课程目录应参与布局并使用 sticky 固定。')

const desktopMainContent = styleBlock(courseDetail, '.reader-main')
assert.doesNotMatch(desktopMainContent, /margin-left:\s*260px;/, '主内容不应依赖固定 margin-left 避让脱流侧栏。')

const mobileStyles = mediaBlock(courseDetail, '@media (max-width: 900px)')
const mobileSidebar = styleBlock(mobileStyles, '.reader-sidebar')
assert.match(mobileSidebar, /position:\s*fixed;/, '移动端课程目录仍应作为抽屉 fixed 覆盖显示。')
assert.match(mobileSidebar, /transform:\s*translateX\(-100%\);/, '移动端课程目录默认应收起在屏幕外。')

console.log('course detail layout static checks passed')

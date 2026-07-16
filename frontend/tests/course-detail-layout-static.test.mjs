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

assert.match(courseDetail, /class="material-doc-shell"/, '课程阅读区应使用资料直读三栏外壳。')
assert.match(courseDetail, /class="material-doc-sidebar"/, '课程阅读区应包含左侧资料目录。')
assert.match(courseDetail, /class="material-doc-main"/, '课程阅读区应包含中间资料正文。')
assert.match(courseDetail, /class="material-doc-guide"/, '课程阅读区应包含右侧导读栏。')
assert.doesNotMatch(courseDetail, /booksite-layout|reader-sidebar|CourseToc|LessonReader/, '课程阅读区不得再使用课时书站布局。')

const pageStyle = styleBlock(courseDetail, '.course-detail-page')
assert.match(pageStyle, /--app-header-height:\s*60px;/, '课程详情页应统一声明固定顶栏高度。')
assert.match(pageStyle, /padding-top:\s*var\(--app-header-height\);/, '课程详情页应为固定顶栏预留顶部空间。')

const desktopLayout = styleBlock(courseDetail, '.material-doc-shell')
assert.match(desktopLayout, /display:\s*grid;/, '桌面端课程阅读区应使用网格布局。')
assert.match(desktopLayout, /grid-template-columns:\s*292px\s+minmax\(0,\s*1fr\)\s+280px;/, '桌面端应稳定保留目录、正文和导读三列。')

assert.match(
  courseDetail,
  /\.material-doc-sidebar,\s*\.material-doc-guide\s*\{[\s\S]*?position:\s*sticky;/,
  '桌面端资料目录与导读栏应使用 sticky 固定。',
)

const desktopMainContent = styleBlock(courseDetail, '.material-doc-main')
assert.doesNotMatch(desktopMainContent, /margin-left:\s*260px;/, '主内容不应依赖固定 margin-left 避让脱流侧栏。')

const mobileStyles = mediaBlock(courseDetail, '@media (max-width: 900px)')
const mobileShell = styleBlock(mobileStyles, '.material-doc-shell')
assert.match(mobileShell, /display:\s*block;/, '移动端资料阅读外壳应改为纵向堆叠。')

console.log('course detail layout static checks passed')

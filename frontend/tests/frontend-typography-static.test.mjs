import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function cssBlock(source, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\}`))
  return match?.[1] ?? ''
}

function firstCssBlock(source, selectors, file) {
  for (const selector of selectors) {
    const block = cssBlock(source, selector)
    if (block) return { selector, block }
  }
  throw new Error(`${file} 缺少预期的页面标题样式`)
}

function assertNoLegacyHeadingStyle(file, selectors, surfaceName) {
  const source = read(file)
  const { selector, block } = firstCssBlock(source, selectors, file)
  assert.doesNotMatch(
    block,
    /font-family:\s*var\(--font-serif\)/,
    `${surfaceName} ${file} 的 ${selector} 不应继续使用宋体标题`,
  )
  assert.doesNotMatch(
    block,
    /letter-spacing:\s*0\.05em/,
    `${surfaceName} ${file} 的 ${selector} 不应继续使用大字距`,
  )
}

function assertNoLegacyHeadingStyles(file, selectors, surfaceName) {
  for (const selector of selectors) {
    assertNoLegacyHeadingStyle(file, [selector], surfaceName)
  }
}

const mainCss = read('src/assets/main.css')

for (const token of [
  '--text-display-title:',
  '--text-page-title:',
  '--text-section-title:',
  '--text-card-title:',
  '--text-body:',
  '--text-muted:',
  '--text-caption:',
  '--leading-title:',
  '--leading-body:',
  '--leading-compact:',
]) {
  assert.match(mainCss, new RegExp(token), `全局 CSS 需要定义排版变量 ${token}`)
}

assert.match(mainCss, /text-wrap:\s*balance/, '全局 CSS 需要标题断行保护')
assert.match(mainCss, /text-wrap:\s*pretty/, '全局 CSS 需要正文断行保护')
assert.match(mainCss, /font-variant-numeric:\s*tabular-nums/, '全局 CSS 需要数字等宽排版工具')

const checkedUiFiles = ['src/views/InboxView.vue']

for (const file of checkedUiFiles) {
  const source = read(file)
  assert.doesNotMatch(
    source,
    /border-left:\s*[2-9]px/,
    `${file} 不应使用 2px 以上侧边色条作为卡片或标题装饰`,
  )
  assert.doesNotMatch(
    source,
    /color:\s*#fff\b/,
    `${file} 不应使用纯白文字色，应使用带轻微色相的白`,
  )
}

const studentTaskPages = [
  { file: 'src/views/PracticeView.vue', selectors: ['.hero-inner h1'] },
  { file: 'src/views/PracticeAssignments.vue', selectors: ['.hero-inner h1'] },
  { file: 'src/views/PracticeQuizView.vue', selectors: ['.quiz-info h2', '.summary-card h2'] },
  { file: 'src/views/CreateView.vue', selectors: ['.hero-inner h1'] },
  { file: 'src/views/PortfolioView.vue', selectors: ['.hero-inner h1'] },
  { file: 'src/views/ProjectDetailView.vue', selectors: ['.project-header h1'] },
  { file: 'src/views/ProjectUploadView.vue', selectors: ['.upload-card h1'] },
  { file: 'src/views/ProfileView.vue', selectors: ['.page-header h1'] },
  { file: 'src/views/InboxView.vue', selectors: ['.hero-inner h1'] },
]

for (const { file, selectors } of studentTaskPages) {
  assertNoLegacyHeadingStyle(file, selectors, '学生端')
}

for (const selector of ['.section-title', '.module-title']) {
  assertNoLegacyHeadingStyle(
    'src/components/home/CoursePreview.vue',
    [selector],
    'home retained component',
  )
}

const publicVisiblePages = [
  {
    file: 'src/views/ActView.vue',
    selectors: ['.hero-inner h1', '.section-header h2', '.outcome-title', '.detail-main h2'],
  },
  {
    file: 'src/views/ActDetailView.vue',
    selectors: ['.article-header h1', '.section-title span', '.more-section h2'],
  },
  {
    file: 'src/views/AboutView.vue',
    selectors: ['.hero-inner h1', '.about-block h2', '.phil-card h3', '.ch-top h3'],
  },
  {
    file: 'src/views/ContactView.vue',
    selectors: ['.hero-inner h1', '.contact-form-card h2', '.contact-info-card h2'],
  },
  {
    file: 'src/views/PrivacyView.vue',
    selectors: ['.hero-inner h1', '.content-block h2'],
  },
  {
    file: 'src/views/LoginView.vue',
    selectors: ['.brand-content h1', '.form-content h2'],
  },
  {
    file: 'src/views/RegisterView.vue',
    selectors: ['.brand-content h1', '.form-content h2'],
  },
  {
    file: 'src/views/ChangePasswordView.vue',
    selectors: ['.card-header'],
  },
  {
    file: 'src/views/NotFoundView.vue',
    selectors: ['.not-found-content h1'],
  },
]

for (const { file, selectors } of publicVisiblePages) {
  assertNoLegacyHeadingStyles(file, selectors, '公开可见页面')
}

for (const file of ['src/views/LearnView.vue', 'src/views/CourseDetailView.vue']) {
  const source = read(file)
  assert.match(source, /text-wrap:\s*pretty/, `${file} 的长说明文案需要正文断行保护`)
}

console.log('frontend-typography-static: ok')

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const hero = read('src/components/home/HeroSection.vue')
const header = read('src/components/AppHeader.vue')

assert.match(
  hero,
  /中国计量大学\s*·\s*AI 通识教育课程平台/,
  '首页首屏徽标应写明“中国计量大学 · AI 通识教育课程平台”。',
)

assert.match(
  hero,
  /hero-badge-mark/,
  '首页首屏徽标应带有校名相关的视觉标记。',
)

assert.match(
  header,
  /中国计量大学\s*·\s*AI 通识课平台/,
  '顶部品牌副标题应补充中国计量大学归属。',
)

assert.match(
  header,
  /中国计量大学 AI 通识课平台标识/,
  '顶部新图标应提供清晰的中文可访问名称。',
)

assert.doesNotMatch(
  header,
  />学<\/text>/,
  '顶部图标不应继续使用旧的单字“学”圆章。',
)

assert.match(
  header,
  /logo-emblem-book/,
  '顶部图标应换成与学校和课程语境相关的书本图形。',
)

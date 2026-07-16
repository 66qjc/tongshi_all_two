import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const detailView = readFileSync(resolve(root, 'src/views/ActDetailView.vue'), 'utf8')

assert.match(
  detailView,
  /handleBlockImageError/,
  '正文图片加载失败时应进入可恢复的中文占位状态。',
)
assert.match(
  detailView,
  /图片暂时无法加载/,
  '正文图片失败状态应显示用户可理解的中文提示。',
)

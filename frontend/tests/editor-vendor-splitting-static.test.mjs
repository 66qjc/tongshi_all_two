import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const viteConfig = readFileSync(resolve(root, 'vite.config.ts'), 'utf8')

assert.match(viteConfig, /name:\s*['"]vendor-wangeditor['"]/, 'wangEditor 应进入独立 vendor-wangeditor chunk')
assert.match(
  viteConfig,
  /test:\s*\/node_modules\[\\\\\/\]\(@wangeditor\)\[\\\\\/\]\//,
  'vendor-wangeditor 只应匹配 @wangeditor 依赖',
)
assert.match(viteConfig, /priority:\s*40/, 'vendor-wangeditor 应高于通用依赖分组优先级')

console.log('editor-vendor-splitting-static: 所有断言通过')

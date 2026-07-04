import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const viteConfig = readFileSync(resolve(root, 'vite.config.ts'), 'utf8')

assert.match(viteConfig, /rolldownOptions\s*:/, 'Vite 构建应显式配置 Rolldown 分包')
assert.match(viteConfig, /codeSplitting\s*:/, 'Rolldown 输出应使用 codeSplitting.groups')
assert.match(viteConfig, /name:\s*['"]vendor-vue['"]/, 'Vue 基础依赖应进入 vendor-vue chunk')
assert.match(viteConfig, /name:\s*['"]vendor-element-plus['"]/, 'Element Plus 应进入独立 vendor chunk')
assert.match(viteConfig, /name:\s*['"]vendor-http['"]/, 'HTTP 基础依赖应进入独立 vendor chunk')
assert.doesNotMatch(
  viteConfig,
  /test:\s*\/node_modules(?:\/|\s|$)/,
  '禁止使用宽泛 node_modules 总包，避免吞掉异步重依赖',
)

console.log('vendor-chunk-splitting-static: 所有断言通过')

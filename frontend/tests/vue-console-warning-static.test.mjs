import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, extname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const srcRoot = resolve(root, 'src')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function vueFiles(dir = srcRoot) {
  const files = []
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      files.push(...vueFiles(fullPath))
    } else if (extname(fullPath) === '.vue') {
      files.push(fullPath)
    }
  }
  return files
}

const app = read('src/App.vue')
assert.match(
  app,
  /<Transition[^>]*name="page-fade"[\s\S]*<div[^>]*class="page-transition-shell"/,
  'App.vue 的页面 Transition 需要包住单一真实 DOM 节点，避免多根路由组件触发 Vue warning',
)

const main = read('src/main.ts')
assert.match(
  main,
  /\bElCheckbox\b/,
  'main.ts 需要注册 ElCheckbox，确保通知中心的“只看未读”控件可渲染',
)
assert.match(
  main,
  /\bElSegmented\b/,
  'main.ts 需要注册 ElSegmented，确保通知中心的分类分段控件可渲染',
)
assert.match(
  main,
  /app\.component\('el-radio-group',\s*ElRadioGroup\)/,
  'main.ts 需要显式注册 el-radio-group 别名，避免局部页面无法解析单选组组件',
)
assert.match(
  main,
  /app\.component\('el-radio-button',\s*ElRadioButton\)/,
  'main.ts 需要显式注册 el-radio-button 别名，避免局部页面无法解析单选按钮组组件',
)

for (const file of vueFiles()) {
  const source = readFileSync(file, 'utf8')
  const label = relative(root, file).replaceAll('\\', '/')
  assert.doesNotMatch(
    source,
    /<el-option\b[^>]*:value="null"/,
    `${label} 不应给 el-option 传 null value，Element Plus 会输出 prop warning`,
  )
  assert.doesNotMatch(
    source,
    /value:\s*null/,
    `${label} 不应在 el-option 数据源里使用 null value，Element Plus 会输出 prop warning`,
  )
  assert.doesNotMatch(
    source,
    /<el-tag\b[^>]*:type="[^"]*\?\s*''/,
    `${label} 不应给 el-tag 传空字符串 type，Element Plus 会输出 prop warning`,
  )
}

console.log('vue-console-warning-static: ok')

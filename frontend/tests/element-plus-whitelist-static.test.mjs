import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const main = readFileSync(resolve(root, 'src/main.ts'), 'utf8')

const requiredComponents = [
  'ElAlert',
  'ElButton',
  'ElCard',
  'ElCollapse',
  'ElCollapseItem',
  'ElDatePicker',
  'ElDialog',
  'ElDrawer',
  'ElEmpty',
  'ElForm',
  'ElFormItem',
  'ElIcon',
  'ElInput',
  'ElInputNumber',
  'ElOption',
  'ElPagination',
  'ElPopconfirm',
  'ElProgress',
  'ElRadioButton',
  'ElRadioGroup',
  'ElSelect',
  'ElSkeleton',
  'ElSwitch',
  'ElTable',
  'ElTableColumn',
  'ElTabPane',
  'ElTabs',
  'ElTag',
  'ElUpload',
]

assert.doesNotMatch(
  main,
  /import\s+ElementPlus\s+from\s+['"]element-plus['"]/,
  '入口不能默认导入 ElementPlus 全量插件',
)
assert.doesNotMatch(main, /app\.use\(ElementPlus/, '入口不能安装 ElementPlus 全量插件')
assert.match(main, /provideGlobalConfig\s*,/, '入口应从 element-plus 导入 provideGlobalConfig')
assert.match(
  main,
  /provideGlobalConfig\(\{\s*locale:\s*zhCn\s*\},\s*app,\s*true\)/,
  '入口应保留 Element Plus 中文全局配置',
)
assert.match(main, /app\.use\(ElLoading\)/, '入口应保留 v-loading 指令和 $loading 服务')
assert.match(main, /const\s+elementPlusComponents\s*=\s*\[/, '入口应集中维护 Element Plus 组件白名单')

for (const componentName of requiredComponents) {
  assert.match(
    main,
    new RegExp(`\\b${componentName}\\b`),
    `入口应导入并注册 ${componentName}`,
  )
}

console.log('element-plus-whitelist-static: 所有断言通过')

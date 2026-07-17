import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const api = read('src/api/adminQuestionBank.ts')
const page = read('src/views/admin/AdminQuestionBank.vue')
const publicPage = read('src/views/admin/AdminPublicCourses.vue')

function skipStringOrComment(source, index) {
  const character = source[index]
  const nextCharacter = source[index + 1]

  if (character === "'" || character === '"' || character === '`') {
    for (let cursor = index + 1; cursor < source.length; cursor += 1) {
      if (source[cursor] === '\\') {
        cursor += 1
        continue
      }
      if (source[cursor] === character) return cursor + 1
    }
    assert.fail('静态测试解析到未闭合的字符串或模板字符串')
  }

  if (character === '/' && nextCharacter === '/') {
    const lineEnd = source.indexOf('\n', index + 2)
    return lineEnd === -1 ? source.length : lineEnd + 1
  }

  if (character === '/' && nextCharacter === '*') {
    const commentEnd = source.indexOf('*/', index + 2)
    assert.notEqual(commentEnd, -1, '静态测试解析到未闭合的块注释')
    return commentEnd + 2
  }

  return index
}

function findMatchingDelimiter(source, startIndex, opening, closing, description) {
  assert.equal(source[startIndex], opening, `${description} 应从 ${opening} 开始`)

  let depth = 0
  for (let index = startIndex; index < source.length;) {
    const skippedIndex = skipStringOrComment(source, index)
    if (skippedIndex !== index) {
      index = skippedIndex
      continue
    }

    if (source[index] === opening) depth += 1
    if (source[index] === closing) {
      depth -= 1
      if (depth === 0) return index
    }
    index += 1
  }

  assert.fail(`${description} 未闭合`)
}

function findCodeSequence(source, sequence, startIndex = 0) {
  for (let index = startIndex; index < source.length;) {
    const skippedIndex = skipStringOrComment(source, index)
    if (skippedIndex !== index) {
      index = skippedIndex
      continue
    }
    if (source.startsWith(sequence, index)) return index
    index += 1
  }
  return -1
}

function skipWhitespace(source, index) {
  while (index < source.length && /\s/.test(source[index])) index += 1
  return index
}

function extractAsyncFunctionBody(source, name) {
  const signature = `async function ${name}`
  const signatureIndex = findCodeSequence(source, signature)
  assert.notEqual(signatureIndex, -1, `页面应定义 ${name} 删除逻辑`)

  const parametersStart = skipWhitespace(source, signatureIndex + signature.length)
  assert.equal(source[parametersStart], '(', `${name} 删除逻辑应声明参数`)
  const parametersEnd = findMatchingDelimiter(source, parametersStart, '(', ')', `${name} 删除逻辑的参数列表`)

  const bodyStart = skipWhitespace(source, parametersEnd + 1)
  assert.equal(source[bodyStart], '{', `${name} 删除逻辑应包含函数体`)
  const bodyEnd = findMatchingDelimiter(source, bodyStart, '{', '}', `${name} 删除逻辑的函数体`)
  return source.slice(bodyStart + 1, bodyEnd)
}

function extractConfirmationBody(functionBody, functionName) {
  const callSignature = 'await ElMessageBox.confirm'
  const callIndex = findCodeSequence(functionBody, callSignature)
  assert.notEqual(callIndex, -1, `${functionName} 应等待删除确认框结果`)

  const callStart = skipWhitespace(functionBody, callIndex + callSignature.length)
  assert.equal(functionBody[callStart], '(', `${functionName} 的删除确认框应传入参数`)
  const callEnd = findMatchingDelimiter(functionBody, callStart, '(', ')', `${functionName} 的删除确认调用`)

  const bodyStart = skipWhitespace(functionBody, callStart + 1)
  assert.ok(["'", '"', '`'].includes(functionBody[bodyStart]), `${functionName} 的确认正文应使用文本字面量`)
  const bodyEnd = skipStringOrComment(functionBody, bodyStart)
  assert.ok(bodyEnd <= callEnd, `${functionName} 的确认正文应是 ElMessageBox.confirm 的首个参数`)
  return functionBody.slice(bodyStart, bodyEnd)
}

function assertQuestionDeleteConfirmation(functionName) {
  const functionBody = extractAsyncFunctionBody(page, functionName)
  const confirmationBody = extractConfirmationBody(functionBody, functionName)

  assert.match(confirmationBody, /(?:教师贡献题目|由教师贡献)/, `${functionName} 应说明教师贡献题目的风险`)
  assert.match(confirmationBody, /移入回收站/, `${functionName} 应说明是移入回收站而非永久删除`)
  assert.match(confirmationBody, /被未删除作业引用/, `${functionName} 应说明被作业引用时不能删除`)
  assert.match(confirmationBody, /历史答题记录会保留/, `${functionName} 应说明历史答题记录保留`)
}

assert.match(api, /batchDeleteAdminQuestionBank/, '独立题库 API 应提供批量删除题目方法')
assert.match(
  api,
  /\/admin\/question-bank\/batch-delete/,
  '批量删除应调用 /admin/question-bank/batch-delete 接口',
)

const adminQuestionBankNamedImport = page.match(
  /import\s*\{([\s\S]*?)\}\s*from\s*['"]@\/api\/adminQuestionBank['"]/,
)
assert.ok(adminQuestionBankNamedImport, '独立题库页面应从 adminQuestionBank API 命名导入方法')
assert.match(
  adminQuestionBankNamedImport[1],
  /(?:^|,)\s*batchDeleteAdminQuestionBank\s*(?=,|$)/m,
  '独立题库页面应从 adminQuestionBank API 命名导入批量删除方法',
)
assert.match(page, /\bbatchDeleteAdminQuestionBank\s*\(/, '独立题库页面应调用已导入的批量删除方法')
assert.match(page, /一键删除全部/, '独立题库应提供一键删除全部按钮')
assert.match(page, /删除选中/, '独立题库应提供删除选中按钮')
assert.match(page, /type="selection"/, '题库表格应支持多选')
assert.match(page, /removeAllQuestions/, '应实现一键删除全部逻辑')
assert.match(page, /removeSelectedQuestions/, '应实现删除选中逻辑')

for (const functionName of ['removeQuestion', 'removeSelectedQuestions', 'removeAllQuestions']) {
  assertQuestionDeleteConfirmation(functionName)
}
assert.match(api, /skip_count: number/, '管理端导入返回类型应包含跳过数量')
assert.match(api, /skips: \{ row: number; reason: string \}\[\]/, '管理端导入返回类型应包含跳过详情')
assert.match(page, /跳过 \$\{result\.skip_count\} 题/, '导入结果提示应展示跳过数量')
assert.match(page, /\.\.\.result\.skips/, '导入详情应合并展示跳过记录')
assert.match(page, /导入未写入详情/, '导入详情弹窗应同时适用于跳过和失败记录')

// 公共课程页已移除题库维护入口
assert.doesNotMatch(publicPage, /removeSelectedQuestions|removeAllQuestions|openCreateQuestion|showQuestionDialog/, '公共课程页不应再维护题库 CRUD')
assert.match(publicPage, /共享题库/, '公共课程页应引导前往共享题库')

console.log('admin-question-batch-delete-static.test.mjs passed')

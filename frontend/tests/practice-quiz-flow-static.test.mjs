import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import assert from 'node:assert/strict'

const __dirname = dirname(fileURLToPath(import.meta.url))
const viewPath = resolve(__dirname, '../src/views/PracticeQuizView.vue')
const source = readFileSync(viewPath, 'utf8')

function extractFunctionBody(name) {
  const signature = `async function ${name}()`
  const start = source.indexOf(signature)
  assert.notEqual(start, -1, `未找到函数 ${name}`)
  const braceStart = source.indexOf('{', start)
  assert.notEqual(braceStart, -1, `未找到函数 ${name} 的函数体`)

  let depth = 0
  for (let i = braceStart; i < source.length; i++) {
    const char = source[i]
    if (char === '{') depth++
    if (char === '}') depth--
    if (depth === 0) {
      return source.slice(braceStart + 1, i)
    }
  }
  throw new Error(`函数 ${name} 的函数体未闭合`)
}

function test(name, fn) {
  try {
    fn()
    console.log(`✓ ${name}`)
  } catch (error) {
    console.error(`✗ ${name}`)
    throw error
  }
}

const submitAnswerBody = extractFunctionBody('submitAnswer')

test('答对后不进入解析态，直接推进到下一题或完成练习', () => {
  assert.match(
    submitAnswerBody,
    /if\s*\(\s*result\.is_correct\s*\)\s*\{/,
    'submitAnswer 需要在 result.is_correct 为 true 时进入单独分支',
  )
  assert.match(
    submitAnswerBody,
    /currentIndex\.value\s*<\s*totalQuestions\.value\s*-\s*1[\s\S]*nextQuestion\(\)/,
    '非最后一题答对后应调用 nextQuestion() 自动进入下一题',
  )
  assert.match(
    submitAnswerBody,
    /await\s+finishPractice\(\)/,
    '作业模式最后一题答对后应复用 finishPractice() 完成任务',
  )
  assert.match(
    submitAnswerBody,
    /practiceFinished\.value\s*=\s*true/,
    '自由练习最后一题答对后应直接展示总结',
  )
})

test('只有答错时才停留当前题并展示解析', () => {
  const correctBranchStart = submitAnswerBody.indexOf('if (result.is_correct)')
  const submittedAfterCorrectBranch = submitAnswerBody.indexOf('submitted.value = true', correctBranchStart)

  assert.notEqual(correctBranchStart, -1, '缺少正确答案分支')
  assert.notEqual(submittedAfterCorrectBranch, -1, '答错分支需要设置 submitted.value = true')
  assert(
    submittedAfterCorrectBranch > submitAnswerBody.indexOf('return', correctBranchStart),
    'submitted.value = true 应位于正确答案分支提前返回之后，避免正确答案展示解析',
  )
  assert.match(
    submitAnswerBody,
    /results\.value\[currentIndex\.value\]\s*=\s*result\.is_correct[\s\S]*persistDraft\(\)[\s\S]*if\s*\(\s*result\.is_correct\s*\)/,
    '提交后应先记录结果并保存草稿，再按正确或错误分支处理展示状态',
  )
})

test('结果解析框只在答错时渲染', () => {
  assert.match(
    source,
    /<div\s+v-if="submitted && results\[currentIndex\] === false"\s+class="result-box"/,
    'result-box 应只在当前题答错时展示，避免正确题渲染回答正确解析框',
  )
})

// ─── 草稿恢复：仅恢复答对题目 ───

test('草稿恢复仅恢复答对的题目，答错留空重新作答', () => {
  assert.match(
    source,
    /if\s*\(\s*wasCorrect\s*===\s*true\s*\)/,
    '草稿恢复逻辑应只恢复 wasCorrect === true 的题目',
  )
  assert.match(
    source,
    /restoredResults\[idx\]\s*=\s*true/,
    '恢复的结果应标记为 true',
  )
  // 答错的题不应被恢复（不存在 restoredResults[idx] = false 的赋值）
  assert.doesNotMatch(
    source,
    /restoredResults\[idx\]\s*=\s*false/,
    '不应将答错的题恢复为 false，应留空让用户重新作答',
  )
})

test('恢复后全部答对则直接进入总结并清理草稿', () => {
  assert.match(
    source,
    /if\s*\(\s*restoredResults\.every\(\s*r\s*=>\s*r\s*===\s*true\s*\)\s*\)\s*\{[\s\S]*?practiceFinished\.value\s*=\s*true[\s\S]*?clearQuizDraft/,
    '恢复后若全部答对应直接展示总结并清理草稿',
  )
})

// ─── allDone watcher：仅全部答对才自动结束 ───

test('allDone watcher 仅在全部答对时自动结束练习', () => {
  assert.match(
    source,
    /watch\(allDone,\s*\(done\)\s*=>\s*\{[\s\S]*?const\s+allCorrect\s*=\s*results\.value\.every\(\s*r\s*=>\s*r\s*===\s*true\s*\)/,
    'allDone watcher 应检查是否全部答对',
  )
  assert.match(
    source,
    /if\s*\(\s*allCorrect\s*\)\s*\{[\s\S]*?practiceFinished\.value\s*=\s*true[\s\S]*?clearQuizDraft\(null,\s*'global'\)/,
    '全部答对时才设置 practiceFinished 并清理草稿',
  )
})

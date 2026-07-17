import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const quizApi = fs.readFileSync(path.join(root, 'src/api/quiz.ts'), 'utf8')
const practice = fs.readFileSync(path.join(root, 'src/views/PracticeView.vue'), 'utf8')
const quizView = fs.readFileSync(path.join(root, 'src/views/PracticeQuizView.vue'), 'utf8')
const draft = fs.readFileSync(path.join(root, 'src/composables/useQuizDraft.ts'), 'utf8')
const router = fs.readFileSync(path.join(root, 'src/router/index.ts'), 'utf8')

assert.match(quizApi, /\/quiz\/questions/, '应封装全局题池接口')
assert.match(practice, /进入全局练习/, '练习页应只有一个全局自由练习入口')
assert.match(practice, /getQuizStats/, '全局统计应调用 getQuizStats')
assert.doesNotMatch(practice, /goToFreePractice\(c\.id\)/, '课程卡片不应再承载自由练习入口')
assert.match(quizView, /getPracticeQuestions/, '自由练习应调用全局题池')
assert.match(draft, /quiz-draft:global-practice/, '草稿应使用全局键')
assert.match(router, /path: '\/practice\/quiz'/, '应注册全局练习路由')

console.log('global-practice-pool-static.test.mjs passed')

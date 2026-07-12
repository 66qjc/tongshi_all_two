import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = relativePath => readFileSync(resolve(root, relativePath), 'utf8')

const progressApi = read('src/api/progress.ts')
const app = read('src/App.vue')
const courseDetail = read('src/views/CourseDetailView.vue')

assert.match(
  progressApi,
  /visit_started\?:\s*boolean/,
  '课时进度请求类型应显式区分真实进入课时和普通心跳',
)
assert.equal(
  (progressApi.match(/visit_started:\s*data\.visit_started\s*\?\?\s*false/g) || []).length,
  2,
  '普通请求和 keepalive 请求都应序列化 visit_started',
)

assert.equal(
  (app.match(/viewRoute\.path/g) || []).length,
  2,
  '前台和工作台路由组件都应使用 path 作为稳定 key',
)
assert.doesNotMatch(
  app,
  /viewRoute\.fullPath/,
  '仅 lesson_id 查询参数变化时不应重建整个课程页面',
)

assert.match(
  courseDetail,
  /function takeUnreportedDuration\(\)/,
  '课程页应集中读取并清零本次尚未上报的学习时长',
)
assert.doesNotMatch(
  courseDetail,
  /progressDurationSinceLastReport/,
  '旧的重复计时入口应统一为 takeUnreportedDuration',
)
assert.match(
  courseDetail,
  /let finalReportSent\s*=\s*false/,
  '课程页应维护最终补报门闩',
)
assert.match(
  courseDetail,
  /function reportFinalProgressOnce\(\)[\s\S]*finalReportSent[\s\S]*reportLessonProgressKeepalive/,
  '隐藏、离页和卸载应共用一次性 keepalive 补报函数',
)
assert.ok(
  (courseDetail.match(/reportFinalProgressOnce\(\)/g) || []).length >= 4,
  '最终补报函数应由 visibilitychange、pagehide 和卸载共同调用',
)
assert.match(
  courseDetail,
  /reportCurrentLessonProgress\(0,\s*true\)/,
  '每次真正切换课时后应只发送一次访问开始标记',
)
assert.match(
  courseDetail,
  /visit_started:\s*visitStarted/,
  '普通进度上报应将调用方的访问开始标记传给 API',
)
assert.match(
  courseDetail,
  /reportLessonProgressKeepalive[\s\S]*visit_started:\s*false/,
  '最终补报只能累计时长，不能增加访问次数',
)

console.log('课时进度上报静态检查通过')

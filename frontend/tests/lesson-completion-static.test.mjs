import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = relativePath => readFileSync(resolve(root, relativePath), 'utf8')

const lessonReader = read('src/components/lesson/LessonReader.vue')
const courseDetail = read('src/views/CourseDetailView.vue')

assert.match(
  lessonReader,
  /const hasVideoMaterial\s*=\s*computed/,
  '课时阅读器应计算当前课时是否包含视频',
)
assert.match(
  lessonReader,
  /\(e:\s*'content-kind',[^)]*boolean/,
  '课时阅读器应通过 content-kind 事件向父组件暴露视频状态',
)
assert.match(
  lessonReader,
  /emit\('content-kind'/,
  '课时内容变化时应主动报告内容类型',
)

assert.match(
  courseDetail,
  /@content-kind="handleLessonContentKind"/,
  '课程详情应接收课时阅读器的视频状态',
)
assert.match(
  courseDetail,
  /!currentLessonHasVideo/,
  '完成按钮只应出现在不含视频的课时',
)
assert.match(
  courseDetail,
  /currentLessonProgress\?\.status\s*!==\s*'completed'/,
  '已完成课时不应继续显示完成按钮',
)
assert.match(courseDetail, /完成本课/u, '文本或 PDF 课时应提供“完成本课”按钮')
assert.match(
  courseDetail,
  /:loading="completingLesson"/,
  '完成动作提交期间应禁用重复操作并显示加载状态',
)
assert.match(
  courseDetail,
  /reportCurrentLessonProgress\(takeUnreportedDuration\(\),\s*false,\s*100\)/,
  '点击完成本课应上报 100% 并带上本次尚未上报时长',
)
assert.match(
  courseDetail,
  /progressPercentOverride\s*\?\?\s*calculatedLessonPercent\(\)/,
  '普通心跳仍应使用自动进度，显式完成可以覆盖为 100%',
)
assert.match(courseDetail, /本课已完成/u, '完成成功后应给出明确中文反馈')
assert.match(courseDetail, /完成本课失败/u, '完成失败时应给出可理解的中文提示')

console.log('非视频课时完成静态检查通过')

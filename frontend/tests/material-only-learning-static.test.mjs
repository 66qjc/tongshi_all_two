import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = relativePath => readFileSync(resolve(root, relativePath), 'utf8')

const retiredFiles = [
  'src/api/lesson.ts',
  'src/api/progress.ts',
  'src/components/lesson/CourseToc.vue',
  'src/components/lesson/LessonEditor.vue',
  'src/components/lesson/LessonReader.vue',
  'src/components/lesson/PrevNextNav.vue',
  'src/components/lesson/AuthenticatedLessonVideo.vue',
]

for (const relativePath of retiredFiles) {
  assert.equal(existsSync(resolve(root, relativePath)), false, `${relativePath} 应已删除`)
}

const learn = read('src/views/LearnView.vue')
assert.doesNotMatch(
  learn,
  /lesson_id|lesson_count|getLessons|getCourseProgress|progressMap|课时/,
  '教程列表不得再依赖课时和课时进度',
)
assert.match(learn, /material_count/, '教程卡片应继续展示资料数量')

const detail = read('src/views/CourseDetailView.vue')
assert.match(detail, /MaterialInlineReader/, '课程详情应保留资料直读器')
assert.doesNotMatch(
  detail,
  /CourseToc|LessonReader|PrevNextNav|reportLessonProgress|lesson_id|activeTab|完成本课|课时/,
  '课程详情不得再读取或渲染课时能力',
)

const publicApi = read('src/api/publicLearning.ts')
assert.doesNotMatch(
  publicApi,
  /getPublicLessons|normalizeLesson|lesson_count|from ['"]\.\/lesson['"]/,
  '公开学习 API 不得保留课时契约',
)

const packageJson = read('package.json')
const viteConfig = read('vite.config.ts')
assert.doesNotMatch(packageJson, /@wangeditor/, '前端依赖应移除 wangEditor')
assert.doesNotMatch(viteConfig, /vendor-wangeditor|@wangeditor/, 'Vite 应移除 wangEditor 专用分包')

console.log('资料唯一学习主路径静态检查通过')

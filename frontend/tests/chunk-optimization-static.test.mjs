import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
const portfolioView = read('src/views/PortfolioView.vue')
const main = read('src/main.ts')

assert.doesNotMatch(
  teacherCourseDetail,
  /LessonEditor|@\/api\/lesson|@\/api\/progress|getCourseAnalytics|课时|学习分析/,
  '教师课程详情不得再依赖课时、学习分析或富文本编辑器',
)

assert.doesNotMatch(portfolioView, /from ['"]vue-echarts['"]/, '成长档案页不能静态引入 vue-echarts')
assert.doesNotMatch(portfolioView, /from ['"]echarts\//, '成长档案页不能静态引入 ECharts 模块')
assert.match(
  portfolioView,
  /defineAsyncComponent\(\s*\(\)\s*=>\s*import\(['"]@\/components\/portfolio\/PortfolioRadarChart\.vue['"]\)/,
  '成长档案页应动态加载图表组件',
)

assert.doesNotMatch(main, /import\s+\*\s+as\s+ElementPlusIconsVue/, '入口不能全量导入 Element Plus 图标')
assert.match(
  main,
  /import\s+\{\s*Loading\s*\}\s+from ['"]@element-plus\/icons-vue['"]/,
  '入口只注册实际使用的 Loading 图标',
)

console.log('chunk-optimization-static: 所有断言通过')

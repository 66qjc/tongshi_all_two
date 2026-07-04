import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

function assertNoMojibake(name, content) {
  const badPattern =
    /�|(?:Ã|Â|ä|å|è|é|ê|ð|ñ|ò|ó|ô|õ|ö|ù|ú|û|鐠|鐎|閸|閺|閻|缂|妫|鐟|閳|閴|娑|氓|盲|忙|莽|猫|茅|茂录|茫聙|鍏|瀛|璇|绋|涔|鎼|缁|鍔|涓|鐧|鏆|椤|棰|瑙|潰|鈥|鈫|鉁|鈽|狅笍)/
  assert.ok(!badPattern.test(content), `${name} 不应包含中文乱码或误解码字符`)
}

const router = read('src/router/index.ts')
const learn = read('src/views/LearnView.vue')
const detail = read('src/views/CourseDetailView.vue')
const publicApi = read('src/api/publicLearning.ts')
const hero = read('src/components/home/HeroSection.vue')
const toc = read('src/components/lesson/CourseToc.vue')
const reader = read('src/components/lesson/LessonReader.vue')
const prevNext = read('src/components/lesson/PrevNextNav.vue')
const materialCard = read('src/components/common/MaterialRichCard.vue')
const previewDialog = read('src/components/common/MaterialPreviewDialog.vue')
const materialApi = read('src/api/material.ts')
const adminPublicCourses = read('src/views/admin/AdminPublicCourses.vue')
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
const nginxPath = resolve(root, '../deploy/nginx.conf')
const nginx = existsSync(nginxPath) ? read('../deploy/nginx.conf') : ''

assert.match(router, /path:\s*'\/learn'[\s\S]*meta:\s*\{[^}]*public:\s*true/, '/learn 应允许游客访问')
assert.match(
  router,
  /path:\s*'\/learn\/course\/:courseId'[\s\S]*meta:\s*\{[^}]*public:\s*true/,
  '课程阅读页应允许游客访问公开课程',
)
assert.match(
  router,
  /isStudentBusinessPath\(to\.path\)[\s\S]*return '\/teacher'/,
  '教师访问学生业务路径仍应回到教师工作台',
)
assert.ok(
  router.indexOf('isStudentBusinessPath(to.path)') < router.indexOf('if (to.meta.public) return true'),
  '教师学生端拦截必须早于 public 直接放行',
)

assert.match(publicApi, /\/public\/learning\/courses/, '前端应封装公开课程接口')
assert.match(publicApi, /\/public\/learning\/materials\/\$\{materialId\}\/file/, '前端应封装公开资料文件 URL')
assert.match(publicApi, /normalizePublicCourse/, '公开学习接口应规范化课程中文文本')
assert.match(publicApi, /normalizeMaterial/, '公开学习接口应规范化资料中文文本')
assert.match(materialApi, /type:\s*'video'\s*\|\s*'pdf'\s*\|\s*'link'/, '资料展示类型应允许公开链接资料')
assert.match(materialApi, /MaterialCreatePayload[\s\S]*type:\s*'video'\s*\|\s*'pdf'/, '普通上传资料仍只允许视频或 PDF')

assert.match(learn, /AI 通识公开学习馆/, '学习馆标题应使用正常中文')
assert.match(learn, /公开课程书架/, '/learn 应呈现公开课程书架')
assert.match(learn, /selectedCourseId/, '/learn 应记录当前从书架抽出的课程')
assert.match(learn, /selectedCourse/, '/learn 应根据选中课程渲染展开内容')
assert.match(learn, /selectCourse/, '/learn 应支持先选中课程而不是直接跳转')
assert.match(learn, /openSelectedCourse/, '/learn 展开课程后应提供进入课程的明确动作')
assert.match(learn, /ink-learning-stage/, '/learn 应使用水墨学习馆舞台作为课程主视觉')
assert.match(learn, /summer-ink-theme/, '/learn 应使用适配暑假的水墨主题容器')
assert.match(learn, /course-spine-panel/, '/learn 课程选择区应使用书脊式书架面板')
assert.match(learn, /course-spine-rail/, '/learn 课程选择区应使用横向书脊轨道')
assert.match(learn, /course-spine/, '/learn 应把单门课程呈现为竖向书脊')
assert.match(learn, /course-spine-title/, '/learn 书脊应包含课程标题结构')
assert.match(learn, /course-book-panel/, '/learn 应有抽出后展开的课程书面板')
assert.match(learn, /ink-open-book/, '/learn 展开课程应呈现打开的水墨书页结构')
assert.match(learn, /--paper-bg/, '/learn 水墨主题应定义宣纸底色变量')
assert.match(learn, /--wash-green/, '/learn 水墨主题应定义墨绿主色变量')
assert.match(learn, /--water-blue/, '/learn 水墨主题应定义青蓝水色变量')
assert.match(learn, /--spine-accent/, '/learn 书脊应通过 CSS 变量控制主题色')
assert.match(learn, /writing-mode:\s*vertical-rl/, '/learn 书脊标题应使用竖排阅读方向')
assert.match(learn, /course-spine-rail[\s\S]*overflow-x:\s*auto/, '/learn 移动端书脊轨道应支持横向滚动')
assert.doesNotMatch(learn, /learning-map/, '/learn 不应继续保留分散注意力的旧学习路径组件')
assert.doesNotMatch(learn, /materials-strip/, '/learn 本轮应删除旧的最新资料条带，突出课程书架主题')
assert.doesNotMatch(learn, /catalog-search/, '/learn 不应保留课程搜索工具条，避免书架首屏出现无效控件')
assert.doesNotMatch(learn, /keyword/, '/learn 移除搜索工具条后不应继续保留关键词状态')
assert.doesNotMatch(learn, /搜索课程名称/, '/learn 不应继续展示搜索课程名称输入框')
assert.doesNotMatch(learn, /--library-wood/, '/learn 水墨主题不应继续保留木质书架主变量')
assert.doesNotMatch(learn, /shelf-board/, '/learn 水墨主题不应继续保留木质书架类名')
assert.doesNotMatch(learn, /course-volume/, '/learn 应使用书脊类名而不是旧书封卡片类名')

assert.match(detail, /booksite-layout/, '课程阅读页应使用书站式三栏布局容器')
assert.match(detail, /reader-sidebar/, '课程阅读页应包含左侧目录栏')
assert.match(detail, /reader-main/, '课程阅读页应包含中间正文阅读区')
assert.match(detail, /resource-rail/, '课程阅读页应包含右侧资源栏')
assert.match(detail, /本课学习资料/, '右侧资料栏应有正常中文标题')
assert.match(detail, /课程目录/, '课程阅读页目录文案应为正常中文')
assert.match(detail, /登录后可保存学习进度/, '游客状态提示应为正常中文')
assert.match(detail, /getPublicMaterialFileUrl/, '游客预览资料应使用公开资料文件接口')
assert.match(detail, /materials-booksite-layout/, '学习资料页签应使用书站式三栏布局容器')
assert.match(detail, /materials-sidebar/, '学习资料页签应包含左侧资料目录')
assert.match(detail, /materials-reader/, '学习资料页签应包含中间资料阅读流')
assert.match(detail, /materials-rail/, '学习资料页签应包含右侧资料索引栏')
assert.match(detail, /资料目录/, '学习资料页签左侧目录标题应为正常中文')
assert.match(detail, /本页资料/, '学习资料页签右侧索引标题应为正常中文')
assert.match(detail, /scrollToMaterialStage/, '学习资料页签目录应能跳转到对应阶段')
assert.ok(
  detail.indexOf('materials-booksite-layout') < detail.indexOf('stage-section'),
  '学习资料页签应先建立书站式布局，再渲染阶段资料内容',
)
assert.match(
  detail,
  /materials-booksite-layout[\s\S]*materials-sidebar[\s\S]*materials-reader[\s\S]*materials-rail/,
  '学习资料页签三栏结构应同时出现在材料页签模板内',
)

assert.match(previewDialog, /previewUrl/, '资料预览弹窗应支持外部传入公开预览 URL')
assert.match(hero, /中国计量大学/, '首页首屏应出现学校名称')
assert.match(hero, /深度/, '首页首屏应出现“深度”表达')
assert.match(
  adminPublicCourses,
  /material\.type\s*===\s*'link'[\s\S]*该链接资料来自公开学习内容源/,
  '公共课程后台编辑链接资料时应给出中文提示并退出旧上传表单',
)
assert.match(
  teacherCourseDetail,
  /material\.type\s*===\s*'link'[\s\S]*链接资料暂不支持嵌入课时正文/,
  '教师课时正文插入链接资料时应给出中文提示并保持正文占位仅处理视频或 PDF',
)

if (nginx) {
  assert.match(nginx, /try_files\s+\$uri\s+\$uri\/\s+\/index\.html;/, 'Nginx 应支持前端 history 路由刷新')
  assert.match(nginx, /location\s+\/assets\/\s*\{[\s\S]*Cache-Control/, 'Nginx 应缓存前端 assets')
  assert.match(nginx, /location\s+\/_protected_uploads\/\s*\{[\s\S]*internal;/, '公开资料预览依赖已有受保护上传目录')
}

for (const [name, content] of [
  ['router/index.ts', router],
  ['LearnView.vue', learn],
  ['CourseDetailView.vue', detail],
  ['publicLearning.ts', publicApi],
  ['HeroSection.vue', hero],
  ['CourseToc.vue', toc],
  ['LessonReader.vue', reader],
  ['PrevNextNav.vue', prevNext],
  ['MaterialRichCard.vue', materialCard],
  ['MaterialPreviewDialog.vue', previewDialog],
  ['material.ts', materialApi],
  ['AdminPublicCourses.vue', adminPublicCourses],
  ['TeacherCourseDetail.vue', teacherCourseDetail],
]) {
  assertNoMojibake(name, content)
}

console.log('public-learning-static: 所有断言通过')

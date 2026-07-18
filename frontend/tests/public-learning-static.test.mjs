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
const materialCard = read('src/components/common/MaterialRichCard.vue')
const previewDialog = read('src/components/common/MaterialPreviewDialog.vue')
const materialApi = read('src/api/material.ts')
const adminPublicCourses = read('src/views/admin/AdminPublicCourses.vue')
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
const inlineReaderPath = 'src/components/learn/MaterialInlineReader.vue'
const inlineReader = existsSync(resolve(root, inlineReaderPath)) ? read(inlineReaderPath) : ''
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
assert.doesNotMatch(publicApi, /getPublicLessons|normalizeLesson|lesson_count/, '公开学习接口不得保留课时契约')
assert.match(materialApi, /type:\s*'video'\s*\|\s*'pdf'\s*\|\s*'link'/, '资料展示类型应允许公开链接资料')
assert.match(materialApi, /MaterialCreatePayload[\s\S]*type:\s*'video'\s*\|\s*'pdf'/, '普通上传资料仍只允许视频或 PDF')

assert.match(learn, /公开教程/, '/learn 标题应使用公开教程')
assert.match(learn, /course-grid/, '/learn 应以教程卡片网格展示')
assert.match(learn, /course-card/, '/learn 每门教程应使用课程卡片')
assert.match(learn, /getPublicCourses/, '/learn 应请求公开课程列表')
assert.match(learn, /activeKeyword|searchInput/, '/learn 应支持教程名称搜索状态')
assert.match(learn, /runSearch|搜索/, '/learn 应提供搜索动作')
assert.match(learn, /查看教程|查看资料/, '/learn 卡片应提供进入学习动作')
assert.match(learn, /openCourse/, '/learn 点击教程应进入课程阅读页')
assert.match(learn, /material_count/, '/learn 卡片应展示资料数量')
assert.doesNotMatch(learn, /lesson_id|lesson_count|getLessons|getCourseProgress|progressMap|课时/, '/learn 不得依赖课时和进度')
assert.doesNotMatch(learn, /course-spine/, '/learn 不应再使用书脊书架')
assert.doesNotMatch(learn, /ink-open-book/, '/learn 不应再使用翻开书展开面板')
assert.doesNotMatch(learn, /library-facts/, '/learn 不应展示门数/课时/资料总览统计')
assert.doesNotMatch(learn, /materials-strip/, '/learn 不应展示最新资料条带')
assert.doesNotMatch(learn, /learning-map/, '/learn 不应继续保留旧学习路径组件')
assert.doesNotMatch(learn, /--library-wood/, '/learn 不应保留木质书架变量')
assert.doesNotMatch(learn, /shelf-board/, '/learn 不应保留木质书架类名')

assert.match(detail, /返回教程列表/, '课程阅读页应提供返回教程列表')
assert.match(detail, /getPublicMaterialFileUrl/, '游客预览资料应使用公开资料文件接口')
assert.match(detail, /activeMaterialId/, '学习资料页应维护当前选中的资料 ID')
assert.match(detail, /activeMaterial/, '学习资料页应计算当前直读资料')
assert.match(detail, /defaultMaterial/, '学习资料页应有默认资料选择逻辑')
assert.match(detail, /pickDefaultMaterial/, '学习资料页应优先选取更适合学习的默认资料')
assert.match(detail, /materialLearningScore/, '学习资料页应按资料类型、标题和体量计算默认阅读优先级')
assert.match(detail, /selectMaterial/, '左侧目录点击资料后应切换当前阅读资料')
assert.match(detail, /toggleStage/, '资料目录阶段头应支持折叠展开')
assert.match(detail, /collapsedStageKeys/, '资料目录应维护阶段折叠状态')
assert.match(detail, /stage-head/, '资料目录阶段应使用紧凑分组头')
assert.match(detail, /stage-materials/, '资料条目应缩进在阶段分组下')
assert.doesNotMatch(detail, /guide-facts/, '右侧当前资料不应再展示类型/大小等 facts 列表')
assert.match(detail, /MaterialInlineReader/, 'CourseDetailView 应引入直读式资料阅读组件')
assert.match(detail, /material-doc-shell/, '学习资料页应使用文档站式资料阅读外壳')
assert.match(detail, /material-doc-sidebar/, '学习资料页应包含左侧阶段化资料目录')
assert.match(detail, /material-doc-main/, '学习资料页应包含中间当前资料阅读区')
assert.match(detail, /material-doc-guide/, '学习资料页应包含右侧当前资料导读')
assert.match(detail, /上一份资料/, '右侧导读应提供上一份资料入口')
assert.match(detail, /下一份资料/, '右侧导读应提供下一份资料入口')
assert.match(detail, /activeMaterialFileUrl/, '学习资料页应计算当前资料文件 URL')
assert.match(detail, /getPublicMaterialFileUrl/, '公开资料直读应继续复用公开资料文件接口')
const materialFileUrlBody = detail.match(/function materialFileUrl\(material: Material\)\s*\{([\s\S]*?)\n\}/)?.[1] || ''
const publicLinkIndex = materialFileUrlBody.indexOf("material.type === 'link'")
const publicSourceIndex = materialFileUrlBody.indexOf("contentSource.value === 'public'")
assert.ok(
  publicLinkIndex >= 0 && publicSourceIndex > publicLinkIndex,
  '公开链接资料必须先使用 material.url，不能改写为没有文件记录的公开文件接口。',
)
assert.ok(
  publicSourceIndex >= 0 && publicSourceIndex < materialFileUrlBody.indexOf('material.file_id'),
  '公开数据源判断必须早于 file_id，登录状态不得把公开资料改走私有接口。',
)
assert.match(
  detail,
  /selectedMaterial\.value\.type\s*===\s*['"]link['"][\s\S]*?return undefined[\s\S]*?contentSource\.value\s*===\s*['"]public['"]/,
  '公开链接资料打开预览时也不得传入公开文件接口。',
)
assert.match(detail, /useAuthenticatedFileUrl/, '课程详情父级应解析当前资料文件地址')
assert.match(detail, /activeMaterialResolvedUrl/, '直读器和打开原资料入口应复用同一解析地址')
assert.match(detail, /hasRefreshingMaterialPreview/, '学习资料页应识别是否存在生成中的资料预览')
assert.match(detail, /refreshMaterialsForInlineReader/, '学习资料页应提供直读器资料刷新方法')
assert.match(detail, /setInterval[\s\S]*refreshMaterialsForInlineReader/, '学习资料页应在预览生成中定时刷新资料数据')
assert.match(detail, /visibilitychange/, '学习资料页应在页面重新可见时刷新资料数据')
assert.match(detail, /clearInterval/, '学习资料页卸载时应清理资料刷新定时器')
assert.match(
  detail,
  /material-doc-shell[\s\S]*material-doc-sidebar[\s\S]*material-doc-main[\s\S]*material-doc-guide/,
  '学习资料页应同时包含文档站式左目录、中间直读区和右导读栏',
)
assert.doesNotMatch(
  detail,
  /CourseToc|LessonReader|PrevNextNav|reportLessonProgress|lesson_id|activeTab|完成本课|课时|booksite-layout/,
  '课程详情不得再读取或渲染课时能力',
)
assert.doesNotMatch(
  detail,
  /<main v-else class="materials-content">[\s\S]*<MaterialRichCard/,
  '学习资料页主流程不应继续以 MaterialRichCard 卡片流作为中间主体',
)
assert.doesNotMatch(
  detail,
  /<main v-else class="materials-content">[\s\S]*@click="previewMaterial\(material\)"/,
  '学习资料页主流程不应通过点击预览弹窗阅读资料',
)

assert.ok(inlineReader, '应新增 MaterialInlineReader.vue 直读式资料阅读组件')
assert.match(inlineReader, /defineProps/, 'MaterialInlineReader 应声明 props')
assert.match(inlineReader, /material:\s*Material\s*\|\s*null/, 'MaterialInlineReader 应接收当前资料')
assert.match(inlineReader, /fileUrl:\s*string/, 'MaterialInlineReader 应接收当前资料文件 URL')
assert.match(inlineReader, /VuePdfEmbed/, 'MaterialInlineReader 应使用 vue-pdf-embed 在页面内真实渲染 PDF')
assert.match(
  inlineReader,
  /vue-pdf-embed\/dist\/index\.essential\.mjs/,
  'MaterialInlineReader 应使用 vue-pdf-embed essential 入口以便显式配置 PDF worker',
)
assert.match(inlineReader, /GlobalWorkerOptions/, 'MaterialInlineReader 应显式配置 PDF.js worker')
assert.match(inlineReader, /pdf\.worker\.min\.mjs\?url/, 'MaterialInlineReader 应通过 Vite URL 导入 PDF worker')
assert.match(inlineReader, /type === 'pdf'/, 'MaterialInlineReader 应处理 PDF 资料')
assert.doesNotMatch(inlineReader, /useAuthenticatedFileUrl|\bblobUrl\b|response\.blob\s*\(|URL\.createObjectURL\s*\(|\bfetch\s*\(/, '直读器应只消费父级解析地址，允许浏览器和 PDF.js 按需 Range 读取')
assert.match(inlineReader, /<VuePdfEmbed[\s\S]*:source="fileUrl"/, 'PDF 资料应在页面中间通过父级解析地址直接渲染阅读')
assert.match(inlineReader, /pdfPagesToRender/, 'PDF 资料应控制首屏渲染页数，避免长 PDF 首屏等待过久')
assert.match(inlineReader, /:page="pdfPagesToRender"/, 'PDF 直读器应先渲染可见页再逐步加载更多')
assert.match(inlineReader, /IntersectionObserver/, 'PDF 资料应使用滚动观察器自动加载后续页面')
assert.match(inlineReader, /pdfLoadSentinel/, 'PDF 资料应在内容底部放置自动加载观察哨兵')
assert.match(inlineReader, /const\s+nextPageCount\s*=\s*visiblePdfPageCount\.value\s*\+\s*2/, 'PDF 资料每次应自动追加两页')
assert.doesNotMatch(inlineReader, /加载更多页面/, 'PDF 长资料不应再要求点击加载更多页面')
assert.doesNotMatch(inlineReader, /pdf-open-row/, 'PDF 正文下方不应保留重复的打开原资料区域')
assert.match(inlineReader, /@loaded="handlePdfLoaded"/, 'PDF 加载完成后应记录直读器状态')
assert.match(inlineReader, /@loading-failed="pdfFailureHandler"/, 'PDF 加载失败时应通过固化地址的处理器显示中文失败状态')
assert.match(inlineReader, /@rendering-failed="pdfFailureHandler"/, 'PDF 渲染失败时应通过固化地址的处理器显示中文失败状态')
assert.match(inlineReader, /emit\(['"]file-error['"],\s*failedUrl\)/, 'PDF 或视频加载失败应携带实际失败地址通知父级续签一次')
assert.match(
  inlineReader,
  /<object\s+v-else-if="fileUrl && !fileError && pdfStatus === 'error'"[\s\S]*?:data="fileUrl"/,
  '浏览器 PDF object 只能在 PDF.js 失败后按需挂载，不能与 PDF.js 并行下载。',
)
assert.match(inlineReader, /浏览器无法直接显示 PDF/, 'PDF 内嵌失败时应有中文降级提示')
assert.match(inlineReader, /type === 'video'/, 'MaterialInlineReader 应处理视频资料')
	assert.match(inlineReader, /<video[\s\S]*controls/, '视频资料应在页面中间直接播放')
	assert.match(inlineReader, /type === 'link'/, 'MaterialInlineReader 应处理链接资料')
	assert.match(inlineReader, /打开原资料/, '链接资料应提供打开入口')
	assert.match(inlineReader, /props\.material\.type === 'pdf'/, '直读器应仅对 PDF 展示抽取摘要')
	assert.match(inlineReader, /PDF 摘要生成中/, 'PDF 摘要生成中应有中文状态')
	assert.match(detail, /function materialSummary\(material: Material\)/, '课程详情右侧导读应展示资料摘要')
	assert.match(detail, /material\.type !== 'pdf'/, '右侧导读应区分 PDF 与其它资料类型')

assert.match(previewDialog, /previewUrl/, '资料预览弹窗应支持外部传入公开预览 URL')
assert.match(
  hero,
  /中国计量大学 · AI 通识教育课程平台/,
  '首页首屏应使用当前学校与平台完整品牌文案',
)
assert.match(
  adminPublicCourses,
  /material\.type\s*===\s*'link'[\s\S]*该链接资料来自公开学习内容源/,
  '公共课程后台编辑链接资料时应给出中文提示并退出旧上传表单',
)
// 教师端课时能力将在后续任务清理；此处仅校验中文无乱码与文件可读
assert.ok(teacherCourseDetail.length > 0, '教师课程详情页仍应存在')

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
  ['MaterialRichCard.vue', materialCard],
  ['MaterialPreviewDialog.vue', previewDialog],
  ['MaterialInlineReader.vue', inlineReader],
  ['material.ts', materialApi],
  ['AdminPublicCourses.vue', adminPublicCourses],
  ['TeacherCourseDetail.vue', teacherCourseDetail],
]) {
  assertNoMojibake(name, content)
}

console.log('public-learning-static: 所有断言通过')

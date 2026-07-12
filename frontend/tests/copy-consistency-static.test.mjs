import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
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

const teacherDashboard = read('src/views/teacher/TeacherDashboard.vue')
const teacherAnnouncements = read('src/views/teacher/TeacherAnnouncements.vue')
const teacherCourses = read('src/views/teacher/TeacherCourses.vue')
const teacherCourseDetail = read('src/views/teacher/TeacherCourseDetail.vue')
const teacherMaterials = read('src/views/teacher/TeacherMaterials.vue')
const teacherQuestions = read('src/views/teacher/TeacherQuestions.vue')
const teacherReviews = read('src/views/teacher/TeacherReviews.vue')
const teacherStudents = read('src/views/teacher/TeacherStudents.vue')
const teacherTaskReport = read('src/views/teacher/TeacherTaskReport.vue')
const adminPasswordReset = read('src/views/admin/AdminPasswordReset.vue')
const adminPublicCourses = read('src/views/admin/AdminPublicCourses.vue')
const adminShowcase = read('src/views/admin/AdminShowcase.vue')
const hero = read('src/components/home/HeroSection.vue')
const moduleShowcase = read('src/components/home/ModuleShowcase.vue')
const statsSection = read('src/components/home/StatsSection.vue')
const appFooter = read('src/components/AppFooter.vue')
const learn = read('src/views/LearnView.vue')
const courseDetail = read('src/views/CourseDetailView.vue')
const practiceAssignments = read('src/views/PracticeAssignments.vue')
const practiceQuiz = read('src/views/PracticeQuizView.vue')
const inbox = read('src/views/InboxView.vue')
const createView = read('src/views/CreateView.vue')
const projectDetail = read('src/views/ProjectDetailView.vue')
const profileView = read('src/views/ProfileView.vue')
const materialRichCard = read('src/components/common/MaterialRichCard.vue')
const materialPreviewDialog = read('src/components/common/MaterialPreviewDialog.vue')
const pdfPreviewDialog = read('src/components/common/PdfPreviewDialog.vue')
const httpApi = read('src/api/http.ts')
const router = read('src/router/index.ts')

test('教师端统计与作业术语应匹配实际业务口径', () => {
  assert.doesNotMatch(teacherDashboard, /本周练习/, '教师工作台不能把累计练习次数写成“本周练习”')
  assert.match(teacherDashboard, /累计练习/, '教师工作台练习统计应使用累计口径文案')
  assert.match(teacherDashboard, /新增、编辑或导入题目/, '教师工作台题库入口应使用题目术语')
  assert.doesNotMatch(teacherDashboard, /练习题/, '教师工作台不应把单道题称为练习题')
  assert.match(teacherAnnouncements, /确定删除作业「\$\{row\.title\}」/, '删除作业确认应带作业名称')
  assert.doesNotMatch(teacherAnnouncements, /发布题目/, '教师发布页不应再把作业称为发布题目')
  assert.doesNotMatch(teacherTaskReport, /作业任务/, '作业完成页不应混用“作业任务”')
})

test('教师端危险操作和空状态应说明真实后果和下一步', () => {
  assert.match(teacherCourses, /将删除你工作台中的课程副本/, '删除课程应说明会影响教师自己的课程副本')
  assert.match(teacherCourses, /不影响公共课程源/, '删除课程应说明不影响公共课程源')
  assert.match(teacherCourseDetail, /所属阶段改为「未分类」或其他阶段/, '删除阶段失败提示应给出可执行移动方式')
  assert.match(teacherCourseDetail, /本课程副本中的资料/, '课程详情资料删除应统一课程副本文案')
  assert.match(teacherMaterials, /本课程副本中的资料/, '资料管理删除应统一课程副本文案')
  assert.match(teacherMaterials, /暂无资料。点击「上传资料」添加到所选课程。/, '教师资料空状态应说明上传资料并归入所选课程')
  assert.doesNotMatch(teacherMaterials, /添加课程资料/, '教师资料空状态不应混用课程资料')
  assert.match(teacherStudents, /当前筛选条件下暂无学生成绩/, '学生成绩空状态应适配筛选场景')
  assert.match(teacherReviews, /当前筛选条件下暂无作品/, '作品审核空状态应适配筛选场景')
  assert.match(teacherReviews, /PDF 预览不稳定时/, 'PDF 预览提示不应暴露服务器环境说明')
  assert.match(teacherReviews, /在新窗口打开报告/, '教师作品 PDF 预览降级说明应使用新窗口打开')
  assert.doesNotMatch(teacherReviews, /新窗口查看/, '教师作品 PDF 预览降级说明不应使用新窗口查看')
  assert.doesNotMatch(teacherAnnouncements, /题目属于同一课程|当前课程暂无题目/, '共享题库后发布作业页不应暗示题目必须属于当前课程')
  assert.match(teacherAnnouncements, /题库暂无题目，请先到题库管理中新增或导入题目。/, '共享题库空状态应说明全站题库暂无题目')
})

test('导入说明应有中文解释且避免纯内部枚举口吻', () => {
  assert.match(teacherQuestions, /choice（选择题）/, '教师题库导入说明应解释 choice')
  assert.match(teacherQuestions, /multi_choice（多选题）/, '教师题库导入说明应解释 multi_choice')
  assert.match(teacherQuestions, /fill（填空题）/, '教师题库导入说明应解释 fill')
  assert.match(adminPublicCourses, /choice（选择题）/, '管理员题库导入说明应解释 choice')
  assert.match(adminPublicCourses, /multi_choice（多选题）/, '管理员题库导入说明应解释 multi_choice')
  assert.match(adminPublicCourses, /fill（填空题）/, '管理员题库导入说明应解释 fill')
})

test('管理端文案承诺应和实际行为一致', () => {
  assert.match(
    adminPasswordReset,
    /const\s+result\s*=\s*await\s+ElMessageBox\.prompt/,
    '管理员驳回密码重置时应读取 prompt 结果',
  )
  assert.match(
    adminPasswordReset,
    /adminRejectPasswordResetRequest\(requestId,\s*reason\)/,
    '管理员驳回密码重置时应把驳回原因传给接口',
  )
  assert.match(adminShowcase, /上传后可预览，保存后前台生效/, '封面上传提示不能误导为立即前台生效')
  assert.match(adminPublicCourses, /资料和阶段会同步到教师课程副本，题库为全站共享/, '公共课程说明应区分资料阶段同步和全站共享题库')
  assert.match(adminPublicCourses, /公共课程源资料/, '删除公共资料应使用公共课程源术语')
  assert.match(adminPublicCourses, /教师课程副本中移除对应同步资料/, '删除公共资料应说明同步资料会从教师课程副本移除')
  assert.match(adminPublicCourses, /教师自行新增资料不受影响/, '删除公共资料应说明不影响教师自建资料')
  assert.match(adminPublicCourses, /教师自行新增题目不受影响/, '删除公共题目应说明不影响教师自建题目')
  assert.match(adminPublicCourses, /全站共享题库/, '公共题库文案应说明题库是全站共享')
  assert.doesNotMatch(adminPublicCourses, /同步题目|公共题目已(?:新增|更新)，并同步|暂无题目，新增后会同步|导入后会自动同步/, '题库说明不应继续使用题目同步到教师课程副本的旧口径')
  assert.doesNotMatch(adminPublicCourses, /公共源/, '管理端应使用公共课程源完整术语')
  assert.doesNotMatch(adminPublicCourses, /:title="previewTitle"/, '管理端资料预览不应覆盖通用资料预览标题')
  assert.doesNotMatch(adminPublicCourses, /公开学习数据源/, '管理端不应暴露“公开学习数据源”这种内部口吻')
})

test('公开端长文案不应暴露内部迁移说明或错误登录边界', () => {
  assert.match(hero, /登录后查看作品展示，并提交自己的实践成果/, '首页作品入口应说明需要登录')
  assert.doesNotMatch(hero, /查看优秀作品，登录后提交/, '首页作品入口不应暗示游客可查看作品')
  assert.doesNotMatch(moduleShowcase, /写死|旧模块|真实数据/, '首页模块说明不应暴露开发迁移说明')
  assert.doesNotMatch(statsSection, /旧模块|过期|真实数据/, '首页统计区不应暴露开发迁移说明')
  assert.doesNotMatch(appFooter, /课程大纲/, '页脚不应把公开学习馆称为课程大纲')
  assert.match(appFooter, /公开学习馆/, '页脚应使用公开学习馆术语')
  const createRoute = router.match(/path:\s*['"]\/create['"][\s\S]*?\n\s*\},/u)?.[0] || ''
  assert.doesNotMatch(createRoute, /public:\s*true/, '作品入口必须要求登录，不能标记为公开路由')
})

test('学生端应统一公开学习馆、学习资料和作业术语', () => {
  assert.match(learn, /选择一门课程，查看简介、课时和学习资料/, '学习馆说明应使用直接任务指令')
  assert.doesNotMatch(learn, /抽出一门课程|翻看简介|右侧会抽出展开/, '学习馆说明不应过度依赖书架隐喻')
  assert.match(moduleShowcase, /进入公开学习馆查看课程与学习资料/, '首页学习入口状态应使用公开学习馆口径')
  assert.match(moduleShowcase, /作业、练习和错题/, '首页练习入口状态应使用作业术语')
  assert.doesNotMatch(moduleShowcase, /学习页|最新课程|任务集中处理|按任务选择/, '首页模块长文案不应保留旧学习页或任务口径')
  assert.match(moduleShowcase, /查看学习资料/, '首页学习入口动作应使用学习资料术语')
  assert.doesNotMatch(moduleShowcase, /查看课程资料/, '首页学习入口动作不应混用课程资料')
  assert.match(courseDetail, /本课学习资料/, '课程右侧栏应使用学习资料术语')
  assert.match(courseDetail, /查看全部学习资料/, '课程资料入口应使用学习资料术语')
  assert.match(courseDetail, /学习资料库/, '资料页签应使用学习资料库术语')
  assert.doesNotMatch(courseDetail, /本课资源|课程资料库/, '学生端不应混用资源或课程资料库')
  assert.match(practiceAssignments, /选择作业/, '作业列表应使用作业术语')
  assert.match(inbox, /查看老师发布的作业/, '学生消息页应把教师发布的答题活动称为作业')
  assert.doesNotMatch(inbox, /题目任务|该任务已截止/, '学生消息页不应把作业混称为题目任务或任务')
  assert.doesNotMatch(practiceQuiz, /任务练习|该任务暂未配置题目|任务完成失败/, '学生答题页不应把作业混称为任务')
  assert.match(practiceQuiz, /作业暂未配置题目/, '学生答题页空状态应使用作业术语')
  assert.match(practiceQuiz, /作业完成状态提交失败/, '学生答题页失败兜底应说明作业完成状态提交失败')
})

test('作品和个人中心空状态应给出明确下一步', () => {
  assert.match(createView, /查看同学提交的课程作品、报告和演示链接/, '作品页说明应具体说明可查看内容')
  assert.doesNotMatch(createView, /碰撞的火花/, '作品页说明不应使用空泛宣传语')
  assert.match(projectDetail, /在新窗口打开 PDF 报告/, '作品详情 PDF 报告入口应使用新窗口打开动作')
  assert.doesNotMatch(projectDetail, /查看 PDF 报告/, '作品详情 PDF 报告入口不应使用查看口径')
  assert.match(profileView, /完成课程练习后，这里会汇总答错题目/, '错题空状态应说明触发条件')
  assert.match(profileView, /前往作品页查看已审核作品/, '收藏空状态应给出明确入口')
})

test('通用资料组件应统一资料预览和打开动作', () => {
  assert.match(materialRichCard, /暂无资料摘要/, '资料卡片摘要缺省应使用中性文案')
  assert.match(materialRichCard, /可在新窗口打开文件/, '资料卡片应对应新窗口打开动作')
  assert.doesNotMatch(materialRichCard, /return '预览生成中'\s*[\r\n\s]*\}/, '未知预览状态不应默认显示生成中')
  assert.match(materialPreviewDialog, /title="资料预览"/, '通用资料弹窗标题应统一为资料预览')
  assert.match(materialPreviewDialog, /在新窗口打开/, '通用资料弹窗按钮应统一为在新窗口打开')
  assert.match(pdfPreviewDialog, /title \|\| '资料预览'/, 'PDF 弹窗默认标题应统一为资料预览')
  assert.match(pdfPreviewDialog, /在新窗口打开/, 'PDF 弹窗按钮应统一为在新窗口打开')
})

test('未知校验错误不应直接透出技术细节', () => {
  assert.match(
    httpApi,
    /return '提交内容不符合要求，请检查填写内容'/,
    '未知校验错误应回落为中文通用提示',
  )
  assert.doesNotMatch(httpApi, /return message\s*\n\}/, '未知校验错误不应原样返回后端技术消息')
})

console.log('copy-consistency-static: 所有断言通过')

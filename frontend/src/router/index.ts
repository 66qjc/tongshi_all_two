import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return true
    const payload = JSON.parse(atob(parts[1]!))
    if (!payload.exp) return false
    return payload.exp * 1000 < Date.now() + 10_000
  } catch {
    return true
  }
}

const studentBusinessPathPrefixes = [
  '/learn',
  '/practice',
  '/create',
  '/act',
  '/portfolio',
  '/inbox',
  '/student/notifications',
  '/student/settings/notifications',
]

function isStudentBusinessPath(path: string): boolean {
  return studentBusinessPathPrefixes.some(prefix => path === prefix || path.startsWith(`${prefix}/`))
}

const AdminLayout = () => import('../views/admin/AdminLayout.vue')
const AdminTeachers = () => import('../views/admin/AdminTeachers.vue')
const ChangePasswordView = () => import('../views/ChangePasswordView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { title: '学 · 思 · 践 · 悟 — AI 通识课平台' },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: '登录 · AI 通识课程平台', public: true },
    },
    {
      path: '/learn',
      name: 'learn',
      component: () => import('../views/LearnView.vue'),
      meta: { title: '学 · 公开教程', public: true },
    },
    {
      path: '/learn/course/:courseId',
      name: 'course-detail',
      component: () => import('../views/CourseDetailView.vue'),
      meta: { title: '课程阅读', public: true },
    },
    {
      path: '/practice',
      name: 'practice',
      component: () => import('../views/PracticeView.vue'),
      meta: { title: '思 · 学以致用' },
    },
    {
      path: '/create',
      name: 'create',
      component: () => import('../views/CreateView.vue'),
      meta: { title: '践 · 智创未来', public: true },
    },
    {
      path: '/act',
      name: 'act',
      component: () => import('../views/ActView.vue'),
      meta: { title: '悟 · 知行合一', public: true },
    },
    {
      path: '/act/showcase/:id',
      name: 'act-showcase-detail',
      component: () => import('../views/ActDetailView.vue'),
      meta: { title: '行动详情', public: true },
    },
    {
      path: '/practice/assignments',
      name: 'practice-assignments',
      component: () => import('../views/PracticeAssignments.vue'),
      meta: { title: '选择作业' },
    },
    {
      path: '/practice/quiz',
      name: 'practice-quiz-global',
      component: () => import('../views/PracticeQuizView.vue'),
      meta: { title: '思 · 自由练习' },
    },
    {
      path: '/practice/quiz/:courseId',
      name: 'practice-quiz',
      redirect: (to) => ({
        path: '/practice/quiz',
        query: {
          ...to.query,
          // 保留旧链接的 random/question_ids，不再使用 courseId
        },
      }),
      meta: { title: '思 · 在线练习' },
    },
    {
      path: '/practice/announcement/:announcementId',
      name: 'practice-announcement',
      component: () => import('../views/PracticeQuizView.vue'),
      meta: { title: '作业练习' },
    },
    {
      path: '/create/project/:id',
      name: 'project-detail',
      component: () => import('../views/ProjectDetailView.vue'),
      meta: { title: '作品详情', public: true },
    },
    {
      path: '/create/upload',
      name: 'project-upload',
      component: () => import('../views/ProjectUploadView.vue'),
      meta: { title: '提交作品' },
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: () => import('../views/PortfolioView.vue'),
      meta: { title: '我的成长档案' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { title: '个人中心' },
    },
    {
      path: '/inbox',
      name: 'inbox',
      component: () => import('../views/InboxView.vue'),
      meta: { title: '消息通知' },
    },
    {
      path: '/student/notifications',
      name: 'student-notifications',
      component: () => import('../views/InboxView.vue'),
      meta: { title: '通知中心' },
    },
    {
      path: '/student/settings/notifications',
      name: 'student-notification-settings',
      component: () => import('../views/InboxView.vue'),
      meta: { title: '通知偏好' },
    },
    {
      path: '/teacher',
      component: () => import('../views/teacher/TeacherLayout.vue'),
      meta: { title: '教师工作台', role: 'teacher' },
      children: [
        {
          path: '',
          name: 'teacher-dashboard',
          component: () => import('../views/teacher/TeacherDashboard.vue'),
          meta: { title: '教师工作台' },
        },
        {
          path: 'classes',
          name: 'teacher-classes',
          component: () => import('../views/teacher/TeacherClasses.vue'),
          meta: { title: '班级管理' },
        },
        {
          path: 'questions',
          name: 'teacher-questions',
          component: () => import('../views/teacher/TeacherQuestions.vue'),
          meta: { title: '共享题库' },
        },
        {
          path: 'courses',
          name: 'teacher-courses',
          component: () => import('../views/teacher/TeacherCourses.vue'),
          meta: { title: '管理课程' },
        },
        {
          path: 'courses/:courseId',
          name: 'teacher-course-detail',
          component: () => import('../views/teacher/TeacherCourseDetail.vue'),
          meta: { title: '管理课程' },
        },
        {
          path: 'publish',
          name: 'teacher-publish',
          component: () => import('../views/teacher/TeacherAnnouncements.vue'),
          meta: { title: '发布作业' },
        },
        {
          path: 'grades',
          name: 'teacher-grades',
          component: () => import('../views/teacher/TeacherStudents.vue'),
          meta: { title: '学生成绩' },
        },
        {
          path: 'task-report',
          name: 'teacher-task-report',
          component: () => import('../views/teacher/TeacherTaskReport.vue'),
          meta: { title: '任务完成' },
        },
        {
          path: 'task-report/:taskId',
          name: 'teacher-task-report-detail',
          component: () => import('../views/teacher/TeacherTaskReportDetail.vue'),
          meta: { title: '作业完成详情' },
        },
        {
          path: 'student-admin',
          name: 'teacher-student-admin',
          component: () => import('../views/teacher/TeacherStudentAdmin.vue'),
          meta: { title: '学生管理' },
        },
        {
          path: 'reviews',
          name: 'teacher-reviews',
          component: () => import('../views/teacher/TeacherReviews.vue'),
          meta: { title: '作品审核' },
        },
        {
          path: 'random-picker',
          name: 'teacher-random-picker',
          component: () => import('../views/teacher/TeacherRandomPicker.vue'),
          meta: { title: 'AI 随机点名' },
        },
      ],
    },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { role: 'admin' },
      children: [
        { path: '', redirect: '/admin/teachers' },
        { path: 'teachers', component: AdminTeachers, meta: { title: '教师管理', role: 'admin' } },
        {
          path: 'public-courses',
          component: () => import('../views/admin/AdminPublicCourses.vue'),
          meta: { title: '公共课程', role: 'admin' },
        },
        {
          path: 'question-bank',
          component: () => import('../views/admin/AdminQuestionBank.vue'),
          meta: { title: '共享题库', role: 'admin' },
        },
        {
          path: 'showcase',
          component: () => import('../views/admin/AdminShowcase.vue'),
          meta: { title: '内容管理', role: 'admin' },
        },
        {
          path: 'password-reset',
          component: () => import('../views/admin/AdminPasswordReset.vue'),
          meta: { title: '密码重置管理', role: 'admin' },
        },
        {
          path: 'recycle-bin',
          component: () => import('../views/admin/AdminRecycleBin.vue'),
          meta: { title: '数据回收站', role: 'admin' },
        },
        {
          path: 'audit-logs',
          component: () => import('../views/admin/AdminAuditLogs.vue'),
          meta: { title: '审计日志', role: 'admin' },
        },
      ],
    },
    {
      path: '/change-password',
      component: ChangePasswordView,
      meta: { title: '修改密码' },
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
      meta: { title: '关于平台', public: true },
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: () => import('../views/PrivacyView.vue'),
      meta: { title: '隐私政策', public: true },
    },
    {
      path: '/contact',
      name: 'contact',
      component: () => import('../views/ContactView.vue'),
      meta: { title: '联系我们', public: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
      meta: { title: '页面未找到', public: true },
    },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0, behavior: 'smooth' }
  },
})

router.beforeEach((to) => {
  document.title = (to.meta.title as string) || '学 · 思 · 践 · 行 · AI 通识课程平台'

  const authStore = useAuthStore()

  // Token 过期后清除登录态；公开页面按游客身份继续访问。
  if (authStore.isLoggedIn && authStore.token && isTokenExpired(authStore.token)) {
    authStore.logout()
    if (to.meta.public || to.path === '/') return true
    return '/login'
  }

  // 教师访问首页时自动进入教师工作台。
  if (authStore.isLoggedIn && authStore.user?.role === 'teacher' && to.path === '/') {
    return '/teacher'
  }

  // 教师端只进入教师工作台，不展示学生端业务页面。
  if (
    authStore.isLoggedIn &&
    authStore.user?.role === 'teacher' &&
    isStudentBusinessPath(to.path)
  ) {
    return '/teacher'
  }

  // 公开路由允许游客与已登录用户访问。
  if (to.meta.public) return true

  if (!authStore.isLoggedIn) {
    if (to.path === '/') return true
    return '/login'
  }

  // 首次登录或重置密码后，先完成密码修改。
  if (
    authStore.isLoggedIn &&
    authStore.user?.needs_password_change &&
    to.path !== '/change-password'
  ) {
    return '/change-password'
  }

  // 管理员访问首页时自动进入管理后台。
  if (to.path === '/' && authStore.isLoggedIn && authStore.user?.role === 'admin') {
    return '/admin'
  }

  if (to.meta.role === 'teacher' && authStore.user?.role !== 'teacher') {
    return '/'
  }
  if (to.meta.role === 'admin' && authStore.user?.role !== 'admin') {
    return '/'
  }

  return true
})

export default router

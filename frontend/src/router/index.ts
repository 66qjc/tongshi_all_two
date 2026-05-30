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
      meta: { title: '登录 — AI 通识课平台', public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { title: '注册 — AI 通识课平台', public: true },
    },
    {
      path: '/learn',
      name: 'learn',
      component: () => import('../views/LearnView.vue'),
      meta: { title: '探 · 学无止境' },
    },
    {
      path: '/learn/course/:courseId',
      name: 'course-detail',
      component: () => import('../views/CourseDetailView.vue'),
      meta: { title: '课程详情' },
    },
    {
      path: '/practice',
      name: 'practice',
      component: () => import('../views/PracticeView.vue'),
      meta: { title: '练 · 学以致用' },
    },
    {
      path: '/create',
      name: 'create',
      component: () => import('../views/CreateView.vue'),
      meta: { title: '造 · 智创未来' },
    },
    {
      path: '/act',
      name: 'act',
      component: () => import('../views/ActView.vue'),
      meta: { title: '行 · 知行合一' },
    },
    {
      path: '/practice/quiz/:courseId',
      name: 'practice-quiz',
      component: () => import('../views/PracticeQuizView.vue'),
      meta: { title: '练 · 在线练习' },
    },
    {
      path: '/create/project/:id',
      name: 'project-detail',
      component: () => import('../views/ProjectDetailView.vue'),
      meta: { title: '作品详情' },
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
          path: 'materials',
          name: 'teacher-materials',
          component: () => import('../views/teacher/TeacherMaterials.vue'),
          meta: { title: '资料管理' },
        },
        {
          path: 'questions',
          name: 'teacher-questions',
          component: () => import('../views/teacher/TeacherQuestions.vue'),
          meta: { title: '题库管理' },
        },
        {
          path: 'courses',
          name: 'teacher-courses',
          component: () => import('../views/teacher/TeacherCourses.vue'),
          meta: { title: '课程管理' },
        },
        {
          path: 'publish',
          name: 'teacher-publish',
          component: () => import('../views/teacher/TeacherAnnouncements.vue'),
          meta: { title: '发布题目' },
        },
        {
          path: 'grades',
          name: 'teacher-grades',
          component: () => import('../views/teacher/TeacherStudents.vue'),
          meta: { title: '学生成绩' },
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
          path: 'showcase',
          component: () => import('../views/admin/AdminShowcase.vue'),
          meta: { title: '内容管理', role: 'admin' },
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
  document.title = (to.meta.title as string) || '学 · 思 · 践 · 悟 — AI 通识课平台'

  const authStore = useAuthStore()

  if (to.meta.public) return true
  if (to.path === '/') return true

  if (!authStore.isLoggedIn) {
    return '/login'
  }

  // Token 过期检查：过期则清除状态并跳转登录
  if (authStore.token && isTokenExpired(authStore.token)) {
    authStore.logout()
    return '/login'
  }

  // 已登录且需要修改密码：强制跳转到改密页（改密页本身除外）
  if (
    authStore.isLoggedIn &&
    authStore.user?.needs_password_change &&
    to.path !== '/change-password'
  ) {
    return '/change-password'
  }

  // 管理员访问首页时自动跳转到后台
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

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { title: '探 · 练 · 创 · 行 — AI 通识课平台' },
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
      path: '/learn/:chapterId',
      name: 'chapter-detail',
      component: () => import('../views/ChapterView.vue'),
      meta: { title: '章节学习' },
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
      path: '/practice/quiz/:chapterId',
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
          path: 'announcements',
          name: 'teacher-announcements',
          component: () => import('../views/teacher/TeacherAnnouncements.vue'),
          meta: { title: '任务发布' },
        },
        {
          path: 'students',
          name: 'teacher-students',
          component: () => import('../views/teacher/TeacherStudents.vue'),
          meta: { title: '学生数据' },
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
  document.title = (to.meta.title as string) || '探 · 练 · 创 · 行 — AI 通识课平台'

  const authStore = useAuthStore()

  if (to.meta.public) return true
  if (to.path === '/') return true

  if (!authStore.isLoggedIn) {
    return '/login'
  }

  if (to.meta.role === 'teacher' && authStore.user?.role !== 'teacher') {
    return '/'
  }

  return true
})

export default router

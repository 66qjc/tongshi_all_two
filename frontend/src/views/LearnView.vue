<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getCourseList, type Course } from '@/api/course'
import { getLessons } from '@/api/lesson'
import { getCourseProgress } from '@/api/progress'
import { getPublicCourses, type PublicCourse } from '@/api/publicLearning'

interface CourseProgressView {
  lastLessonId: number | null
  percent: number
  lessonCount: number
  completedLessons: number
  totalDuration: number
}

const router = useRouter()
const authStore = useAuthStore()

const courses = ref<(Course | PublicCourse)[]>([])
const publicCourseIds = ref<Set<number>>(new Set())
const loading = ref(true)
const courseHint = ref<string | null>(null)
const progressMap = ref<Record<number, CourseProgressView>>({})
const searchInput = ref('')
const activeKeyword = ref('')

async function loadProgressForCourses(courseList: Course[]) {
  await Promise.all(
    courseList.map(async (course) => {
      try {
        const [progress, lessons] = await Promise.all([
          getCourseProgress(course.id),
          getLessons(course.id),
        ])
        const lastLessonId = progress.last_lesson_id
        const lessonCount = progress.total_lessons || lessons.length
        let percent = Math.round(progress.completion_rate || 0)
        if (!percent && lastLessonId && lessons.length > 0) {
          const index = lessons.findIndex((lesson) => lesson.id === lastLessonId)
          percent = Math.round(((index >= 0 ? index + 1 : 1) / lessons.length) * 100)
        }
        progressMap.value[course.id] = {
          lastLessonId,
          percent,
          lessonCount,
          completedLessons: progress.completed_lessons || 0,
          totalDuration: progress.total_duration || 0,
        }
      } catch {
        progressMap.value[course.id] = {
          lastLessonId: null,
          percent: 0,
          lessonCount: 0,
          completedLessons: 0,
          totalDuration: 0,
        }
      }
    }),
  )
}

function mergeCourses(publicCourses: PublicCourse[], enrolledCourses: Course[]) {
  const merged = new Map<number, Course | PublicCourse>()
  publicCourses.forEach((course) => merged.set(course.id, course))
  enrolledCourses.forEach((course) => merged.set(course.id, course))
  courses.value = Array.from(merged.values())
  publicCourseIds.value = new Set(publicCourses.map((course) => course.id))
}

async function loadCourses(keyword = activeKeyword.value) {
  loading.value = true
  try {
    const trimmed = keyword.trim()
    const publicResult = await getPublicCourses(trimmed || undefined)

    let enrolledCourses: Course[] = []
    let enrolledHint: string | null = null
    if (authStore.isLoggedIn && authStore.user?.role === 'student') {
      const enrolledResult = await getCourseList()
      enrolledCourses = enrolledResult.courses
      enrolledHint = enrolledResult.hint
      if (trimmed) {
        const lower = trimmed.toLowerCase()
        enrolledCourses = enrolledCourses.filter((course) =>
          course.name.toLowerCase().includes(lower),
        )
      }
    }

    mergeCourses(publicResult.courses, enrolledCourses)
    courseHint.value = publicResult.hint || enrolledHint
    progressMap.value = {}
    if (authStore.isLoggedIn && authStore.user?.role === 'student' && enrolledCourses.length > 0) {
      await loadProgressForCourses(enrolledCourses)
    }
  } finally {
    loading.value = false
  }
}

function getProgress(courseId: number): CourseProgressView {
  return (
    progressMap.value[courseId] ?? {
      lastLessonId: null,
      percent: 0,
      lessonCount: 0,
      completedLessons: 0,
      totalDuration: 0,
    }
  )
}

function isPublicCourse(courseId: number) {
  return publicCourseIds.value.has(courseId)
}

function courseLessonCount(course: Course | PublicCourse) {
  return 'lesson_count' in course ? course.lesson_count : getProgress(course.id).lessonCount
}

function courseActionText(course: Course | PublicCourse) {
  const progress = getProgress(course.id)
  if (progress.lastLessonId) return '继续学习'
  if (courseLessonCount(course) > 0) return '开始学习'
  return '查看资料'
}

function courseDescription(course: Course | PublicCourse) {
  return course.description || '这门教程暂未填写简介，可以先进入查看目录、资料和公开课时。'
}

function openCourse(course: Course | PublicCourse) {
  const progress = getProgress(course.id)
  if (progress.lastLessonId) {
    router.push(`/learn/course/${course.id}?lesson_id=${progress.lastLessonId}`)
    return
  }
  router.push(
    courseLessonCount(course) > 0
      ? `/learn/course/${course.id}`
      : `/learn/course/${course.id}?tab=materials`,
  )
}

function runSearch() {
  activeKeyword.value = searchInput.value.trim()
  void loadCourses(activeKeyword.value)
}

function clearSearch() {
  searchInput.value = ''
  activeKeyword.value = ''
  void loadCourses('')
}

onMounted(() => {
  void loadCourses()
})

const emptyText = computed(() => {
  if (activeKeyword.value) {
    return `没有匹配「${activeKeyword.value}」的教程，可以清空搜索后重试。`
  }
  return courseHint.value || '暂无公开教程'
})
</script>

<template>
  <div class="learn-page">
    <section class="learn-hero">
      <div class="container hero-copy">
        <p class="kicker">中国计量大学 · 深度 AI 通识学习平台</p>
        <h1>公开教程</h1>
        <p>
          游客可直接浏览公开课程与学习资料。选一门教程开始阅读；登录后可保存学习进度。
        </p>
      </div>
    </section>

    <main class="courses-section">
      <div class="container">
        <div class="toolbar">
          <div>
            <h2>全部教程</h2>
            <p>一门公开课对应一门教程，可按名称搜索。</p>
          </div>
          <form class="search-box" @submit.prevent="runSearch">
            <input
              v-model="searchInput"
              type="search"
              placeholder="搜索教程名称，例如：人工智能"
              aria-label="搜索教程名称"
            />
            <button type="submit">搜索</button>
          </form>
        </div>

        <p v-if="!authStore.isLoggedIn" class="guest-note">
          登录后可保存学习进度；未登录也可以阅读公开教程和资料。
        </p>

        <div v-if="loading" class="library-empty">教程加载中...</div>

        <div v-else-if="courses.length > 0" class="course-grid">
          <button
            v-for="course in courses"
            :key="course.id"
            type="button"
            class="course-card"
            @click="openCourse(course)"
          >
            <span class="badge">{{ isPublicCourse(course.id) ? '公开' : '已加入' }}</span>
            <h3>{{ course.name }}</h3>
            <p class="desc">{{ courseDescription(course) }}</p>
            <div class="meta-row">
              <span>{{ courseLessonCount(course) }} 课时</span>
              <span>{{ course.material_count || 0 }} 份资料</span>
              <span
                v-if="getProgress(course.id).percent"
                class="progress-text"
              >
                已学 {{ getProgress(course.id).percent }}%
              </span>
            </div>
            <span class="cta">{{ courseActionText(course) }}</span>
          </button>
        </div>

        <div v-else class="library-empty">
          <p>{{ emptyText }}</p>
          <button
            v-if="activeKeyword"
            type="button"
            class="clear-search"
            @click="clearSearch"
          >
            清空搜索
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.learn-page {
  padding-top: 60px;
  color: var(--color-text);
  background:
    radial-gradient(circle at 12% 20%, rgba(45, 106, 122, 0.08), transparent 28%),
    linear-gradient(180deg, #f4f0e6 0%, var(--color-bg) 42%, var(--color-bg) 100%);
}

.learn-hero {
  padding: 48px 0 28px;
  border-bottom: 1px solid var(--color-border-light);
  background:
    radial-gradient(circle at 12% 20%, rgba(45, 106, 122, 0.08), transparent 28%),
    linear-gradient(180deg, #f4f0e6 0%, var(--color-bg) 100%);
}

.hero-copy {
  max-width: 720px;
}

.kicker {
  margin: 0 0 10px;
  color: var(--color-learn);
  font-size: 0.8rem;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.learn-hero h1 {
  margin: 0 0 12px;
  font-size: clamp(1.8rem, 3vw, 2.35rem);
  line-height: 1.2;
  font-weight: 900;
}

.learn-hero p {
  margin: 0;
  max-width: 640px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  text-wrap: pretty;
}

.courses-section {
  padding: 28px 0 72px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.toolbar h2 {
  margin: 0;
  font-size: 1.15rem;
}

.toolbar p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.search-box {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: min(360px, 100%);
  padding: 8px 10px 8px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-card);
}

.search-box input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text);
  min-width: 0;
}

.search-box button {
  padding: 8px 14px;
  border: none;
  border-radius: 999px;
  background: var(--color-learn);
  color: #fff;
  font-weight: 700;
  font-size: 0.86rem;
  cursor: pointer;
}

.guest-note {
  margin: 0 0 18px;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.course-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
  box-shadow: 0 10px 30px rgba(24, 24, 44, 0.05);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    transform 160ms ease,
    box-shadow 160ms ease;
}

.course-card:hover {
  border-color: rgba(45, 106, 122, 0.35);
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(24, 24, 44, 0.07);
}

.course-card:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.badge {
  display: inline-flex;
  width: fit-content;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--color-learn-bg);
  color: var(--color-learn);
  font-size: 0.72rem;
  font-weight: 800;
}

.course-card h3 {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.35;
  color: var(--color-text);
}

.desc {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.9em;
  text-wrap: pretty;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.progress-text {
  color: var(--color-learn);
  font-weight: 700;
}

.cta {
  margin-top: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-weight: 700;
  font-size: 0.9rem;
}

.library-empty {
  padding: 56px 16px;
  color: var(--color-text-muted);
  text-align: center;
  font-size: 0.94rem;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
}

.library-empty p {
  margin: 0;
}

.clear-search {
  margin-top: 14px;
  padding: 8px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg);
  color: var(--color-learn);
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 960px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .learn-hero {
    padding: 36px 0 22px;
  }

  .search-box {
    min-width: 100%;
  }

  .courses-section {
    padding-bottom: 48px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .course-card {
    transition: none;
  }

  .course-card:hover {
    transform: none;
  }
}
</style>

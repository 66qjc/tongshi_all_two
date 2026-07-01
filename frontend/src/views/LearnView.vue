<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCourseList, type Course } from '@/api/course'
import { getLessons } from '@/api/lesson'
import { getCourseProgress } from '@/api/progress'

interface CourseProgressView {
  lastLessonId: number | null
  percent: number
  lessonCount: number
}

const router = useRouter()
const courses = ref<Course[]>([])
const loading = ref(true)
const keyword = ref('')
const courseHint = ref<string | null>(null)
const progressMap = ref<Record<number, CourseProgressView>>({})

async function loadProgressForCourses(courseList: Course[]) {
  await Promise.all(
    courseList.map(async (course) => {
      try {
        const [progress, lessons] = await Promise.all([
          getCourseProgress(course.id),
          getLessons(course.id),
        ])
        const lastLessonId = progress.last_lesson_id
        let percent = 0
        if (lastLessonId && lessons.length > 0) {
          const index = lessons.findIndex((l) => l.id === lastLessonId)
          percent = Math.round(((index >= 0 ? index + 1 : 1) / lessons.length) * 100)
        }
        progressMap.value[course.id] = { lastLessonId, percent, lessonCount: lessons.length }
      } catch {
        progressMap.value[course.id] = { lastLessonId: null, percent: 0, lessonCount: 0 }
      }
    }),
  )
}

async function loadCourses() {
  loading.value = true
  try {
    const result = await getCourseList(keyword.value.trim() || undefined)
    courses.value = result.courses
    courseHint.value = result.hint
    progressMap.value = {}
    if (result.courses.length > 0) {
      await loadProgressForCourses(result.courses)
    }
  } finally {
    loading.value = false
  }
}

function getProgress(courseId: number): CourseProgressView {
  return progressMap.value[courseId] ?? { lastLessonId: null, percent: 0, lessonCount: 0 }
}

function openCourse(course: Course) {
  const progress = getProgress(course.id)
  if (progress.lastLessonId) {
    router.push(`/learn/course/${course.id}?lesson_id=${progress.lastLessonId}`)
    return
  }
  router.push(progress.lessonCount > 0 ? `/learn/course/${course.id}` : `/learn/course/${course.id}?tab=materials`)
}

function courseActionText(courseId: number) {
  const progress = getProgress(courseId)
  if (progress.lastLessonId) return '继续学习'
  return progress.lessonCount > 0 ? '开始学习' : '查看资料'
}

onMounted(loadCourses)

const filteredCourses = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return courses.value
  return courses.value.filter(c => c.name.toLowerCase().includes(q))
})

const emptyText = computed(() => {
  if (keyword.value.trim()) return '未找到匹配的课程'
  return courseHint.value || '暂无课程内容'
})
</script>

<template>
  <div class="learn-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <img
              src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png"
              alt="AI 通识课平台标识"
              width="40"
              height="40"
              class="hero-icon-image"
            />
          </div>
          <h1>学 · 积累知识</h1>
          <p>浏览老师为你选择的课程资料，按自己的节奏学习。</p>
        </div>
      </div>
    </section>

    <section class="courses-section">
      <div class="container">
        <div class="search-bar">
          <input
            v-model="keyword"
            type="text"
            placeholder="搜索课程名称"
            @keyup.enter="loadCourses"
          />
          <button @click="loadCourses">搜索</button>
        </div>
        <div v-if="loading" class="empty-state">课程加载中...</div>
        <div v-else-if="filteredCourses.length > 0" class="course-grid">
          <div
            v-for="course in filteredCourses"
            :key="course.id"
            class="course-card"
          >
            <h3>{{ course.name }}</h3>
            <p>{{ course.material_count }} 份学习资料 · {{ course.question_count }} 道练习题</p>
            <div v-if="getProgress(course.id).percent" class="course-progress">
              <div class="progress-track">
                <div
                  class="progress-fill"
                  :style="{ width: `${getProgress(course.id).percent}%` }"
                ></div>
              </div>
              <span class="progress-text">已学 {{ getProgress(course.id).percent }}%</span>
            </div>
            <div class="card-links">
              <button class="card-link primary" @click="openCourse(course)">
                {{ courseActionText(course.id) }}
              </button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">{{ emptyText }}</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.learn-page {
  padding-top: 60px;
}

.page-hero {
  padding: var(--space-3xl) 0 var(--space-2xl);
  background: var(--color-learn-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.hero-inner {
  text-align: center;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
  box-shadow: 0 4px 14px rgba(45, 106, 122, 0.2);
}

.hero-icon-image {
  display: block;
  width: 40px;
  height: 40px;
  object-fit: contain;
}

.hero-inner h1 {
  font-family: var(--font-serif);
  font-size: 1.8rem;
  font-weight: 900;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  letter-spacing: 0.05em;
}

.hero-inner p {
  font-size: 0.92rem;
  color: var(--color-text-secondary);
}

.courses-section {
  padding: var(--space-2xl) 0 var(--space-3xl);
}

.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: var(--space-xl);
}

.search-bar input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
}

.search-bar button {
  padding: 10px 20px;
  background: var(--color-learn);
  color: white;
  border-radius: var(--radius-md);
  font-weight: 700;
  font-size: 0.85rem;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-lg);
}

.course-card {
  text-align: left;
  display: flex;
  flex-direction: column;
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
  position: relative;
  overflow: hidden;
}

.course-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  border-color: rgba(45, 106, 122, 0.24);
}

.course-card h3 {
  font-family: var(--font-serif);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  letter-spacing: 0.03em;
}

.course-card p {
  color: var(--color-text-secondary);
  font-size: 0.88rem;
  margin-bottom: var(--space-lg);
}

.card-links {
  display: flex;
  gap: var(--space-sm);
  margin-top: auto;
}

.card-link {
  padding: 6px 18px;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.card-link.primary {
  color: white;
  background: var(--color-learn);
}

.card-link.primary:hover {
  opacity: 0.9;
}

.course-progress {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

.progress-track {
  flex: 1;
  height: 6px;
  background: var(--color-border-light);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-learn);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.78rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>

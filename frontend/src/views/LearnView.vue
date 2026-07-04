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
}

const router = useRouter()
const authStore = useAuthStore()

const courses = ref<(Course | PublicCourse)[]>([])
const publicCourseIds = ref<Set<number>>(new Set())
const selectedCourseId = ref<number | null>(null)
const loading = ref(true)
const courseHint = ref<string | null>(null)
const progressMap = ref<Record<number, CourseProgressView>>({})

const spineAccents = [
  'oklch(0.35 0.07 178)',
  'oklch(0.42 0.08 205)',
  'oklch(0.38 0.055 146)',
  'oklch(0.33 0.045 222)',
  'oklch(0.46 0.075 164)',
  'oklch(0.40 0.05 192)',
]

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
          const index = lessons.findIndex((lesson) => lesson.id === lastLessonId)
          percent = Math.round(((index >= 0 ? index + 1 : 1) / lessons.length) * 100)
        }
        progressMap.value[course.id] = { lastLessonId, percent, lessonCount: lessons.length }
      } catch {
        progressMap.value[course.id] = { lastLessonId: null, percent: 0, lessonCount: 0 }
      }
    }),
  )
}

function syncSelectedCourse(courseList: (Course | PublicCourse)[]) {
  if (!courseList.length) {
    selectedCourseId.value = null
    return
  }
  const stillVisible = courseList.some((course) => course.id === selectedCourseId.value)
  const firstCourse = courseList[0]
  if (!stillVisible && firstCourse) selectedCourseId.value = firstCourse.id
}

function mergeCourses(publicCourses: PublicCourse[], enrolledCourses: Course[]) {
  const merged = new Map<number, Course | PublicCourse>()
  publicCourses.forEach((course) => merged.set(course.id, course))
  enrolledCourses.forEach((course) => merged.set(course.id, course))
  const nextCourses = Array.from(merged.values())
  courses.value = nextCourses
  publicCourseIds.value = new Set(publicCourses.map((course) => course.id))
  syncSelectedCourse(nextCourses)
}

async function loadCourses() {
  loading.value = true
  try {
    const publicResult = await getPublicCourses()

    let enrolledCourses: Course[] = []
    let enrolledHint: string | null = null
    if (authStore.isLoggedIn && authStore.user?.role === 'student') {
      const enrolledResult = await getCourseList()
      enrolledCourses = enrolledResult.courses
      enrolledHint = enrolledResult.hint
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
  return progressMap.value[courseId] ?? { lastLessonId: null, percent: 0, lessonCount: 0 }
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
  return course.description || '这门课程暂未填写简介，可以先进入课程查看目录、资料和公开课时。'
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

function selectCourse(course: Course | PublicCourse) {
  selectedCourseId.value = course.id
}

function openSelectedCourse() {
  if (!selectedCourse.value) return
  openCourse(selectedCourse.value)
}

function spineStyle(index: number) {
  return {
    '--spine-accent': spineAccents[index % spineAccents.length],
    '--spine-rise': `${(index % 3) * 8}px`,
  } as Record<string, string>
}

onMounted(loadCourses)

const selectedCourse = computed(() => {
  return (
    courses.value.find((course) => course.id === selectedCourseId.value) ??
    courses.value[0] ??
    null
  )
})

const selectedProgress = computed(() =>
  selectedCourse.value ? getProgress(selectedCourse.value.id) : null,
)

const totalLessonCount = computed(() =>
  courses.value.reduce((sum, course) => sum + courseLessonCount(course), 0),
)

const totalMaterialCount = computed(() =>
  courses.value.reduce((sum, course) => sum + (course.material_count || 0), 0),
)

const emptyText = computed(() => courseHint.value || '暂无公开课程内容')
</script>

<template>
  <div class="learn-page summer-ink-theme">
    <section class="library-hero">
      <div class="container library-shell">
        <div class="library-copy">
          <p class="library-kicker">中国计量大学 · 深度 AI 通识学习平台</p>
          <h1>AI 通识公开学习馆</h1>
          <p>
            选择一门课程，查看简介、课时和学习资料，再进入完整阅读页。游客可以直接浏览公开课程，登录后继续保存学习进度。
          </p>
        </div>

        <aside class="library-facts" aria-label="学习馆概览">
          <div>
            <strong>{{ courses.length }}</strong>
            <span>门课程</span>
          </div>
          <div>
            <strong>{{ totalLessonCount }}</strong>
            <span>个课时</span>
          </div>
          <div>
            <strong>{{ totalMaterialCount }}</strong>
            <span>份资料</span>
          </div>
        </aside>
      </div>
    </section>

    <main class="courses-section">
      <div class="container">
        <div class="catalog-toolbar">
          <div>
            <p class="section-kicker">公开课程书架</p>
            <h2>选一本书，翻开它</h2>
          </div>
        </div>

        <p v-if="!authStore.isLoggedIn" class="guest-note">
          登录后可保存学习进度；未登录也可以阅读公开课程和资料。
        </p>

        <div v-if="loading" class="library-empty">书架整理中...</div>
        <section v-else-if="courses.length > 0" class="ink-learning-stage">
          <aside class="course-spine-panel" aria-label="课程书架">
            <div class="spine-panel-heading">
              <span>课程书架</span>
              <small>选择一门课程后，可在右侧查看简介和进入阅读页。</small>
            </div>
            <div class="course-spine-rail" role="list">
              <button
                v-for="(course, index) in courses"
                :key="course.id"
                type="button"
                class="course-spine"
                :class="{ 'is-active': selectedCourse?.id === course.id }"
                :style="spineStyle(index)"
                role="listitem"
                @click="selectCourse(course)"
              >
                <span class="course-spine-badge">{{ isPublicCourse(course.id) ? '公开' : '已加入' }}</span>
                <strong class="course-spine-title">{{ course.name }}</strong>
                <small>{{ courseLessonCount(course) }} 课时 · {{ course.material_count || 0 }} 资料</small>
              </button>
            </div>
          </aside>

          <article v-if="selectedCourse" class="course-book-panel" aria-live="polite">
            <div class="selected-book-meta">
              <span>{{ isPublicCourse(selectedCourse.id) ? '公开课程' : '我的课程' }}</span>
              <strong>{{ courseActionText(selectedCourse) }}</strong>
            </div>

            <div class="ink-open-book">
              <section class="book-page ink-book-cover">
                <p class="book-eyebrow">Course Book</p>
                <h3>{{ selectedCourse.name }}</h3>
                <dl>
                  <div>
                    <dt>课时</dt>
                    <dd>{{ courseLessonCount(selectedCourse) }}</dd>
                  </div>
                  <div>
                    <dt>资料</dt>
                    <dd>{{ selectedCourse.material_count || 0 }}</dd>
                  </div>
                  <div v-if="selectedProgress && selectedProgress.percent">
                    <dt>进度</dt>
                    <dd>{{ selectedProgress.percent }}%</dd>
                  </div>
                </dl>
              </section>

              <section class="book-page ink-book-content">
                <p class="book-eyebrow">课程简介</p>
                <h3>{{ selectedCourse.name }}</h3>
                <p class="book-summary">{{ courseDescription(selectedCourse) }}</p>

                <div
                  v-if="selectedProgress && selectedProgress.percent"
                  class="course-progress"
                  aria-label="课程学习进度"
                >
                  <div class="progress-track">
                    <div
                      class="progress-fill"
                      :style="{ width: `${selectedProgress.percent}%` }"
                    ></div>
                  </div>
                  <span>已学 {{ selectedProgress.percent }}%</span>
                </div>

                <div class="book-actions">
                  <button type="button" class="primary-action" @click="openSelectedCourse">
                    {{ courseActionText(selectedCourse) }}
                  </button>
                  <button
                    type="button"
                    class="secondary-action"
                    @click="router.push('/')"
                  >
                    返回首页
                  </button>
                </div>
              </section>
            </div>
          </article>
        </section>
        <div v-else class="library-empty">{{ emptyText }}</div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.learn-page {
  --ink-text: oklch(0.2 0.026 198);
  --ink-muted: oklch(0.48 0.018 202);
  --paper-bg: oklch(0.975 0.012 103);
  --paper-surface: oklch(0.99 0.007 108);
  --paper-line: oklch(0.86 0.018 104);
  --wash-green: oklch(0.38 0.072 170);
  --water-blue: oklch(0.58 0.07 210);
  --spine-accent: var(--wash-green);
  --library-ink: var(--ink-text);
  --library-muted: var(--ink-muted);
  --library-paper: var(--paper-bg);
  --library-surface: var(--paper-surface);
  --library-line: var(--paper-line);
  --library-green: var(--wash-green);
  padding-top: 60px;
  color: var(--library-ink);
  background:
    radial-gradient(circle at 78% 12%, color-mix(in oklch, var(--water-blue), transparent 82%), transparent 28%),
    radial-gradient(circle at 12% 28%, color-mix(in oklch, var(--wash-green), transparent 86%), transparent 32%),
    linear-gradient(180deg, oklch(0.96 0.018 102) 0%, var(--paper-bg) 48%, oklch(0.985 0.008 118) 100%);
}

.library-hero {
  padding: 72px 0 34px;
  border-bottom: 1px solid var(--library-line);
  background:
    radial-gradient(circle at 6% 20%, color-mix(in oklch, var(--wash-green), transparent 84%), transparent 26%),
    linear-gradient(90deg, color-mix(in oklch, var(--water-blue), transparent 91%), transparent 54%),
    var(--library-paper);
}

.library-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 48px;
  align-items: end;
}

.library-copy {
  max-width: 760px;
}

.library-kicker,
.section-kicker,
.book-eyebrow {
  margin: 0 0 10px;
  color: var(--library-green);
  font-size: 0.8rem;
  font-weight: 900;
}

.library-copy h1 {
  margin: 0;
  color: var(--library-ink);
  font-size: 2.45rem;
  line-height: 1.18;
  font-weight: 900;
  letter-spacing: 0;
}

.library-copy p:last-child {
  max-width: 680px;
  margin: 18px 0 0;
  color: var(--library-muted);
  font-size: 1rem;
  line-height: 1.85;
}

.library-facts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  overflow: hidden;
  border: 1px solid var(--library-line);
  border-radius: 8px;
  background: var(--library-line);
  box-shadow: 0 18px 40px rgba(30, 43, 42, 0.08);
}

.library-facts div {
  display: grid;
  gap: 4px;
  min-height: 96px;
  align-content: center;
  justify-items: center;
  background: var(--library-surface);
}

.library-facts strong {
  color: var(--library-green);
  font-size: 1.5rem;
  line-height: 1;
}

.library-facts span {
  color: var(--library-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.courses-section {
  padding: 30px 0 86px;
}

.catalog-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.catalog-toolbar h2 {
  margin: 0;
  color: var(--library-ink);
  font-size: 1.34rem;
  font-weight: 900;
}

.primary-action,
.secondary-action {
  height: 42px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 0.86rem;
  font-weight: 900;
  transition:
    transform 160ms var(--ease-out),
    box-shadow 160ms var(--ease-out),
    border-color 160ms var(--ease-out);
}

.primary-action {
  color: var(--color-bg-card);
  background: var(--library-green);
  box-shadow: 0 10px 22px rgba(21, 93, 86, 0.16);
}

.secondary-action {
  color: var(--library-green);
  border: 1px solid rgba(21, 93, 86, 0.22);
  background: rgba(21, 93, 86, 0.07);
  box-shadow: none;
}

.primary-action:hover,
.secondary-action:hover {
  transform: translateY(-1px);
}

.guest-note {
  margin: 0 0 22px;
  color: var(--library-muted);
  font-size: 0.86rem;
}

.ink-learning-stage {
  display: grid;
  grid-template-columns: minmax(340px, 0.42fr) minmax(0, 1fr);
  gap: 28px;
  align-items: stretch;
}

.course-spine-panel {
  position: relative;
  min-height: 560px;
  padding: 18px 18px 30px;
  border: 1px solid color-mix(in oklch, var(--wash-green), white 72%);
  border-radius: 8px;
  background:
    radial-gradient(circle at 24% 16%, color-mix(in oklch, var(--water-blue), transparent 78%), transparent 30%),
    radial-gradient(circle at 82% 72%, color-mix(in oklch, var(--wash-green), transparent 82%), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.66), rgba(255, 255, 255, 0.36)),
    var(--paper-bg);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.72), 0 24px 52px rgba(36, 62, 58, 0.12);
}

.course-spine-panel::before {
  content: '';
  position: absolute;
  inset: 18px;
  border-radius: 7px;
  background:
    linear-gradient(115deg, transparent 0 40%, color-mix(in oklch, var(--water-blue), transparent 90%) 42%, transparent 58%),
    radial-gradient(ellipse at 18% 82%, rgba(28, 87, 80, 0.08), transparent 36%);
  pointer-events: none;
}

.spine-panel-heading {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 18px;
  color: var(--ink-text);
}

.spine-panel-heading span {
  font-weight: 900;
}

.spine-panel-heading small {
  max-width: 170px;
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.5;
  text-align: right;
}

.course-spine-rail {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 9px;
  align-items: end;
  min-height: 392px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 34px 4px 30px;
  scroll-snap-type: x proximity;
}

.course-spine-rail::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 12px;
  height: 2px;
  background: linear-gradient(90deg, transparent, color-mix(in oklch, var(--wash-green), transparent 42%), transparent);
}

.course-spine {
  position: relative;
  z-index: 1;
  display: flex;
  flex: 0 0 72px;
  min-width: 72px;
  min-height: calc(318px + var(--spine-rise));
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 10px 16px;
  border: 1px solid color-mix(in oklch, var(--spine-accent), black 12%);
  border-radius: 6px 6px 3px 3px;
  color: oklch(0.98 0.006 96);
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.18), transparent 22%, rgba(0, 0, 0, 0.08) 100%),
    linear-gradient(180deg, color-mix(in oklch, var(--spine-accent), white 10%), var(--spine-accent));
  box-shadow: 8px 14px 20px rgba(27, 50, 48, 0.16);
  scroll-snap-align: start;
  text-align: center;
  transform-origin: bottom center;
  transition:
    transform 230ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 180ms var(--ease-out),
    filter 180ms var(--ease-out);
}

.course-spine::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 10px;
  width: 1px;
  background: rgba(255, 255, 255, 0.32);
}

.course-spine:hover,
.course-spine.is-active {
  transform: translateY(-22px) rotateZ(-1.2deg);
  box-shadow: 14px 22px 32px rgba(24, 48, 46, 0.24);
  filter: saturate(1.08);
}

.course-spine:focus-visible {
  outline: 3px solid color-mix(in oklch, var(--water-blue), white 20%);
  outline-offset: 3px;
}

.course-spine-badge {
  align-self: flex-start;
  padding: 3px 6px;
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 0.7rem;
  font-weight: 900;
}

.course-spine-title {
  display: block;
  align-self: center;
  max-height: 210px;
  overflow: hidden;
  color: inherit;
  font-size: 1rem;
  line-height: 1.35;
  font-weight: 900;
  letter-spacing: 0;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.course-spine small {
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.7rem;
  font-weight: 800;
  line-height: 1.45;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.course-book-panel {
  display: grid;
  gap: 18px;
  min-width: 0;
  padding: 22px;
  border: 1px solid var(--library-line);
  border-radius: 8px;
  background:
    radial-gradient(circle at 94% 8%, color-mix(in oklch, var(--water-blue), transparent 86%), transparent 26%),
    linear-gradient(135deg, rgba(33, 91, 85, 0.06), transparent 36%),
    var(--library-surface);
  box-shadow: 0 22px 48px rgba(31, 45, 43, 0.12);
}

.selected-book-meta {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.selected-book-meta span {
  color: var(--library-green);
  font-size: 0.8rem;
  font-weight: 900;
}

.selected-book-meta strong {
  color: var(--library-muted);
  font-size: 0.86rem;
}

.ink-open-book {
  display: grid;
  grid-template-columns: minmax(220px, 0.85fr) minmax(0, 1.15fr);
  min-height: 448px;
  overflow: hidden;
  border: 1px solid var(--paper-line);
  border-radius: 8px;
  background:
    radial-gradient(circle at 10% 8%, color-mix(in oklch, var(--water-blue), transparent 88%), transparent 24%),
    var(--paper-bg);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.8);
}

.book-page {
  padding: 32px;
}

.ink-book-cover {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: oklch(0.97 0.008 104);
  background:
    radial-gradient(circle at 28% 18%, color-mix(in oklch, var(--water-blue), transparent 62%), transparent 32%),
    linear-gradient(180deg, color-mix(in oklch, var(--wash-green), white 6%), var(--wash-green));
}

.ink-book-cover h3,
.ink-book-content h3 {
  margin: 0;
  font-size: 1.52rem;
  line-height: 1.35;
  font-weight: 900;
  letter-spacing: 0;
}

.ink-book-cover .book-eyebrow {
  color: rgba(255, 255, 255, 0.72);
}

.ink-book-cover dl {
  display: grid;
  gap: 10px;
  margin: 32px 0 0;
}

.ink-book-cover dl div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.ink-book-cover dt {
  color: rgba(255, 255, 255, 0.68);
  font-size: 0.8rem;
  font-weight: 800;
}

.ink-book-cover dd {
  margin: 0;
  color: inherit;
  font-weight: 900;
}

.ink-book-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
  color: var(--library-ink);
  background:
    linear-gradient(90deg, rgba(23, 64, 60, 0.06), transparent 5%),
    radial-gradient(circle at 92% 14%, color-mix(in oklch, var(--water-blue), transparent 90%), transparent 24%),
    var(--paper-surface);
}

.book-summary {
  max-width: 64ch;
  margin: 18px 0 0;
  color: var(--library-muted);
  line-height: 1.85;
}

.course-progress {
  display: grid;
  gap: 8px;
  margin-top: 24px;
}

.progress-track {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--library-line);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--library-green);
  transition: width 240ms var(--ease-out);
}

.course-progress span {
  color: var(--library-muted);
  font-size: 0.8rem;
  font-weight: 800;
}

.book-actions {
  display: flex;
  gap: 10px;
  margin-top: auto;
  padding-top: 28px;
  flex-wrap: wrap;
}

.library-empty {
  padding: 72px 0;
  color: var(--library-muted);
  text-align: center;
  font-size: 0.94rem;
}

@media (max-width: 1180px) {
  .ink-learning-stage {
    grid-template-columns: 1fr;
  }

  .course-spine-panel {
    min-height: auto;
  }
}

@media (max-width: 900px) {
  .library-shell,
  .catalog-toolbar,
  .ink-open-book {
    grid-template-columns: 1fr;
  }

  .library-hero {
    padding: 48px 0 28px;
  }

  .library-copy h1 {
    font-size: 2rem;
  }

  .library-facts {
    max-width: 420px;
  }

  .course-book-panel {
    padding: 16px;
  }

  .ink-open-book {
    min-height: 0;
    overflow: visible;
  }
}

@media (max-width: 640px) {
  .courses-section {
    padding-bottom: 58px;
  }

  .course-spine-panel {
    padding: 14px;
  }

  .spine-panel-heading {
    display: grid;
  }

  .spine-panel-heading small {
    max-width: none;
    text-align: left;
  }

  .course-spine-rail {
    min-height: 328px;
    padding-top: 24px;
  }

  .course-spine {
    flex-basis: 68px;
    min-width: 68px;
    min-height: 286px;
  }

  .course-spine:hover,
  .course-spine.is-active {
    transform: translateY(-4px);
  }

  .book-page {
    padding: 24px 20px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .primary-action,
  .secondary-action,
  .course-spine,
  .progress-fill {
    transition: none;
  }

  .primary-action:hover,
  .secondary-action:hover,
  .course-spine:hover,
  .course-spine.is-active {
    transform: none;
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getCourseDetail, type CourseDetail } from '@/api/course'
import { getCourseContents, type Material } from '@/api/material'
import { getLessons, type Lesson } from '@/api/lesson'
import { getCourseProgress, saveCourseProgress } from '@/api/progress'
import CourseToc from '@/components/lesson/CourseToc.vue'
import LessonReader from '@/components/lesson/LessonReader.vue'
import PrevNextNav from '@/components/lesson/PrevNextNav.vue'
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const courseId = computed(() => Number(route.params.courseId))

const course = ref<CourseDetail | null>(null)
const lessons = ref<Lesson[]>([])
const materials = ref<Material[]>([])
const loading = ref(true)
const currentLessonId = ref<number | null>(null)
const initialTab = route.query.tab === 'materials' ? 'materials' : 'lessons'
const activeTab = ref<'lessons' | 'materials'>(initialTab)
const sidebarOpen = ref(false)

const isTeacherOrAdmin = computed(() =>
  ['teacher', 'admin'].includes(authStore.user?.role || ''),
)

const visibleLessons = computed(() => {
  if (isTeacherOrAdmin.value) return lessons.value
  return lessons.value.filter((l) => l.status === 'published')
})

const currentLesson = computed(
  () => visibleLessons.value.find((l) => l.id === currentLessonId.value) || null,
)

const currentLessonIndex = computed(() =>
  visibleLessons.value.findIndex((l) => l.id === currentLessonId.value),
)

const prevLesson = computed<Lesson | null>(() => {
  const idx = currentLessonIndex.value
  return idx > 0 ? (visibleLessons.value[idx - 1] ?? null) : null
})

const nextLesson = computed<Lesson | null>(() => {
  const idx = currentLessonIndex.value
  return idx >= 0 && idx < visibleLessons.value.length - 1
    ? (visibleLessons.value[idx + 1] ?? null)
    : null
})

const progressPercent = computed(() => {
  if (!visibleLessons.value.length) return 0
  if (currentLessonIndex.value < 0) return 0
  return Math.round(((currentLessonIndex.value + 1) / visibleLessons.value.length) * 100)
})

function selectLesson(lesson: Lesson) {
  if (lesson.id === currentLessonId.value) {
    sidebarOpen.value = false
    return
  }
  currentLessonId.value = lesson.id
  sidebarOpen.value = false
  saveProgressAndUrl(lesson.id)
}

function goPrev() {
  if (prevLesson.value) selectLesson(prevLesson.value)
}

function goNext() {
  if (nextLesson.value) selectLesson(nextLesson.value)
}

async function saveProgressAndUrl(lessonId: number) {
  try {
    await saveCourseProgress(courseId.value, lessonId)
  } catch {
    // 进度保存失败不影响主流程
  }
  router.replace({ query: { ...route.query, lesson_id: String(lessonId) } })
}

async function loadData() {
  loading.value = true
  try {
    const [detail, lessonList, materialList] = await Promise.all([
      getCourseDetail(courseId.value),
      getLessons(courseId.value),
      getCourseContents(courseId.value),
    ])
    course.value = detail
    lessons.value = lessonList
    materials.value = materialList
    if (!visibleLessons.value.length && materialList.length > 0) {
      activeTab.value = 'materials'
    }

    const queryLessonId = route.query.lesson_id ? Number(route.query.lesson_id) : null
    const targetFromQuery = queryLessonId
      ? visibleLessons.value.find((l) => l.id === queryLessonId)
      : null

    if (targetFromQuery) {
      currentLessonId.value = targetFromQuery.id
    } else {
      try {
        const progress = await getCourseProgress(courseId.value)
        const targetFromProgress = progress.last_lesson_id
          ? visibleLessons.value.find((l) => l.id === progress.last_lesson_id)
          : null
        currentLessonId.value = targetFromProgress?.id ?? visibleLessons.value[0]?.id ?? null
      } catch {
        currentLessonId.value = visibleLessons.value[0]?.id ?? null
      }
    }
  } catch {
    ElMessage.error('课程加载失败，请检查网络后刷新重试')
  } finally {
    loading.value = false
  }
}

const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)

function previewMaterial(material: Material) {
  selectedMaterial.value = material
  previewVisible.value = true
}

onMounted(loadData)
</script>

<template>
  <div class="course-detail-page">
    <div class="course-shell" :class="{ 'materials-mode': activeTab === 'materials' }">
      <!-- 课时学习页 -->
      <template v-if="activeTab === 'lessons'">
        <div
          class="sidebar-overlay"
          :class="{ open: sidebarOpen }"
          @click="sidebarOpen = false"
        ></div>
        <aside class="sidebar" :class="{ open: sidebarOpen }">
            <div class="mobile-sidebar-header">
              <span>课程目录</span>
              <button class="close-sidebar" @click="sidebarOpen = false">✕</button>
            </div>
            <CourseToc
              :lessons="visibleLessons"
              :active-lesson-id="currentLessonId"
              @select="selectLesson"
            />
        </aside>
      </template>

      <div class="course-main-panel">
        <section class="course-hero">
          <div class="container hero-container">
            <div class="hero-top">
              <button class="back-btn" @click="router.push('/learn')">
                <span class="back-arrow">←</span>
                <span>返回课程列表</span>
              </button>
              <div v-if="course" class="course-heading">
                <h1>{{ course.name }}</h1>
                <p class="course-desc">{{ course.description || '本课程暂无详细介绍。' }}</p>
              </div>
            </div>

            <div class="hero-bottom">
              <div class="tab-bar">
                <button
                  :class="['tab-btn', { active: activeTab === 'lessons' }]"
                  @click="activeTab = 'lessons'"
                >
                  课时
                </button>
                <button
                  :class="['tab-btn', { active: activeTab === 'materials' }]"
                  @click="activeTab = 'materials'"
                >
                  资料
                </button>
              </div>

              <div v-if="activeTab === 'lessons' && visibleLessons.length" class="progress-badge">
                <span>学习进度</span>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
                </div>
                <span>{{ progressPercent }}%</span>
              </div>
            </div>
          </div>
        </section>

        <div v-if="loading" class="loading-state">
          <el-skeleton :rows="10" animated />
        </div>

        <template v-else>
          <template v-if="activeTab === 'lessons'">
          <main class="main-content">
            <button
              v-if="!sidebarOpen"
              class="menu-toggle"
              @click="sidebarOpen = true"
            >
              <span>☰</span>
              <span>目录</span>
            </button>
            <div class="content-wrapper">
              <LessonReader
                :lesson="currentLesson"
                :materials="materials"
                @preview="previewMaterial"
              />
              <PrevNextNav
                :prev-lesson="prevLesson"
                :next-lesson="nextLesson"
                @prev="goPrev"
                @next="goNext"
              />
            </div>
          </main>
          </template>

          <!-- 课程资料页 -->
          <template v-else>
            <main class="materials-content">
              <div class="container">
                <div
                  v-for="(stage, index) in course?.stages || []"
                  :key="stage.id"
                  class="stage-section"
                >
                  <h2>
                    <span class="stage-badge">阶段 {{ index + 1 }}</span>
                    {{ stage.name }}
                  </h2>
                  <div v-if="stage.materials.length > 0" class="material-grid">
                    <MaterialRichCard
                      v-for="m in stage.materials"
                      :key="m.id"
                      :material="m"
                      @preview="previewMaterial"
                    />
                  </div>
                  <div v-else class="stage-empty">该阶段暂无资料</div>
                </div>

                <div
                  v-if="course?.uncategorized_materials.length"
                  class="stage-section"
                >
                  <h2><span class="stage-badge">其他</span>未分类资料</h2>
                  <div class="material-grid">
                    <MaterialRichCard
                      v-for="m in course.uncategorized_materials"
                      :key="m.id"
                      :material="m"
                      @preview="previewMaterial"
                    />
                  </div>
                </div>

                <div
                  v-if="!course?.stages?.length && !course?.uncategorized_materials?.length"
                  class="empty-state"
                >
                  该课程暂无学习资料。
                </div>
              </div>
            </main>
          </template>
        </template>
      </div>
    </div>

    <MaterialPreviewDialog v-model:visible="previewVisible" :material="selectedMaterial" />
  </div>
</template>

<style scoped>
.course-detail-page {
  --course-sidebar-width: 260px;
  --app-header-height: 60px;
  min-height: 100vh;
  padding-top: var(--app-header-height);
  background: var(--color-bg);
}

.course-shell {
  display: flex;
  align-items: flex-start;
  min-height: calc(100vh - var(--app-header-height));
}

.course-main-panel {
  flex: 1;
  min-width: 0;
}

.course-hero {
  padding: 2.5rem 0 0;
  background: var(--color-learn-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.hero-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 1rem;
  padding: 8px 14px;
  color: var(--color-learn);
  background: rgba(45, 106, 122, 0.08);
  border: 1px solid rgba(45, 106, 122, 0.18);
  border-radius: var(--radius-full);
  font-weight: 700;
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(45, 106, 122, 0.14);
  transform: translateX(-2px);
}

.back-arrow {
  font-size: 1.15rem;
  line-height: 1;
}

.course-heading h1 {
  font-size: 1.9rem;
  font-weight: 800;
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
  color: var(--color-text);
  margin-bottom: 0.6rem;
}

.course-desc {
  color: var(--color-text-secondary);
  max-width: 720px;
  line-height: 1.8;
  margin: 0;
}

.hero-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.tab-bar {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.tab-btn {
  padding: 0.75rem 1.25rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: var(--color-text);
}

.tab-btn.active {
  color: var(--color-learn);
  border-bottom-color: var(--color-learn);
}

.progress-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--color-primary-light);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.progress-bar {
  width: 80px;
  height: 6px;
  background: rgba(45, 106, 122, 0.2);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
  transition: width 0.4s ease;
}

.loading-state {
  max-width: 820px;
  margin: 0 auto;
  padding: 3rem 1.5rem;
}

.sidebar {
  position: sticky;
  top: var(--app-header-height);
  flex: 0 0 var(--course-sidebar-width);
  width: var(--course-sidebar-width);
  height: calc(100vh - var(--app-header-height));
  z-index: 90;
  transform: translateX(0);
  transition: transform 0.3s ease;
}

.main-content {
  flex: 1;
  min-width: 0;
  position: relative;
}

.content-wrapper {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 28px 80px;
}

.menu-toggle {
  display: none;
  position: fixed;
  left: 16px;
  top: 90px;
  z-index: 70;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.mobile-sidebar-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-light);
  font-weight: 700;
  color: var(--color-text);
}

.close-sidebar {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-alt);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 80;
}

/* Materials tab */
.materials-content {
  padding: 2rem 0 4rem;
}

.stage-section {
  margin-bottom: 2.5rem;
}

.stage-section h2 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 1rem;
}

.stage-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2rem 0.6rem;
  background: var(--color-learn);
  color: #fff;
  border-radius: var(--radius-full);
  margin-right: 0.5rem;
}

.material-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}

.stage-empty {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  padding: 2rem 0;
  text-align: center;
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border);
}

.empty-state {
  text-align: center;
  padding: 4rem 0;
  color: var(--color-text-muted);
}

@media (max-width: 900px) {
  .course-shell {
    display: block;
  }

  .course-hero {
    padding-top: 1.5rem;
  }

  .course-heading h1 {
    font-size: 1.55rem;
  }

  .hero-bottom {
    flex-direction: column;
    align-items: flex-start;
  }

  .tab-bar {
    width: 100%;
  }

  .progress-badge {
    margin-bottom: 0;
  }

  .sidebar {
    position: fixed;
    top: var(--app-header-height);
    left: 0;
    transform: translateX(-100%);
    box-shadow: var(--shadow-lg);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .mobile-sidebar-header {
    display: flex;
  }

  .menu-toggle {
    display: inline-flex;
  }

  .content-wrapper {
    padding: 28px 20px 60px;
    padding-top: 60px;
  }

  .sidebar-overlay.open {
    display: block;
  }

  .material-grid {
    grid-template-columns: 1fr;
  }
}
</style>

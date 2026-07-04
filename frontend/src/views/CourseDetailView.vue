<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getCourseDetail, type CourseDetail } from '@/api/course'
import { getCourseContents, type Material } from '@/api/material'
import { getLessons, type Lesson } from '@/api/lesson'
import { getCourseProgress, saveCourseProgress } from '@/api/progress'
import {
  getPublicCourseDetail,
  getPublicLessons,
  getPublicMaterialFileUrl,
} from '@/api/publicLearning'
import CourseToc from '@/components/lesson/CourseToc.vue'
import LessonReader from '@/components/lesson/LessonReader.vue'
import PrevNextNav from '@/components/lesson/PrevNextNav.vue'
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'

interface MaterialSection {
  key: string
  id: number | null
  title: string
  label: string
  materials: Material[]
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const courseId = computed(() => Number(route.params.courseId))

const course = ref<CourseDetail | null>(null)
const lessons = ref<Lesson[]>([])
const materials = ref<Material[]>([])
const loading = ref(true)
const currentLessonId = ref<number | null>(null)
const contentSource = ref<'authenticated' | 'public'>('public')
const activeTab = ref<'lessons' | 'materials'>(route.query.tab === 'materials' ? 'materials' : 'lessons')
const sidebarOpen = ref(false)
const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)

const isTeacherOrAdmin = computed(() =>
  ['teacher', 'admin'].includes(authStore.user?.role || ''),
)

const canSaveProgress = computed(() =>
  authStore.isLoggedIn &&
  authStore.user?.role === 'student' &&
  contentSource.value === 'authenticated',
)

const visibleLessons = computed(() => {
  if (isTeacherOrAdmin.value) return lessons.value
  return lessons.value.filter((lesson) => lesson.status === 'published')
})

const currentLesson = computed(
  () => visibleLessons.value.find((lesson) => lesson.id === currentLessonId.value) || null,
)

const currentLessonIndex = computed(() =>
  visibleLessons.value.findIndex((lesson) => lesson.id === currentLessonId.value),
)

const prevLesson = computed<Lesson | null>(() => {
  const index = currentLessonIndex.value
  return index > 0 ? (visibleLessons.value[index - 1] ?? null) : null
})

const nextLesson = computed<Lesson | null>(() => {
  const index = currentLessonIndex.value
  return index >= 0 && index < visibleLessons.value.length - 1
    ? (visibleLessons.value[index + 1] ?? null)
    : null
})

const progressPercent = computed(() => {
  if (!visibleLessons.value.length || currentLessonIndex.value < 0) return 0
  return Math.round(((currentLessonIndex.value + 1) / visibleLessons.value.length) * 100)
})

const railMaterials = computed(() => materials.value.slice(0, 5))

const materialSections = computed<MaterialSection[]>(() => {
  const sections: MaterialSection[] = (course.value?.stages ?? []).map((stage, index) => ({
    key: `stage-${stage.id}`,
    id: stage.id,
    title: stage.name,
    label: `阶段 ${index + 1}`,
    materials: stage.materials ?? [],
  }))

  const uncategorized = course.value?.uncategorized_materials ?? []
  if (uncategorized.length) {
    sections.push({
      key: 'uncategorized',
      id: null,
      title: '未分类资料',
      label: '其他',
      materials: uncategorized,
    })
  }

  return sections
})

const materialTypeStats = computed(() => {
  const stats = { pdf: 0, video: 0, link: 0 }
  materials.value.forEach((material) => {
    stats[material.type] += 1
  })
  return stats
})

const selectedMaterialPreviewUrl = computed(() => {
  if (!selectedMaterial.value) return undefined
  if (contentSource.value === 'public') return getPublicMaterialFileUrl(selectedMaterial.value.id)
  return undefined
})

function selectLesson(lesson: Lesson) {
  if (lesson.id === currentLessonId.value) {
    sidebarOpen.value = false
    return
  }
  currentLessonId.value = lesson.id
  activeTab.value = 'lessons'
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
  if (canSaveProgress.value) {
    try {
      await saveCourseProgress(courseId.value, lessonId)
    } catch {
      // 进度保存失败不影响阅读流程。
    }
  }
  router.replace({ query: { ...route.query, tab: 'lessons', lesson_id: String(lessonId) } })
}

async function loadAuthenticatedData() {
  const [detail, lessonList, materialList] = await Promise.all([
    getCourseDetail(courseId.value, true),
    getLessons(courseId.value),
    getCourseContents(courseId.value),
  ])
  contentSource.value = 'authenticated'
  return { detail, lessonList, materialList }
}

async function loadPublicData() {
  const [detail, lessonList] = await Promise.all([
    getPublicCourseDetail(courseId.value, true),
    getPublicLessons(courseId.value),
  ])
  const stageMaterials = (detail.stages ?? []).flatMap((stage) => stage.materials ?? [])
  const materialList: Material[] = [
    ...stageMaterials,
    ...(detail.uncategorized_materials ?? []),
  ]
  contentSource.value = 'public'
  return { detail, lessonList, materialList }
}

async function loadData() {
  loading.value = true
  try {
    let loaded: { detail: CourseDetail; lessonList: Lesson[]; materialList: Material[] }
    if (authStore.isLoggedIn && authStore.user?.role === 'student') {
      try {
        loaded = await loadAuthenticatedData()
      } catch {
        loaded = await loadPublicData()
      }
    } else {
      loaded = await loadPublicData()
    }

    course.value = {
      ...loaded.detail,
      stages: loaded.detail.stages ?? [],
      uncategorized_materials: loaded.detail.uncategorized_materials ?? [],
    }
    lessons.value = loaded.lessonList
    materials.value = loaded.materialList

    if (!visibleLessons.value.length && loaded.materialList.length > 0) {
      activeTab.value = 'materials'
    }

    const queryLessonId = route.query.lesson_id ? Number(route.query.lesson_id) : null
    const targetFromQuery = queryLessonId
      ? visibleLessons.value.find((lesson) => lesson.id === queryLessonId)
      : null

    if (targetFromQuery) {
      currentLessonId.value = targetFromQuery.id
    } else if (canSaveProgress.value) {
      try {
        const progress = await getCourseProgress(courseId.value)
        const targetFromProgress = progress.last_lesson_id
          ? visibleLessons.value.find((lesson) => lesson.id === progress.last_lesson_id)
          : null
        currentLessonId.value = targetFromProgress?.id ?? visibleLessons.value[0]?.id ?? null
      } catch {
        currentLessonId.value = visibleLessons.value[0]?.id ?? null
      }
    } else {
      currentLessonId.value = visibleLessons.value[0]?.id ?? null
    }
  } catch {
    ElMessage.error('课程加载失败，请检查该课程是否公开，或登录后刷新重试。')
  } finally {
    loading.value = false
  }
}

function previewMaterial(material: Material) {
  selectedMaterial.value = material
  previewVisible.value = true
}

function materialTypeLabel(type: Material['type']) {
  if (type === 'video') return '视频'
  if (type === 'pdf') return 'PDF'
  return '链接'
}

function materialSummary(material: Material) {
  return material.preview?.summary || material.size || '暂无摘要'
}

function scrollToMaterialStage(key: string) {
  const target = document.getElementById(`material-section-${key}`)
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function readerFileUrl(material: Material) {
  if (contentSource.value === 'public') return getPublicMaterialFileUrl(material.id)
  if (material.file_id) return `/api/files/${material.file_id}`
  return material.url
}

onMounted(loadData)
</script>

<template>
  <div class="course-detail-page">
    <section class="course-hero">
      <div class="container hero-container">
        <button class="back-btn" type="button" @click="router.push('/learn')">
          <span aria-hidden="true">←</span>
          <span>返回学习馆</span>
        </button>

        <div v-if="course" class="course-heading">
          <p class="course-kicker">公开课程阅读</p>
          <h1>{{ course.name }}</h1>
          <p class="course-desc">{{ course.description || '本课程暂无详细介绍。' }}</p>
        </div>

        <div class="hero-bottom">
          <div class="tab-bar" aria-label="课程视图">
            <button
              :class="['tab-btn', { active: activeTab === 'lessons' }]"
              type="button"
              @click="activeTab = 'lessons'"
            >
              课程目录
            </button>
            <button
              :class="['tab-btn', { active: activeTab === 'materials' }]"
              type="button"
              @click="activeTab = 'materials'"
            >
              学习资料
            </button>
          </div>

          <div v-if="activeTab === 'lessons' && visibleLessons.length && canSaveProgress" class="progress-badge">
            <span>学习进度</span>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <span>{{ progressPercent }}%</span>
          </div>
          <div v-if="contentSource === 'public' && !canSaveProgress" class="guest-progress-note">
            登录后可保存学习进度
          </div>
        </div>
      </div>
    </section>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <template v-else>
      <template v-if="activeTab === 'lessons'">
        <button
          v-if="!sidebarOpen"
          class="mobile-toc-button"
          type="button"
          @click="sidebarOpen = true"
        >
          目录
        </button>
        <div
          class="sidebar-overlay"
          :class="{ open: sidebarOpen }"
          @click="sidebarOpen = false"
        ></div>

        <div class="booksite-layout">
          <aside class="reader-sidebar" :class="{ open: sidebarOpen }">
            <div class="mobile-sidebar-header">
              <span>课程目录</span>
              <button type="button" class="close-sidebar" @click="sidebarOpen = false">关闭</button>
            </div>
            <CourseToc
              :lessons="visibleLessons"
              :active-lesson-id="currentLessonId"
              @select="selectLesson"
            />
          </aside>

          <main class="reader-main">
            <LessonReader
              :lesson="currentLesson"
              :materials="materials"
              :file-url-resolver="readerFileUrl"
              @preview="previewMaterial"
            />
            <PrevNextNav
              :prev-lesson="prevLesson"
              :next-lesson="nextLesson"
              @prev="goPrev"
              @next="goNext"
            />
          </main>

          <aside class="resource-rail">
            <section class="rail-section">
              <div class="rail-heading">
                <h2>本课学习资料</h2>
                <span>{{ materials.length }} 份</span>
              </div>
              <div v-if="railMaterials.length" class="rail-material-list">
                <button
                  v-for="material in railMaterials"
                  :key="material.id"
                  type="button"
                  class="rail-material"
                  @click="previewMaterial(material)"
                >
                  <span class="material-type">{{ materialTypeLabel(material.type) }}</span>
                  <strong>{{ material.title }}</strong>
                  <small>{{ materialSummary(material) }}</small>
                </button>
              </div>
              <div v-else class="rail-empty">本课暂未配置配套资料。</div>
              <button
                v-if="materials.length > railMaterials.length"
                type="button"
                class="rail-link"
                @click="activeTab = 'materials'"
              >
                查看全部学习资料
              </button>
            </section>

            <section class="rail-section">
              <h2>课程信息</h2>
              <dl class="course-facts">
                <div>
                  <dt>公开课时</dt>
                  <dd>{{ visibleLessons.length }}</dd>
                </div>
                <div>
                  <dt>学习资料</dt>
                  <dd>{{ materials.length }}</dd>
                </div>
                <div>
                  <dt>阅读状态</dt>
                  <dd>{{ currentLesson ? `第 ${currentLessonIndex + 1} 课` : '未选择' }}</dd>
                </div>
              </dl>
            </section>

            <section v-if="contentSource === 'public' && !canSaveProgress" class="rail-section">
              <h2>学习提示</h2>
              <p class="rail-note">登录后可保存学习进度，后续可以从学习馆继续阅读。</p>
            </section>
          </aside>
        </div>
      </template>

      <main v-else class="materials-content">
        <div class="materials-booksite-layout">
          <aside class="materials-sidebar">
            <section class="materials-panel">
              <h2>资料目录</h2>
              <button
                v-for="section in materialSections"
                :key="section.key"
                type="button"
                class="material-toc-item"
                @click="scrollToMaterialStage(section.key)"
              >
                <span>{{ section.label }}</span>
                <strong>{{ section.title }}</strong>
                <small>{{ section.materials.length }} 份资料</small>
              </button>
              <div v-if="!materialSections.length" class="materials-empty-small">暂无资料目录</div>
            </section>
          </aside>

          <section class="materials-reader">
            <header class="materials-reader-header">
              <p class="course-kicker">学习资料库</p>
              <h2>{{ course?.name || '学习资料' }}</h2>
              <p>按阶段整理课程 PDF、视频与外部链接。先浏览目录，再打开资料预览。</p>
            </header>

            <section
              v-for="section in materialSections"
              :id="`material-section-${section.key}`"
              :key="section.key"
              class="stage-section"
            >
              <h2>
                <span class="stage-badge">{{ section.label }}</span>
                {{ section.title }}
              </h2>
              <div v-if="section.materials.length > 0" class="material-flow">
                <MaterialRichCard
                  v-for="material in section.materials"
                  :key="material.id"
                  :material="material"
                  @preview="previewMaterial"
                />
              </div>
              <div v-else class="stage-empty">该阶段暂无资料</div>
            </section>

            <div v-if="!materialSections.length" class="empty-state">
              该课程暂无学习资料。
            </div>
          </section>

          <aside class="materials-rail">
            <section class="rail-section">
              <h2>本页资料</h2>
              <dl class="course-facts">
                <div>
                  <dt>全部资料</dt>
                  <dd>{{ materials.length }}</dd>
                </div>
                <div>
                  <dt>PDF</dt>
                  <dd>{{ materialTypeStats.pdf }}</dd>
                </div>
                <div>
                  <dt>视频</dt>
                  <dd>{{ materialTypeStats.video }}</dd>
                </div>
                <div>
                  <dt>链接</dt>
                  <dd>{{ materialTypeStats.link }}</dd>
                </div>
              </dl>
            </section>

            <section class="rail-section">
              <h2>快速打开</h2>
              <div v-if="materials.length" class="rail-material-list">
                <button
                  v-for="material in materials.slice(0, 8)"
                  :key="material.id"
                  type="button"
                  class="rail-material"
                  @click="previewMaterial(material)"
                >
                  <span class="material-type">{{ materialTypeLabel(material.type) }}</span>
                  <strong>{{ material.title }}</strong>
                  <small>{{ materialSummary(material) }}</small>
                </button>
              </div>
              <div v-else class="rail-empty">暂无可打开的资料。</div>
            </section>

            <section v-if="contentSource === 'public' && !canSaveProgress" class="rail-section">
              <h2>学习提示</h2>
              <p class="rail-note">游客可以浏览公开资料；登录后可保存学习进度。</p>
            </section>
          </aside>
        </div>
      </main>
    </template>

    <MaterialPreviewDialog
      v-model:visible="previewVisible"
      :material="selectedMaterial"
      :preview-url="selectedMaterialPreviewUrl"
    />
  </div>
</template>

<style scoped>
.course-detail-page {
  --app-header-height: 60px;
  min-height: 100vh;
  padding-top: var(--app-header-height);
  background: var(--color-bg);
}

.course-hero {
  padding: 2rem 0 0;
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
  gap: 1.25rem;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding: 8px 12px;
  color: var(--color-learn);
  background: rgba(45, 106, 122, 0.08);
  border: 1px solid rgba(45, 106, 122, 0.18);
  border-radius: var(--radius-full);
  font-weight: 800;
}

.course-kicker {
  margin: 0 0 0.35rem;
  color: var(--color-learn);
  font-size: 0.82rem;
  font-weight: 900;
}

.course-heading h1 {
  font-size: 1.9rem;
  font-weight: 900;
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: 0.6rem;
}

.course-desc {
  color: var(--color-text-secondary);
  max-width: 760px;
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
}

.tab-btn {
  padding: 0.75rem 1.25rem;
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--color-text-secondary);
  background: transparent;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 160ms var(--ease-out), border-color 160ms var(--ease-out);
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
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.guest-progress-note {
  margin-bottom: 0.5rem;
  color: var(--color-text-muted);
  font-size: 0.84rem;
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

.booksite-layout {
  max-width: 1480px;
  margin: 0 auto;
  padding: 24px 24px 80px;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: flex-start;
}

.reader-sidebar,
.resource-rail {
  position: sticky;
  top: calc(var(--app-header-height) + 16px);
  max-height: calc(100vh - var(--app-header-height) - 32px);
  overflow-y: auto;
}

.reader-sidebar {
  min-height: 420px;
}

.reader-main {
  min-width: 0;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
}

.resource-rail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rail-section {
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.rail-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rail-section h2 {
  margin: 0 0 12px;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 900;
}

.rail-heading h2 {
  margin-bottom: 0;
}

.rail-heading span {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.rail-material-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.rail-material {
  display: grid;
  gap: 5px;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-bg-alt);
  text-align: left;
  transition: background 160ms var(--ease-out), border-color 160ms var(--ease-out);
}

.rail-material:hover {
  background: var(--color-bg-card);
  border-color: rgba(45, 106, 122, 0.24);
}

.material-type {
  color: var(--color-learn);
  font-size: 0.72rem;
  font-weight: 900;
}

.rail-material strong {
  color: var(--color-text);
  line-height: 1.45;
}

.rail-material small {
  color: var(--color-text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rail-link {
  width: 100%;
  margin-top: 10px;
  padding: 8px 10px;
  color: var(--color-learn);
  background: rgba(45, 106, 122, 0.08);
  border-radius: var(--radius-sm);
  font-weight: 800;
}

.rail-empty,
.rail-note {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.7;
  font-size: 0.88rem;
}

.course-facts {
  display: grid;
  gap: 8px;
  margin: 0;
}

.course-facts div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.course-facts div:last-child {
  border-bottom: 0;
}

.course-facts dt {
  color: var(--color-text-muted);
}

.course-facts dd {
  margin: 0;
  color: var(--color-text);
  font-weight: 800;
}

.mobile-sidebar-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-light);
  font-weight: 800;
  color: var(--color-text);
}

.close-sidebar {
  padding: 6px 10px;
  background: var(--color-bg-alt);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.sidebar-overlay,
.mobile-toc-button {
  display: none;
}

.materials-content {
  padding: 0 0 4rem;
}

.materials-booksite-layout {
  max-width: 1480px;
  margin: 0 auto;
  padding: 24px 24px 80px;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 300px;
  gap: 24px;
  align-items: flex-start;
}

.materials-sidebar,
.materials-rail {
  position: sticky;
  top: calc(var(--app-header-height) + 16px);
  max-height: calc(100vh - var(--app-header-height) - 32px);
  overflow-y: auto;
}

.materials-panel {
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.materials-panel h2 {
  margin: 0 0 12px;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 900;
}

.material-toc-item {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 10px;
  margin-bottom: 6px;
  text-align: left;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  transition: background 160ms var(--ease-out), border-color 160ms var(--ease-out);
}

.material-toc-item:hover {
  background: var(--color-bg-alt);
  border-color: rgba(45, 106, 122, 0.18);
}

.material-toc-item span {
  color: var(--color-learn);
  font-size: 0.72rem;
  font-weight: 900;
}

.material-toc-item strong {
  color: var(--color-text);
  font-size: 0.9rem;
  line-height: 1.45;
}

.material-toc-item small,
.materials-empty-small {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.materials-reader {
  min-width: 0;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
}

.materials-reader-header {
  margin-bottom: 24px;
  padding: 32px 36px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.materials-reader-header h2 {
  margin: 0 0 10px;
  color: var(--color-text);
  font-size: 1.55rem;
  font-weight: 900;
}

.materials-reader-header p:last-child {
  max-width: 680px;
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.material-flow {
  display: grid;
  gap: 16px;
}

.materials-rail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stage-section {
  margin-bottom: 2.5rem;
  scroll-margin-top: calc(var(--app-header-height) + 20px);
}

.stage-section h2 {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: 1rem;
}

.stage-badge {
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.2rem 0.6rem;
  background: var(--color-learn);
  color: var(--color-bg-card);
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

@media (max-width: 1180px) {
  .booksite-layout {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  .resource-rail {
    grid-column: 2;
    position: static;
    max-height: none;
  }

  .materials-booksite-layout {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  .materials-rail {
    grid-column: 2;
    position: static;
    max-height: none;
  }
}

@media (max-width: 900px) {
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

  .booksite-layout {
    display: block;
    padding: 18px 16px 60px;
  }

  .reader-sidebar {
    position: fixed;
    top: var(--app-header-height);
    left: 0;
    z-index: 90;
    width: min(86vw, 320px);
    height: calc(100vh - var(--app-header-height));
    max-height: none;
    transform: translateX(-100%);
    transition: transform 220ms var(--ease-out);
    background: var(--color-bg-card);
    box-shadow: var(--shadow-lg);
  }

  .reader-sidebar.open {
    transform: translateX(0);
  }

  .mobile-sidebar-header {
    display: flex;
  }

  .mobile-toc-button {
    display: inline-flex;
    position: fixed;
    left: 16px;
    top: 86px;
    z-index: 70;
    padding: 8px 12px;
    background: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-sm);
    color: var(--color-text-secondary);
    font-weight: 800;
  }

  .sidebar-overlay.open {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 80;
    background: rgba(12, 18, 24, 0.46);
  }

  .reader-main {
    max-width: none;
    padding-top: 48px;
  }

  .resource-rail {
    margin-top: 18px;
  }

  .materials-booksite-layout {
    display: block;
    padding: 18px 16px 60px;
  }

  .materials-sidebar,
  .materials-rail {
    position: static;
    max-height: none;
  }

  .materials-sidebar {
    margin-bottom: 18px;
  }

  .materials-reader-header {
    padding: 24px 20px;
  }

  .materials-rail {
    margin-top: 18px;
  }

  .material-grid {
    grid-template-columns: 1fr;
  }
}
</style>

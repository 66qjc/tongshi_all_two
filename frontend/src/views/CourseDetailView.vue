<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { getCourseDetail, type CourseDetail } from '@/api/course'
import { getCourseContents, type Material } from '@/api/material'
import { getLessons, type Lesson } from '@/api/lesson'
import {
  getCourseProgress,
  reportLessonProgress,
  reportLessonProgressKeepalive,
  type CourseProgress,
} from '@/api/progress'
import {
  getPublicCourseDetail,
  getPublicLessons,
  getPublicMaterialFileUrl,
} from '@/api/publicLearning'
import CourseToc from '@/components/lesson/CourseToc.vue'
import LessonReader from '@/components/lesson/LessonReader.vue'
import PrevNextNav from '@/components/lesson/PrevNextNav.vue'
import MaterialInlineReader from '@/components/learn/MaterialInlineReader.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'
import { useAuthenticatedFileUrl } from '@/composables/useAuthenticatedFileUrl'

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
const activeMaterialId = ref<number | null>(null)
const courseProgress = ref<CourseProgress | null>(null)
const videoPosition = ref(0)
const videoDuration = ref(0)
const currentLessonHasVideo = ref(true)
const completingLesson = ref(false)

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
  if (canSaveProgress.value && courseProgress.value) return Math.round(courseProgress.value.completion_rate || 0)
  if (!visibleLessons.value.length || currentLessonIndex.value < 0) return 0
  return Math.round(((currentLessonIndex.value + 1) / visibleLessons.value.length) * 100)
})

const currentLessonProgress = computed(() => {
  if (!currentLessonId.value) return null
  return courseProgress.value?.lessons.find((item) => item.lesson_id === currentLessonId.value) ?? null
})

const resumePosition = computed(() => currentLessonProgress.value?.last_position || 0)

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

const selectedMaterialPreviewUrl = computed(() => {
  if (!selectedMaterial.value) return undefined
  if (selectedMaterial.value.type === 'link') return undefined
  if (contentSource.value === 'public') return getPublicMaterialFileUrl(selectedMaterial.value.id)
  return undefined
})

const defaultMaterial = computed(() => pickDefaultMaterial(materials.value))

const activeMaterial = computed(() => {
  if (!materials.value.length) return null
  return materials.value.find((material) => material.id === activeMaterialId.value) || defaultMaterial.value
})

const activeMaterialIndex = computed(() => {
  if (!activeMaterial.value) return -1
  return materials.value.findIndex((material) => material.id === activeMaterial.value?.id)
})

const prevMaterial = computed<Material | null>(() => {
  const index = activeMaterialIndex.value
  return index > 0 ? (materials.value[index - 1] ?? null) : null
})

const nextMaterial = computed<Material | null>(() => {
  const index = activeMaterialIndex.value
  return index >= 0 && index < materials.value.length - 1
    ? (materials.value[index + 1] ?? null)
    : null
})

const activeMaterialFileUrl = computed(() => {
  if (!activeMaterial.value) return ''
  return materialFileUrl(activeMaterial.value)
})

const activeMaterialFileEnabled = computed(() =>
  activeTab.value === 'materials' && Boolean(activeMaterial.value && activeMaterialFileUrl.value),
)

const {
  resolvedUrl: activeMaterialResolvedUrl,
  loading: activeMaterialFileLoading,
  error: activeMaterialFileError,
  retryOnce: retryActiveMaterialFileOnce,
} = useAuthenticatedFileUrl(activeMaterialFileUrl, { enabled: activeMaterialFileEnabled })

function handleActiveMaterialFileError(failedUrl: string) {
  void retryActiveMaterialFileOnce(failedUrl)
}

const hasRefreshingMaterialPreview = computed(() =>
  activeTab.value === 'materials' &&
  materials.value.some((material) =>
    ['pending', 'processing'].includes(material.preview?.status || ''),
  ),
)

let materialRefreshTimer: number | undefined
let lessonProgressTimer: number | undefined
let lastProgressReportedAt = Date.now()
let finalReportSent = false

function selectLesson(lesson: Lesson) {
  if (lesson.id === currentLessonId.value) {
    sidebarOpen.value = false
    return
  }
  if (canSaveProgress.value) {
    void reportCurrentLessonProgress(takeUnreportedDuration())
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

function takeUnreportedDuration() {
  const now = Date.now()
  const seconds = Math.max(0, Math.round((now - lastProgressReportedAt) / 1000))
  lastProgressReportedAt = now
  return Math.min(seconds, 120)
}

function calculatedLessonPercent() {
  if (videoDuration.value > 0) {
    return Math.min(100, Math.max(0, Math.round((videoPosition.value / videoDuration.value) * 100)))
  }
  return Math.max(currentLessonProgress.value?.progress_percent || 0, 10)
}

async function refreshCourseProgress() {
  if (!canSaveProgress.value) return
  try {
    courseProgress.value = await getCourseProgress(courseId.value)
  } catch {
    // 进度刷新失败不影响当前阅读。
  }
}

async function reportCurrentLessonProgress(
  durationSeconds = 0,
  visitStarted = false,
  progressPercentOverride?: number,
) {
  if (!canSaveProgress.value || !currentLessonId.value) return
  try {
    const progress = await reportLessonProgress(courseId.value, currentLessonId.value, {
      progress_percent: progressPercentOverride ?? calculatedLessonPercent(),
      last_position: videoPosition.value,
      duration_seconds: durationSeconds,
      visit_started: visitStarted,
    })
    if (courseProgress.value) {
      const index = courseProgress.value.lessons.findIndex((item) => item.lesson_id === progress.lesson_id)
      if (index >= 0) courseProgress.value.lessons[index] = progress
      courseProgress.value.last_lesson_id = progress.lesson_id
      courseProgress.value.completed_lessons = courseProgress.value.lessons.filter((item) => item.status === 'completed').length
      courseProgress.value.total_duration = courseProgress.value.lessons.reduce((sum, item) => sum + item.duration_seconds, 0)
      courseProgress.value.completion_rate = courseProgress.value.total_lessons
        ? Math.round((courseProgress.value.completed_lessons / courseProgress.value.total_lessons) * 1000) / 10
        : 0
    }
    return progress
  } catch {
    // 进度上报失败不影响阅读流程。
    return null
  }
}

function handleLessonContentKind(hasVideo: boolean) {
  currentLessonHasVideo.value = hasVideo
}

async function completeCurrentLesson() {
  if (completingLesson.value) return
  completingLesson.value = true
  try {
    const progress = await reportCurrentLessonProgress(takeUnreportedDuration(), false, 100)
    if (progress?.status === 'completed') {
      ElMessage.success('本课已完成')
      return
    }
    ElMessage.error('完成本课失败，请稍后重试')
  } finally {
    completingLesson.value = false
  }
}

function stopLessonProgressTimer() {
  if (lessonProgressTimer !== undefined) {
    window.clearInterval(lessonProgressTimer)
    lessonProgressTimer = undefined
  }
}

function startLessonProgressTimer() {
  stopLessonProgressTimer()
  if (!canSaveProgress.value || !currentLessonId.value) return
  lastProgressReportedAt = Date.now()
  lessonProgressTimer = window.setInterval(() => {
    if (document.hidden) return
    void reportCurrentLessonProgress(takeUnreportedDuration())
  }, 30000)
}

function resetLessonTracking() {
  videoPosition.value = resumePosition.value
  videoDuration.value = 0
  startLessonProgressTimer()
}

function saveProgressAndUrl(lessonId: number) {
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
  courseProgress.value = null
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
    syncActiveMaterial(loaded.materialList)

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
        courseProgress.value = progress
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
    if (canSaveProgress.value && !courseProgress.value) {
      await refreshCourseProgress()
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

function selectMaterial(material: Material | null) {
  if (!material) return
  activeMaterialId.value = material.id
  activeTab.value = 'materials'
}

function syncActiveMaterial(materialList: Material[]) {
  const currentActive = materialList.find((material) => material.id === activeMaterialId.value)
  if (currentActive) return
  activeMaterialId.value = pickDefaultMaterial(materialList)?.id ?? null
}

function parseMaterialSize(size: string) {
  const match = size.match(/([\d.]+)\s*(B|KB|MB|GB)?/i)
  if (!match) return 0
  const value = Number(match[1])
  if (!Number.isFinite(value)) return 0
  const unit = (match[2] || 'B').toUpperCase()
  if (unit === 'GB') return value * 1024 * 1024 * 1024
  if (unit === 'MB') return value * 1024 * 1024
  if (unit === 'KB') return value * 1024
  return value
}

function materialLearningScore(material: Material) {
  let score = 0
  if (material.type === 'pdf') score += 3000
  else if (material.type === 'video') score += 2000
  else score += 1000

  if (material.preview?.status === 'failed') score -= 500
  if (/长内容|阅读包|手册|学习|通识/.test(material.title)) score += 300
  if (material.preview?.page_count || material.pages) {
    score += Math.min(400, (material.preview?.page_count || material.pages) * 20)
  }
  score += Math.min(600, parseMaterialSize(material.size) / 4096)
  return score
}

function pickDefaultMaterial(materialList: Material[]) {
  return [...materialList].sort((a, b) => materialLearningScore(b) - materialLearningScore(a))[0] ?? null
}

function materialTypeLabel(type: Material['type']) {
  if (type === 'video') return '视频'
  if (type === 'pdf') return 'PDF'
  return '链接'
}

function materialSummary(material: Material) {
  return material.preview?.summary || material.size || '暂无摘要'
}

function materialMetaText(material: Material) {
  const parts: string[] = []
  if (material.preview?.page_count) parts.push(`${material.preview.page_count} 页`)
  else if (material.pages) parts.push(`${material.pages} 页`)
  if (material.preview?.duration_seconds) {
    parts.push(`${Math.max(1, Math.round(material.preview.duration_seconds / 60))} 分钟`)
  } else if (material.duration) {
    parts.push(material.duration)
  }
  if (material.size) parts.push(material.size)
  if (material.date) parts.push(material.date)
  return parts.join(' · ')
}

function materialFileUrl(material: Material) {
  if (material.type === 'link') return material.url
  if (contentSource.value === 'public') return getPublicMaterialFileUrl(material.id)
  if (material.file_id) return `/api/files/${material.file_id}`
  return material.url
}

function readerFileUrl(material: Material) {
  return materialFileUrl(material)
}

async function refreshMaterialsForInlineReader() {
  if (activeTab.value !== 'materials') return
  try {
    if (contentSource.value === 'authenticated') {
      const materialList = await getCourseContents(courseId.value)
      materials.value = materialList
      syncActiveMaterial(materialList)
      return
    }

    const detail = await getPublicCourseDetail(courseId.value, true)
    const refreshedStages = detail.stages ?? []
    const materialList = [
      ...refreshedStages.flatMap((stage) => stage.materials ?? []),
      ...(detail.uncategorized_materials ?? []),
    ]
    course.value = {
      ...detail,
      stages: refreshedStages,
      uncategorized_materials: detail.uncategorized_materials ?? [],
    }
    materials.value = materialList
    syncActiveMaterial(materialList)
  } catch {
    // 资料状态刷新失败不打断当前阅读。
  }
}

function stopMaterialRefreshTimer() {
  if (materialRefreshTimer !== undefined) {
    window.clearInterval(materialRefreshTimer)
    materialRefreshTimer = undefined
  }
}

function syncMaterialRefreshTimer() {
  stopMaterialRefreshTimer()
  if (!hasRefreshingMaterialPreview.value || document.hidden) return
  materialRefreshTimer = window.setInterval(refreshMaterialsForInlineReader, 18000)
}

function handleVisibilityChange() {
  if (document.hidden) {
    stopMaterialRefreshTimer()
    reportFinalProgressOnce()
    return
  }
  finalReportSent = false
  lastProgressReportedAt = Date.now()
  if (activeTab.value === 'materials') {
    void refreshMaterialsForInlineReader()
  }
  syncMaterialRefreshTimer()
}

function reportFinalProgressOnce() {
  if (!canSaveProgress.value || !currentLessonId.value) return
  if (finalReportSent) return
  finalReportSent = true
  void reportLessonProgressKeepalive(courseId.value, currentLessonId.value, {
    progress_percent: calculatedLessonPercent(),
    last_position: videoPosition.value,
    duration_seconds: takeUnreportedDuration(),
    visit_started: false,
  })
}

function handlePageHide() {
  reportFinalProgressOnce()
}

function handleLessonVideoProgress(payload: { currentTime: number; duration: number; ended: boolean }) {
  videoPosition.value = payload.currentTime
  videoDuration.value = payload.duration
  if (payload.ended) {
    void reportCurrentLessonProgress(takeUnreportedDuration())
  }
}

watch(hasRefreshingMaterialPreview, syncMaterialRefreshTimer)
watch(activeTab, () => {
  if (activeTab.value === 'materials') {
    void refreshMaterialsForInlineReader()
  }
  syncMaterialRefreshTimer()
})

watch(currentLessonId, () => {
  currentLessonHasVideo.value = true
  completingLesson.value = false
  finalReportSent = false
  resetLessonTracking()
  void reportCurrentLessonProgress(0, true)
})

onMounted(() => {
  void loadData()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('pagehide', handlePageHide)
})

onBeforeUnmount(() => {
  reportFinalProgressOnce()
  stopLessonProgressTimer()
  stopMaterialRefreshTimer()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('pagehide', handlePageHide)
})
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
              学习资料库
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
              :resume-position="resumePosition"
              @preview="previewMaterial"
              @video-progress="handleLessonVideoProgress"
              @content-kind="handleLessonContentKind"
            />
            <div
              v-if="canSaveProgress && currentLesson && !currentLessonHasVideo && currentLessonProgress?.status !== 'completed'"
              class="lesson-completion-actions"
            >
              <el-button
                type="primary"
                :icon="Check"
                :loading="completingLesson"
                @click="completeCurrentLesson"
              >
                完成本课
              </el-button>
            </div>
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
        <div class="material-doc-shell">
          <aside class="material-doc-sidebar">
            <section class="doc-panel">
              <p class="doc-panel-kicker">资料目录</p>
              <h2>{{ course?.name || '学习资料' }}</h2>
              <div v-if="materialSections.length" class="doc-section-list">
                <section
                  v-for="section in materialSections"
                  :key="section.key"
                  class="doc-section-group"
                >
                  <button
                    type="button"
                    class="doc-section-title"
                    @click="selectMaterial(section.materials[0] || null)"
                  >
                    <span>{{ section.label }}</span>
                    <strong>{{ section.title }}</strong>
                    <small>{{ section.materials.length }} 份资料</small>
                  </button>
                  <button
                    v-for="material in section.materials"
                    :key="material.id"
                    type="button"
                    :class="['doc-material-link', { active: activeMaterial?.id === material.id }]"
                    @click="selectMaterial(material)"
                  >
                    <span class="material-type">{{ materialTypeLabel(material.type) }}</span>
                    <strong>{{ material.title }}</strong>
                    <small>{{ materialMetaText(material) || materialSummary(material) }}</small>
                  </button>
                </section>
              </div>
              <div v-if="!materialSections.length" class="materials-empty-small">暂无资料目录</div>
            </section>
          </aside>

          <section class="material-doc-main">
            <MaterialInlineReader
              :material="activeMaterial"
              :file-url="activeMaterialResolvedUrl"
              :file-loading="activeMaterialFileLoading"
              :file-error="activeMaterialFileError"
              @file-error="handleActiveMaterialFileError"
            />
          </section>

          <aside class="material-doc-guide">
            <section class="guide-panel">
              <p class="doc-panel-kicker">当前资料</p>
              <h2>{{ activeMaterial?.title || '未选择资料' }}</h2>
              <p class="guide-summary">
                {{ activeMaterial ? materialSummary(activeMaterial) : '请选择左侧目录中的资料开始阅读。' }}
              </p>
              <dl v-if="activeMaterial" class="guide-facts">
                <div>
                  <dt>类型</dt>
                  <dd>{{ materialTypeLabel(activeMaterial.type) }}</dd>
                </div>
                <div v-if="activeMaterial.size">
                  <dt>大小</dt>
                  <dd>{{ activeMaterial.size }}</dd>
                </div>
                <div v-if="activeMaterial.preview?.page_count || activeMaterial.pages">
                  <dt>页数</dt>
                  <dd>{{ activeMaterial.preview?.page_count || activeMaterial.pages }} 页</dd>
                </div>
                <div v-if="activeMaterial.preview?.duration_seconds || activeMaterial.duration">
                  <dt>时长</dt>
                  <dd>
                    {{
                      activeMaterial.preview?.duration_seconds
                        ? `${Math.max(1, Math.round(activeMaterial.preview.duration_seconds / 60))} 分钟`
                        : activeMaterial.duration
                    }}
                  </dd>
                </div>
              </dl>
              <a
                v-if="activeMaterialResolvedUrl"
                class="guide-open-link"
                :href="activeMaterialResolvedUrl"
                target="_blank"
                rel="noopener"
              >
                打开原资料
              </a>
            </section>

            <section class="guide-panel">
              <p class="doc-panel-kicker">阅读顺序</p>
              <button
                type="button"
                class="guide-nav"
                :disabled="!prevMaterial"
                @click="selectMaterial(prevMaterial)"
              >
                <span>上一份资料</span>
                <strong>{{ prevMaterial?.title || '已经是第一份' }}</strong>
              </button>
              <button
                type="button"
                class="guide-nav"
                :disabled="!nextMaterial"
                @click="selectMaterial(nextMaterial)"
              >
                <span>下一份资料</span>
                <strong>{{ nextMaterial?.title || '已经是最后一份' }}</strong>
              </button>
            </section>

            <section v-if="contentSource === 'public' && !canSaveProgress" class="guide-panel">
              <p class="doc-panel-kicker">学习提示</p>
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
  text-wrap: balance;
}

.course-desc {
  color: var(--color-text-secondary);
  max-width: 72ch;
  line-height: 1.8;
  margin: 0;
  text-wrap: pretty;
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

.lesson-completion-actions {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0 4px;
}

@media (max-width: 640px) {
  .lesson-completion-actions :deep(.el-button) {
    width: 100%;
  }
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
  text-wrap: pretty;
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

.material-doc-shell {
  max-width: 1480px;
  margin: 0 auto;
  padding: 24px 24px 80px;
  display: grid;
  grid-template-columns: 292px minmax(0, 1fr) 280px;
  gap: 24px;
  align-items: flex-start;
}

.material-doc-sidebar,
.material-doc-guide {
  position: sticky;
  top: calc(var(--app-header-height) + 16px);
  max-height: calc(100vh - var(--app-header-height) - 32px);
  overflow-y: auto;
}

.doc-panel,
.guide-panel {
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.doc-panel-kicker {
  margin: 0 0 6px;
  color: var(--color-learn);
  font-size: 0.74rem;
  font-weight: 900;
}

.doc-panel h2,
.guide-panel h2 {
  margin: 0 0 14px;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 900;
  line-height: var(--leading-compact);
}

.doc-section-list {
  display: grid;
  gap: 14px;
}

.doc-section-group {
  display: grid;
  gap: 6px;
}

.doc-section-title,
.doc-material-link,
.guide-nav {
  width: 100%;
  text-align: left;
}

.doc-section-title {
  display: grid;
  gap: 3px;
  padding: 8px 4px;
  color: var(--color-text);
  background: transparent;
}

.doc-section-title span {
  color: var(--color-learn);
  font-size: 0.72rem;
  font-weight: 900;
}

.doc-section-title strong {
  font-size: 0.92rem;
}

.doc-section-title small {
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.doc-material-link {
  display: grid;
  gap: 4px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  transition: background 160ms var(--ease-out), border-color 160ms var(--ease-out);
}

.doc-material-link:hover,
.doc-material-link.active {
  background: var(--color-bg-alt);
  border-color: rgba(45, 106, 122, 0.22);
}

.doc-material-link.active {
  box-shadow: inset 0 0 0 1px rgba(45, 106, 122, 0.18);
}

.doc-material-link strong {
  color: var(--color-text);
  font-size: 0.88rem;
  line-height: 1.45;
}

.doc-material-link small,
.materials-empty-small {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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

.material-doc-main {
  min-width: 0;
}

.material-doc-guide {
  display: grid;
  gap: 16px;
}

.guide-summary {
  margin: 0 0 12px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  text-wrap: pretty;
}

.guide-facts {
  display: grid;
  gap: 8px;
  margin: 0;
}

.guide-facts div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.guide-facts div:last-child {
  border-bottom: 0;
}

.guide-facts dt {
  color: var(--color-text-muted);
}

.guide-facts dd {
  margin: 0;
  color: var(--color-text);
  font-weight: 800;
}

.guide-open-link {
  display: inline-flex;
  justify-content: center;
  width: 100%;
  margin-top: 12px;
  padding: 9px 12px;
  color: var(--color-bg-card);
  background: var(--color-learn);
  border-radius: var(--radius-sm);
  font-weight: 800;
}

.guide-nav {
  display: grid;
  gap: 4px;
  padding: 10px;
  margin-top: 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-bg-alt);
}

.guide-nav:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.guide-nav span {
  color: var(--color-text-muted);
  font-size: 0.76rem;
}

.guide-nav strong {
  color: var(--color-text);
  line-height: 1.45;
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

  .material-doc-shell {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .material-doc-guide {
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

  .material-doc-shell {
    display: block;
    padding: 18px 16px 60px;
  }

  .material-doc-sidebar,
  .material-doc-guide {
    position: static;
    max-height: none;
  }

  .material-doc-sidebar {
    margin-bottom: 18px;
  }

  .doc-section-list {
    display: grid;
    gap: 16px;
    overflow: visible;
    padding-bottom: 0;
  }

  .doc-section-group {
    min-width: 0;
  }

  .material-doc-guide {
    margin-top: 18px;
  }

  .material-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getCourseDetail, type CourseDetail } from '@/api/course'
import { getCourseContents, type Material } from '@/api/material'
import {
  getPublicCourseDetail,
  getPublicMaterialFileUrl,
} from '@/api/publicLearning'
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
const materials = ref<Material[]>([])
const loading = ref(true)
const contentSource = ref<'authenticated' | 'public'>('public')
const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)
const activeMaterialId = ref<number | null>(null)
/** 资料目录中折叠的阶段 key，默认全部展开 */
const collapsedStageKeys = ref<Set<string>>(new Set())

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
  Boolean(activeMaterial.value && activeMaterialFileUrl.value),
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
  materials.value.some((material) =>
    ['pending', 'processing'].includes(material.preview?.status || ''),
  ),
)

let materialRefreshTimer: number | undefined

async function loadAuthenticatedData() {
  const [detail, materialList] = await Promise.all([
    getCourseDetail(courseId.value, true),
    getCourseContents(courseId.value),
  ])
  contentSource.value = 'authenticated'
  return { detail, materialList }
}

async function loadPublicData() {
  const detail = await getPublicCourseDetail(courseId.value, true)
  const stageMaterials = (detail.stages ?? []).flatMap((stage) => stage.materials ?? [])
  const materialList: Material[] = [
    ...stageMaterials,
    ...(detail.uncategorized_materials ?? []),
  ]
  contentSource.value = 'public'
  return { detail, materialList }
}

async function loadData() {
  loading.value = true
  try {
    let loaded: { detail: CourseDetail; materialList: Material[] }
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
    materials.value = loaded.materialList
    syncActiveMaterial(loaded.materialList)
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
}

function isStageCollapsed(sectionKey: string) {
  return collapsedStageKeys.value.has(sectionKey)
}

function toggleStage(sectionKey: string) {
  const next = new Set(collapsedStageKeys.value)
  if (next.has(sectionKey)) next.delete(sectionKey)
  else next.add(sectionKey)
  collapsedStageKeys.value = next
}

function materialRowMeta(material: Material) {
  return material.size || materialMetaText(material) || ''
}

function materialRowTitle(material: Material) {
  const meta = materialMetaText(material)
  return meta ? `${material.title} · ${meta}` : material.title
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

async function refreshMaterialsForInlineReader() {
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
    return
  }
  void refreshMaterialsForInlineReader()
  syncMaterialRefreshTimer()
}

watch(hasRefreshingMaterialPreview, syncMaterialRefreshTimer)

onMounted(() => {
  void loadData()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  stopMaterialRefreshTimer()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="course-detail-page">
    <section class="course-hero">
      <div class="container hero-container">
        <button class="back-btn" type="button" @click="router.push('/learn')">
          <span aria-hidden="true">←</span>
          <span>返回教程列表</span>
        </button>

        <div v-if="course" class="course-heading">
          <p class="course-kicker">公开教程阅读</p>
          <h1>{{ course.name }}</h1>
          <p class="course-desc">{{ course.description || '本教程暂无详细介绍。' }}</p>
        </div>

        <div class="hero-bottom">
          <p class="hero-meta">
            学习资料 {{ materials.length }} 份
            <span v-if="contentSource === 'public' && !authStore.isLoggedIn"> · 游客可直接阅读公开资料</span>
          </p>
        </div>
      </div>
    </section>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <main v-else-if="!materials.length" class="materials-content">
      <div class="empty-state">
        <p>本教程暂无学习资料</p>
        <p class="empty-state-hint">请稍后再来，或返回教程列表选择其他课程。</p>
      </div>
    </main>

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
                  class="stage-head"
                  :class="{ collapsed: isStageCollapsed(section.key) }"
                  :aria-expanded="!isStageCollapsed(section.key)"
                  @click="toggleStage(section.key)"
                >
                  <span class="chev" aria-hidden="true">▾</span>
                  <span class="stage-badge">{{ section.label }}</span>
                  <span class="stage-title">{{ section.title }}</span>
                  <span class="stage-count">{{ section.materials.length }}</span>
                </button>
                <div
                  v-show="!isStageCollapsed(section.key)"
                  class="stage-materials"
                >
                  <button
                    v-for="material in section.materials"
                    :key="material.id"
                    type="button"
                    class="doc-material-link"
                    :class="{ active: activeMaterial?.id === material.id }"
                    :title="materialRowTitle(material)"
                    @click="selectMaterial(material)"
                  >
                    <span class="material-type">{{ materialTypeLabel(material.type) }}</span>
                    <strong>{{ material.title }}</strong>
                    <small v-if="materialRowMeta(material)">{{ materialRowMeta(material) }}</small>
                  </button>
                </div>
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

          <section v-if="contentSource === 'public' && !authStore.isLoggedIn" class="guide-panel">
            <p class="doc-panel-kicker">学习提示</p>
            <p class="rail-note">游客可以浏览公开资料；登录后可查看已加入的私有课程资料。</p>
          </section>
        </aside>
      </div>
    </main>

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
  padding-bottom: 1rem;
}

.hero-meta {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.88rem;
}

.loading-state {
  max-width: 820px;
  margin: 0 auto;
  padding: 3rem 1.5rem;
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
  gap: 6px;
}

.doc-section-group {
  display: grid;
  gap: 1px;
}

.doc-material-link,
.guide-nav,
.stage-head {
  width: 100%;
  text-align: left;
}

/* 阶段分组头：单行紧凑 */
.stage-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 5px 8px;
  border: none;
  border-radius: 4px;
  border-left: 3px solid var(--color-learn);
  background: var(--color-bg-alt);
  color: var(--color-text);
  line-height: 1.25;
  cursor: pointer;
}

.stage-head:hover {
  background: #ebe4d4;
}

.stage-head .chev {
  flex: 0 0 auto;
  width: 12px;
  color: var(--color-text-muted);
  font-size: 0.68rem;
  line-height: 1;
  transition: transform 140ms var(--ease-out);
}

.stage-head.collapsed .chev {
  transform: rotate(-90deg);
}

.stage-badge {
  flex: 0 0 auto;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(45, 106, 122, 0.12);
  color: var(--color-learn);
  font-size: 0.68rem;
  font-weight: 800;
  line-height: 1.3;
  white-space: nowrap;
}

.stage-title {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stage-count {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}

.stage-materials {
  display: grid;
  gap: 1px;
  padding: 1px 0 2px 10px;
}

/* 资料条目：单行缩进 */
.doc-material-link {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  border-left: 3px solid transparent;
  background: transparent;
  transition: background 120ms var(--ease-out), border-color 120ms var(--ease-out);
  line-height: 1.25;
  cursor: pointer;
}

.doc-material-link:hover {
  background: rgba(45, 106, 122, 0.05);
  border-left-color: rgba(45, 106, 122, 0.22);
}

.doc-material-link.active {
  background: var(--color-learn-bg);
  border-left-color: var(--color-learn);
}

.doc-material-link .material-type {
  flex: 0 0 auto;
  min-width: 28px;
  padding: 0 4px;
  border-radius: 3px;
  background: #ece7db;
  color: var(--color-text-muted);
  font-size: 0.64rem;
  font-weight: 800;
  letter-spacing: 0.02em;
  line-height: 1.4;
  text-align: center;
}

.doc-material-link.active .material-type {
  background: rgba(45, 106, 122, 0.14);
  color: var(--color-learn);
}

.doc-material-link strong {
  flex: 1 1 auto;
  min-width: 0;
  color: var(--color-text);
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-material-link.active strong {
  color: var(--color-learn);
  font-weight: 700;
}

.doc-material-link small {
  flex: 0 0 auto;
  max-width: 42%;
  color: var(--color-text-muted);
  font-size: 0.68rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.materials-empty-small {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  line-height: 1.45;
}

.material-type {
  color: var(--color-learn);
  font-size: 0.72rem;
  font-weight: 900;
}

.rail-note {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.7;
  font-size: 0.88rem;
  text-wrap: pretty;
}

.empty-state {
  text-align: center;
  padding: 4rem 1.5rem;
  color: var(--color-text-muted);
}

.empty-state p {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-secondary);
}

.empty-state-hint {
  margin-top: 8px !important;
  font-size: 0.88rem !important;
  font-weight: 400 !important;
  color: var(--color-text-muted) !important;
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

.guide-open-link {
  display: inline-flex;
  justify-content: center;
  width: 100%;
  margin-top: 4px;
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
}
</style>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCourseDetail, type CourseDetail } from '@/api/course'
import type { Material } from '@/api/material'
import { resolveFileUrl } from '@/utils/url'
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'

const route = useRoute()
const router = useRouter()
const courseId = computed(() => Number(route.params.courseId))
const course = ref<CourseDetail | null>(null)
const loading = ref(true)
const activeStageId = ref<number | null>(null)

const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)

function previewMaterial(material: Material) {
  selectedMaterial.value = material
  previewVisible.value = true
}

function materialUrl(fileId?: number | null, url?: string) {
  if (fileId) return resolveFileUrl(`/api/files/${fileId}`)
  return resolveFileUrl(url || '')
}

const allStages = computed(() => course.value?.stages || [])
const totalMaterials = computed(() => {
  if (!course.value) return 0
  return (
    course.value.stages.reduce((sum, s) => sum + s.materials.length, 0) +
    course.value.uncategorized_materials.length
  )
})

function scrollToStage(stageId: number | null) {
  activeStageId.value = stageId
  const elId = stageId === null ? 'stage-uncategorized' : `stage-${stageId}`
  const el = document.getElementById(elId)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function openMaterial(fileId?: number | null, url?: string) {
  const href = materialUrl(fileId, url)
  if (!href) {
    ElMessage.warning('该资料暂无可访问的链接')
    return
  }
  window.open(href, '_blank', 'noopener')
}

async function loadCourse() {
  loading.value = true
  try {
    const detail = await getCourseDetail(courseId.value)
    course.value = detail
    if (detail.stages?.length) {
      activeStageId.value = detail.stages[0]?.id ?? null
    }
  } catch {
    ElMessage.error('课程加载失败，请检查网络后刷新重试')
  } finally {
    loading.value = false
  }
}

const observer = ref<IntersectionObserver | null>(null)

function setupScrollSpy() {
  observer.value?.disconnect()
  const sections = document.querySelectorAll('.stage-section')
  if (sections.length === 0) return

  observer.value = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const id = Number(entry.target.id.replace('stage-', ''))
          if (id && id !== activeStageId.value) {
            activeStageId.value = id
          }
          break
        }
      }
    },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0 }
  )
  const obs = observer.value
  if (!obs) return
  sections.forEach((el) => obs.observe(el))
}

watch(course, () => {
  if (course.value) nextTick(setupScrollSpy)
})

onMounted(loadCourse)
onUnmounted(() => observer.value?.disconnect())
</script>

<template>
  <div class="course-detail-page">
    <section class="course-hero">
      <div class="container">
        <button class="back-btn" @click="router.push('/learn')">
          <span class="back-arrow">←</span>
          <span>返回课程列表</span>
        </button>
        <div v-if="course" class="course-heading">
          <h1>{{ course.name }}</h1>
          <p class="course-desc">{{ course.description || '本课程暂无详细介绍。' }}</p>
          <p class="hero-meta">📄 {{ totalMaterials }} 份学习资料</p>
        </div>
      </div>
    </section>

    <div class="container detail-layout">
      <aside class="sidebar">
        <h3>课程目录</h3>
        <div
          v-for="(stage, index) in allStages"
          :key="stage.id"
          class="toc-item"
          :class="{ active: stage.id === activeStageId }"
          @click="scrollToStage(stage.id)"
        >
          <span class="toc-num">{{ index + 1 }}</span>
          <span>{{ stage.name }}</span>
        </div>
        <div
          v-if="course?.uncategorized_materials?.length"
          class="toc-item"
          :class="{ active: activeStageId === null }"
          @click="scrollToStage(null)"
        >
          <span class="toc-num">+</span>
          <span>未分类资料</span>
        </div>
      </aside>

      <main class="main-content">
        <div
          v-for="(stage, index) in allStages"
          :id="`stage-${stage.id}`"
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

        <div v-if="course?.uncategorized_materials.length" id="stage-uncategorized" class="stage-section">
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

        <div v-if="!allStages.length && !course?.uncategorized_materials.length" class="empty-state">
          该课程暂无学习资料。
        </div>
      </main>
    </div>

    <MaterialPreviewDialog v-model:visible="previewVisible" :material="selectedMaterial" />
  </div>
</template>

<style scoped>
.course-detail-page { padding-top: 60px; }
.course-hero { padding: 3rem 0; background: var(--color-learn-bg); border-bottom: 1px solid var(--color-border-light); }
.container { max-width: 1200px; margin: 0 auto; padding: 0 1.5rem; }
.back-btn { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 1.5rem; padding: 8px 14px; color: var(--color-learn); background: rgba(45, 106, 122, 0.08); border: 1px solid rgba(45, 106, 122, 0.18); border-radius: var(--radius-full); font-weight: 700; transition: all 0.2s; }
.back-btn:hover { background: rgba(45, 106, 122, 0.14); transform: translateX(-2px); }
.back-arrow { font-size: 1.15rem; line-height: 1; }
.course-heading h1 { font-size: 2rem; font-weight: 800; font-family: var(--font-serif); letter-spacing: 0.05em; color: var(--color-text); margin-bottom: 0.75rem; }
.course-desc { color: var(--color-text-secondary); max-width: 720px; line-height: 1.8; margin-bottom: 1rem; }
.hero-meta { color: var(--color-text-secondary); font-size: 0.95rem; }
.detail-layout { display: flex; gap: 1.5rem; padding: 2rem 0 4rem; }
.sidebar { position: sticky; top: 80px; width: 180px; flex-shrink: 0; align-self: flex-start; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 1rem; }
.sidebar h3 { font-size: 0.9rem; color: var(--color-text-muted); margin-bottom: 0.75rem; font-weight: 600; }
.toc-item { display: flex; align-items: center; gap: 8px; padding: 0.55rem 0.6rem; border-radius: var(--radius-sm); cursor: pointer; color: var(--color-text-secondary); font-size: 0.88rem; transition: all 0.2s; margin-bottom: 4px; }
.toc-item:hover { background: var(--color-bg-alt); color: var(--color-text); }
.toc-item.active { background: rgba(45, 106, 122, 0.1); color: var(--color-learn); font-weight: 600; }
.toc-num { width: 22px; height: 22px; border-radius: 50%; background: var(--color-border); color: var(--color-text-muted); display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }
.toc-item.active .toc-num { background: var(--color-learn); color: #fff; }
.main-content { flex: 1; min-width: 0; }
.stage-section { margin-bottom: 2.5rem; scroll-margin-top: 100px; }
.stage-section h2 { font-size: 1.25rem; font-weight: 700; color: var(--color-text); margin-bottom: 1rem; }
.stage-badge { font-size: 0.7rem; font-weight: 700; padding: 0.2rem 0.6rem; background: var(--color-learn); color: #fff; border-radius: var(--radius-full); margin-right: 0.5rem; }
.material-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.25rem; }
.material-card { display: block; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 1.25rem; transition: all 0.35s ease; cursor: pointer; }
.material-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: rgba(45, 106, 122, 0.2); }
.material-type { font-size: 0.7rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: var(--radius-full); display: inline-block; margin-bottom: 0.75rem; background: rgba(107, 76, 138, 0.1); color: #6b4c8a; }
.material-card h3 { font-size: 1.05rem; font-weight: 700; margin-bottom: 0.35rem; color: var(--color-text); }
.material-card p { font-size: 0.85rem; color: var(--color-text-muted); }
.stage-empty { color: var(--color-text-muted); font-size: 0.9rem; padding: 2rem 0; text-align: center; background: var(--color-bg-alt); border-radius: var(--radius-md); border: 1px dashed var(--color-border); }
.empty-state { text-align: center; padding: 4rem 0; color: var(--color-text-muted); }
@media (max-width: 900px) { .detail-layout { flex-direction: column; } .sidebar { position: relative; top: 0; width: 100%; } .material-grid { grid-template-columns: 1fr; } }
</style>

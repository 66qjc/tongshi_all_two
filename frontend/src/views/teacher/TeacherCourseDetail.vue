<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCourseStage,
  deleteCourseStage,
  getCourseDetail,
  type CourseDetail,
  type CourseStage,
  updateCourse,
  updateCourseStage,
} from '@/api/course'
import type { Material } from '@/api/material'
import { createMaterial, deleteMaterial, getCourseContents, updateMaterial, rebuildMaterialPreview } from '@/api/material'
import { useUploadWithProgress } from '@/composables/useUploadWithProgress'
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'
import {
  createLesson,
  deleteLesson,
  getLessons,
  reorderLessons,
  updateLesson,
  type Lesson,
  type LessonCreatePayload,
  type LessonUpdatePayload,
} from '@/api/lesson'
import { getCourseAnalytics, type CourseAnalytics } from '@/api/progress'

const LessonEditor = defineAsyncComponent(() => import('@/components/lesson/LessonEditor.vue'))

type LessonEditorExpose = {
  insertMaterialPlaceholder: (materialId: number, materialType: 'video' | 'pdf') => void
}

const route = useRoute()
const router = useRouter()
const courseId = computed(() => Number(route.params.courseId))
const course = ref<CourseDetail | null>(null)
const loading = ref(true)

const { uploading, percent: uploadPercent, upload } = useUploadWithProgress()
const uploadInput = ref<HTMLInputElement | null>(null)

// 课程信息编辑
const courseDialogVisible = ref(false)
const courseForm = reactive({ name: '', description: '' })
const savingCourse = ref(false)

// 阶段管理
const newStageName = ref('')
const newStageOrder = ref(0)
const savingStage = ref(false)

// 资料上传/编辑
const materialDialogVisible = ref(false)
const isEditMaterial = ref(false)
const editingMaterialId = ref<number | null>(null)
const defaultStageId = ref<number | null>(null)
const UNCATEGORIZED_STAGE_VALUE = 'uncategorized'
const materialForm = reactive<{
  title: string
  type: 'video' | 'pdf'
  stage_id: number | typeof UNCATEGORIZED_STAGE_VALUE
  file: File | null
}>({
  title: '',
  type: 'video',
  stage_id: UNCATEGORIZED_STAGE_VALUE,
  file: null,
})

// 标签页
const activeTab = ref<'materials' | 'lessons' | 'analytics'>('materials')

// 课时管理
const lessons = ref<Lesson[]>([])
const lessonLoading = ref(false)
const lessonDialogVisible = ref(false)
const isEditLesson = ref(false)
const editingLessonId = ref<number | null>(null)
const lessonForm = reactive<{
  title: string
  content: string
  status: 'draft' | 'published'
  sort_order: number | undefined
}>({
  title: '',
  content: '',
  status: 'draft',
  sort_order: undefined,
})
const savingLesson = ref(false)
const lessonEditorRef = ref<LessonEditorExpose | null>(null)

// 学习分析
const analytics = ref<CourseAnalytics | null>(null)
const analyticsLoading = ref(false)
const analyticsPage = ref(1)
const analyticsPageSize = ref(20)

// 资料选择器
const materialSelectorVisible = ref(false)
const courseMaterials = ref<Material[]>([])
const materialSelectorLoading = ref(false)

const totalMaterials = computed(() => {
  if (!course.value) return 0
  return (
    course.value.stages.reduce((sum, s) => sum + s.materials.length, 0) +
    course.value.uncategorized_materials.length
  )
})

const sortedStages = computed(() => {
  if (!course.value) return []
  return [...course.value.stages].sort((a, b) => a.sort_order - b.sort_order)
})

const sortedLessons = computed(() => {
  return [...lessons.value].sort((a, b) => a.sort_order - b.sort_order)
})

function formatFileSize(bytes: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size >= 10 || index === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[index]}`
}

async function loadCourse() {
  loading.value = true
  try {
    const detail = await getCourseDetail(courseId.value)
    course.value = detail
  } catch {
    ElMessage.error('课程详情加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function loadLessons() {
  lessonLoading.value = true
  try {
    lessons.value = await getLessons(courseId.value)
  } catch {
    ElMessage.error('课时列表加载失败，请稍后重试')
  } finally {
    lessonLoading.value = false
  }
}

function openEditCourse() {
  if (!course.value) return
  courseForm.name = course.value.name
  courseForm.description = course.value.description || ''
  courseDialogVisible.value = true
}

async function handleSaveCourse() {
  const name = courseForm.name.trim()
  if (!name) {
    ElMessage.warning('请输入课程名称')
    return
  }
  savingCourse.value = true
  try {
    await updateCourse(courseId.value, { name, description: courseForm.description.trim() })
    ElMessage.success('课程信息更新成功')
    courseDialogVisible.value = false
    await loadCourse()
  } catch {
    ElMessage.error('更新失败，请稍后重试')
  } finally {
    savingCourse.value = false
  }
}

async function handleAddStage() {
  const name = newStageName.value.trim()
  if (!name) {
    ElMessage.warning('请输入阶段名称')
    return
  }
  savingStage.value = true
  try {
    await createCourseStage(courseId.value, { name, sort_order: newStageOrder.value })
    ElMessage.success('阶段添加成功')
    newStageName.value = ''
    newStageOrder.value = sortedStages.value.length
    await loadCourse()
  } catch {
    ElMessage.error('添加失败，请稍后重试')
  } finally {
    savingStage.value = false
  }
}

async function handleStageNameChange(stage: CourseStage) {
  const name = stage.name.trim()
  if (!name) {
    ElMessage.warning('阶段名称不能为空')
    await loadCourse()
    return
  }
  try {
    await updateCourseStage(stage.id, { name, sort_order: stage.sort_order })
    ElMessage.success('阶段已更新')
  } catch {
    ElMessage.error('更新失败，请稍后重试')
    await loadCourse()
  }
}

async function handleStageOrderChange(stage: CourseStage) {
  try {
    await updateCourseStage(stage.id, { name: stage.name, sort_order: stage.sort_order })
    await loadCourse()
  } catch {
    ElMessage.error('排序更新失败')
    await loadCourse()
  }
}

async function handleDeleteStage(stage: CourseStage) {
  if (stage.materials.length > 0) {
    ElMessage.warning('该阶段下仍有资料。请先编辑这些资料，将所属阶段改为「未分类」或其他阶段，或删除资料。')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除阶段「${stage.name}」？`, '删除确认', { type: 'warning' })
    await deleteCourseStage(stage.id)
    ElMessage.success('已删除')
    await loadCourse()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

const previewVisible = ref(false)
const selectedMaterial = ref<Material | null>(null)

function previewMaterial(material: Material) {
  selectedMaterial.value = material
  previewVisible.value = true
}

async function handleRebuildPreview(material: Material) {
  try {
    await rebuildMaterialPreview(material.id)
    ElMessage.success('预览已重新生成')
    await loadCourse()
  } catch {
    ElMessage.error('预览重建失败，请稍后重试')
  }
}

function resetMaterialForm() {
  materialForm.title = ''
  materialForm.type = 'video'
  materialForm.stage_id = defaultStageId.value ?? UNCATEGORIZED_STAGE_VALUE
  materialForm.file = null
  if (uploadInput.value) uploadInput.value.value = ''
}

function openUploadMaterial(stageId: number | null = null) {
  isEditMaterial.value = false
  editingMaterialId.value = null
  defaultStageId.value = stageId
  resetMaterialForm()
  materialDialogVisible.value = true
}

function openEditMaterial(material: Material) {
  isEditMaterial.value = true
  editingMaterialId.value = material.id
  materialForm.title = material.title
  materialForm.type = material.type as 'video' | 'pdf'
  materialForm.stage_id = material.stage_id ?? UNCATEGORIZED_STAGE_VALUE
  materialForm.file = null
  materialDialogVisible.value = true
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  materialForm.file = input.files?.[0] || null
}

async function handleSaveMaterial() {
  const title = materialForm.title.trim()
  if (!title) {
    ElMessage.warning('请填写资料标题')
    return
  }
  if (isEditMaterial.value && editingMaterialId.value) {
    try {
      await updateMaterial(editingMaterialId.value, {
        title,
        stage_id: materialForm.stage_id === UNCATEGORIZED_STAGE_VALUE ? null : materialForm.stage_id,
      })
      ElMessage.success('资料更新成功')
      materialDialogVisible.value = false
      await loadCourse()
    } catch {
      ElMessage.error('更新失败，请稍后重试')
    }
    return
  }
  if (!materialForm.file) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  try {
    let uploaded
    try {
      uploaded = await upload(materialForm.file, 'material')
    } catch {
      ElMessage.error('文件上传失败，请检查文件后重试')
      return
    }
    try {
      await createMaterial({
        course_id: courseId.value,
        type: materialForm.type,
        title,
        url: uploaded.url,
        size: formatFileSize(uploaded.size),
        file_id: uploaded.file_id,
        stage_id: materialForm.stage_id === UNCATEGORIZED_STAGE_VALUE ? null : materialForm.stage_id,
      })
    } catch {
      ElMessage.error('资料记录创建失败，文件已上传但资料未保存，请重试')
      return
    }
    ElMessage.success('资料上传成功')
    materialDialogVisible.value = false
    await loadCourse()
  } catch {
    ElMessage.error('上传失败，请稍后重试')
  }
}

async function handleDeleteMaterial(material: Material) {
  try {
    await ElMessageBox.confirm(`确定删除资料「${material.title}」？这只会删除本课程副本中的资料，不影响公共课程源内容。`, '删除确认', { type: 'warning' })
    await deleteMaterial(material.id)
    ElMessage.success('已删除')
    await loadCourse()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

// ── 课时管理 ──

function resetLessonForm() {
  lessonForm.title = ''
  lessonForm.content = ''
  lessonForm.status = 'draft'
  lessonForm.sort_order = undefined
}

function openCreateLesson() {
  isEditLesson.value = false
  editingLessonId.value = null
  resetLessonForm()
  lessonDialogVisible.value = true
}

function openEditLesson(lesson: Lesson) {
  isEditLesson.value = true
  editingLessonId.value = lesson.id
  lessonForm.title = lesson.title
  lessonForm.content = lesson.content || ''
  lessonForm.status = lesson.status
  lessonForm.sort_order = lesson.sort_order
  lessonDialogVisible.value = true
}

async function handleSaveLesson() {
  const title = lessonForm.title.trim()
  if (!title) {
    ElMessage.warning('请输入课时标题')
    return
  }

  const basePayload = {
    title,
    content: lessonForm.content,
    status: lessonForm.status,
    sort_order: lessonForm.sort_order,
  }

  savingLesson.value = true
  try {
    if (isEditLesson.value && editingLessonId.value) {
      const updatePayload: LessonUpdatePayload = basePayload
      await updateLesson(editingLessonId.value, updatePayload)
      ElMessage.success('课时更新成功')
    } else {
      const createPayload: LessonCreatePayload = basePayload
      await createLesson(courseId.value, createPayload)
      ElMessage.success('课时创建成功')
    }
    lessonDialogVisible.value = false
    resetLessonForm()
    await loadLessons()
  } catch {
    ElMessage.error(isEditLesson.value ? '更新失败，请稍后重试' : '创建失败，请稍后重试')
  } finally {
    savingLesson.value = false
  }
}

async function handleDeleteLesson(lesson: Lesson) {
  try {
    await ElMessageBox.confirm(`确定删除课时「${lesson.title}」？删除后不可恢复。`, '删除确认', { type: 'warning' })
    await deleteLesson(lesson.id)
    ElMessage.success('已删除')
    await loadLessons()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

async function handleReorderLessons() {
  const items = sortedLessons.value.map((lesson, index) => ({
    id: lesson.id,
    sort_order: index,
  }))
  try {
    await reorderLessons(courseId.value, items)
    ElMessage.success('排序已保存')
    await loadLessons()
  } catch {
    ElMessage.error('排序保存失败，请稍后重试')
  }
}

// ── 资料选择器 ──

async function openMaterialSelector() {
  materialSelectorVisible.value = true
  materialSelectorLoading.value = true
  try {
    courseMaterials.value = await getCourseContents(courseId.value)
  } catch {
    ElMessage.error('资料列表加载失败，请稍后重试')
  } finally {
    materialSelectorLoading.value = false
  }
}

function handleInsertMaterial(material: Material) {
  if (material.type === 'link') {
    ElMessage.warning('链接资料暂不支持嵌入课时正文，可在资料区查看。')
    materialSelectorVisible.value = false
    return
  }
  lessonEditorRef.value?.insertMaterialPlaceholder(material.id, material.type)
  materialSelectorVisible.value = false
}

function formatDuration(seconds: number) {
  if (!seconds) return '0 分钟'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`
}

async function loadAnalytics() {
  analyticsLoading.value = true
  try {
    const result = await getCourseAnalytics(
      courseId.value,
      analyticsPage.value,
      analyticsPageSize.value,
    )
    analytics.value = result
    analyticsPage.value = result.student_progress.page
    analyticsPageSize.value = result.student_progress.page_size
  } catch {
    ElMessage.error('学习分析加载失败，请稍后重试')
  } finally {
    analyticsLoading.value = false
  }
}

function handleAnalyticsPageChange(page: number) {
  analyticsPage.value = page
  void loadAnalytics()
}

function handleAnalyticsPageSizeChange(pageSize: number) {
  analyticsPageSize.value = pageSize
  analyticsPage.value = 1
  void loadAnalytics()
}

onMounted(() => {
  loadCourse()
  loadLessons()
  loadAnalytics()
})
</script>

<template>
  <div class="course-detail-manage-page" v-loading="loading">
    <div class="page-header">
      <div class="header-left">
        <el-button text @click="router.push('/teacher/courses')">← 返回课程管理</el-button>
        <h1>{{ course?.name || '课程详情' }}</h1>
      </div>
      <el-button type="primary" :disabled="!course" @click="openEditCourse">编辑课程信息</el-button>
    </div>

    <div v-if="course" class="course-info-card">
      <p class="course-desc">{{ course.description || '暂无课程简介' }}</p>
      <div class="course-stats">
        <span>📄 {{ totalMaterials }} 份资料</span>
        <span>📑 {{ sortedStages.length }} 个阶段</span>
        <span>📝 {{ course.question_count }} 道题目</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="资料" name="materials">
        <div class="section-card">
          <div class="section-header">
            <h2>课程阶段 / 目录</h2>
            <div class="stage-add">
              <el-input v-model="newStageName" placeholder="新阶段名称" style="width: 200px" />
              <el-input-number v-model="newStageOrder" :min="0" :step="1" step-strictly controls-position="right" style="width: 100px" />
              <el-button type="primary" :loading="savingStage" @click="handleAddStage">添加阶段</el-button>
            </div>
          </div>
          <el-empty v-if="sortedStages.length === 0" description="暂无阶段，可在上方添加" />
          <div v-else class="stage-list">
            <div v-for="stage in sortedStages" :key="stage.id" class="stage-row">
              <el-input v-model="stage.name" style="width: 240px" @change="handleStageNameChange(stage)" />
              <el-input-number v-model="stage.sort_order" :min="0" :step="1" step-strictly controls-position="right" style="width: 100px" @change="handleStageOrderChange(stage)" />
              <span class="stage-meta">{{ stage.materials.length }} 份资料</span>
              <el-button type="primary" size="small" @click="openUploadMaterial(stage.id)">上传资料</el-button>
              <el-button type="danger" text size="small" @click="handleDeleteStage(stage)">删除</el-button>
            </div>
          </div>
        </div>

        <div class="section-card materials-section">
          <div class="section-header">
            <h2>阶段资料</h2>
            <el-button type="primary" @click="openUploadMaterial(null)">上传新资料</el-button>
          </div>
            <div v-for="stage in sortedStages" :key="`m-${stage.id}`" class="stage-materials">
            <h3><span class="stage-tag">阶段</span>{{ stage.name }}</h3>
            <div v-if="stage.materials.length" class="material-flat-list">
              <MaterialRichCard
                v-for="material in stage.materials"
                :key="material.id"
                :material="material"
                manage
                compact
                @preview="previewMaterial"
                @edit="openEditMaterial"
                @delete="handleDeleteMaterial"
                @rebuild="handleRebuildPreview"
              />
            </div>
            <el-empty v-else description="该阶段暂无资料" :image-size="80" />
          </div>

          <div v-if="course && course.uncategorized_materials.length" class="stage-materials">
            <h3><span class="stage-tag other">其他</span>未分类资料</h3>
            <div class="material-flat-list">
              <MaterialRichCard
                v-for="material in course.uncategorized_materials"
                :key="material.id"
                :material="material"
                manage
                compact
                @preview="previewMaterial"
                @edit="openEditMaterial"
                @delete="handleDeleteMaterial"
                @rebuild="handleRebuildPreview"
              />
            </div>
          </div>

          <el-empty v-if="!sortedStages.length && !course?.uncategorized_materials.length" description="暂无资料" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="课时" name="lessons">
        <div class="section-card lessons-section">
          <div class="section-header">
            <h2>课时管理</h2>
            <el-button type="primary" @click="openCreateLesson">新增课时</el-button>
          </div>

          <el-table :data="sortedLessons" v-loading="lessonLoading" stripe size="small" style="width: 100%">
            <el-table-column label="排序号" width="120" align="center">
              <template #default="{ row }">
                <el-input-number v-model="row.sort_order" :min="0" :step="1" step-strictly controls-position="right" style="width: 90px" />
              </template>
            </el-table-column>
            <el-table-column prop="title" label="课时标题" min-width="200" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
                  {{ row.status === 'published' ? '已发布' : '草稿' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" align="center">
              <template #default="{ row }">
                <el-button type="primary" text size="small" @click="openEditLesson(row)">编辑</el-button>
                <el-button type="danger" text size="small" @click="handleDeleteLesson(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="sortedLessons.length" class="lesson-actions">
            <el-button type="primary" size="small" @click="handleReorderLessons">保存排序</el-button>
          </div>

          <el-empty v-if="!sortedLessons.length && !lessonLoading" description="暂无课时，可点击右上角新增" />
        </div>
      </el-tab-pane>


      <el-tab-pane label="学习分析" name="analytics">
        <div class="section-card analytics-section" v-loading="analyticsLoading">
          <div class="section-header">
            <h2>课程学习分析</h2>
            <el-button size="small" @click="loadAnalytics">刷新数据</el-button>
          </div>

          <div v-if="analytics" class="analytics-overview">
            <div class="analytics-card">
              <span class="analytics-label">班级学生数</span>
              <strong>{{ analytics.student_count }}</strong>
            </div>
            <div class="analytics-card">
              <span class="analytics-label">课时数</span>
              <strong>{{ analytics.lesson_count }}</strong>
            </div>
            <div class="analytics-card">
              <span class="analytics-label">整体完成率</span>
              <strong>{{ analytics.avg_completion_rate }}%</strong>
            </div>
            <div class="analytics-card">
              <span class="analytics-label">平均学习时长</span>
              <strong>{{ formatDuration(analytics.avg_duration) }}</strong>
            </div>
          </div>

          <el-table
            v-if="analytics"
            :data="analytics.student_progress.items"
            stripe
            size="small"
            class="student-progress-table"
            empty-text="暂无学生学习进度"
          >
            <el-table-column prop="student_name" label="学生" min-width="140" />
            <el-table-column prop="student_id" label="学号" min-width="120" />
            <el-table-column label="完成课时" min-width="120">
              <template #default="{ row }">
                {{ row.completed_lessons }} / {{ row.total_lessons }}
              </template>
            </el-table-column>
            <el-table-column label="完成率" min-width="140">
              <template #default="{ row }">
                <el-progress :percentage="row.completion_rate" :stroke-width="8" />
              </template>
            </el-table-column>
            <el-table-column label="学习时长" min-width="120">
              <template #default="{ row }">{{ formatDuration(row.duration_seconds) }}</template>
            </el-table-column>
            <el-table-column label="疑似刷课" min-width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.fast_completion_count > 0 ? 'danger' : 'success'" size="small">
                  {{ row.fast_completion_count > 0 ? `${row.fast_completion_count} 次` : '无' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <div
            v-if="analytics && analytics.student_progress.total > 0"
            class="analytics-pagination"
          >
            <el-pagination
              v-model:current-page="analyticsPage"
              v-model:page-size="analyticsPageSize"
              :page-sizes="[20, 50, 100]"
              :total="analytics.student_progress.total"
              :disabled="analyticsLoading"
              layout="total, sizes, prev, pager, next, jumper"
              @current-change="handleAnalyticsPageChange"
              @size-change="handleAnalyticsPageSizeChange"
            />
          </div>

          <div v-if="analytics" class="analytics-columns">
            <div class="analytics-list">
              <h3>热门课时</h3>
              <el-empty v-if="analytics.most_viewed_lessons.length === 0" description="暂无课时浏览数据" :image-size="80" />
              <div v-for="item in analytics.most_viewed_lessons" :key="`hot-${item.lesson_id}`" class="analytics-list-item">
                <span>{{ item.title }}</span>
                <small>浏览 {{ item.view_count }} 次，平均进度 {{ item.avg_progress_percent }}%</small>
              </div>
            </div>
            <div class="analytics-list">
              <h3>低完成课时</h3>
              <el-empty v-if="analytics.low_completion_lessons.length === 0" description="暂无低完成课时" :image-size="80" />
              <div v-for="item in analytics.low_completion_lessons" :key="`low-${item.lesson_id}`" class="analytics-list-item warning">
                <span>{{ item.title }}</span>
                <small>完成率 {{ item.completion_rate }}%，疑似刷课 {{ item.fast_completion_count }} 次</small>
              </div>
            </div>
          </div>

          <el-empty v-if="!analytics && !analyticsLoading" description="暂无学习分析数据" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 编辑课程信息 -->
    <el-dialog v-model="courseDialogVisible" title="编辑课程信息" width="520px">
      <div class="form-group">
        <label>课程名称</label>
        <el-input v-model="courseForm.name" placeholder="请输入课程名称" maxlength="100" show-word-limit />
      </div>
      <div class="form-group">
        <label>课程简介</label>
        <el-input v-model="courseForm.description" type="textarea" :rows="4" placeholder="请输入课程简介（可选）" maxlength="500" show-word-limit />
      </div>
      <template #footer>
        <el-button @click="courseDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingCourse" @click="handleSaveCourse">保存</el-button>
      </template>
    </el-dialog>

    <!-- 上传/编辑资料 -->
    <el-dialog v-model="materialDialogVisible" :title="isEditMaterial ? '编辑资料' : '上传资料'" width="520px">
      <div class="form-group">
        <label>资料标题</label>
        <el-input v-model="materialForm.title" placeholder="请输入资料标题" maxlength="128" show-word-limit />
      </div>
      <div v-if="!isEditMaterial" class="form-group">
        <label>资料类型</label>
        <el-radio-group v-model="materialForm.type" size="large">
          <el-radio-button value="video">视频</el-radio-button>
          <el-radio-button value="pdf">PDF</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>所属阶段</label>
        <el-select v-model="materialForm.stage_id" placeholder="未分类" clearable style="width: 100%">
          <el-option label="未分类" :value="UNCATEGORIZED_STAGE_VALUE" />
          <el-option v-for="stage in sortedStages" :key="stage.id" :label="stage.name" :value="stage.id" />
        </el-select>
      </div>
      <div v-if="!isEditMaterial" class="form-group">
        <label>文件</label>
        <input ref="uploadInput" type="file" accept=".pdf,video/*" hidden @change="handleFileChange" />
        <div class="upload-zone" @click="uploadInput?.click()">
          <span v-if="!materialForm.file">点击选择要上传的文件</span>
          <span v-else class="file-name">{{ materialForm.file.name }}</span>
        </div>
        <el-progress v-if="uploading" :percentage="uploadPercent" style="margin-top: 12px" />
      </div>
      <template #footer>
        <el-button @click="materialDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleSaveMaterial">{{ isEditMaterial ? '保存' : '上传' }}</el-button>
      </template>
    </el-dialog>

    <!-- 新增/编辑课时 -->
    <el-dialog v-model="lessonDialogVisible" :title="isEditLesson ? '编辑课时' : '新增课时'" width="760px" top="5vh">
      <div class="form-group">
        <label>课时标题</label>
        <el-input v-model="lessonForm.title" placeholder="请输入课时标题" maxlength="200" show-word-limit />
      </div>
      <div class="form-group">
        <label>状态</label>
        <el-select v-model="lessonForm.status" placeholder="请选择状态" style="width: 200px">
          <el-option label="草稿" value="draft" />
          <el-option label="已发布" value="published" />
        </el-select>
      </div>
      <div class="form-group">
        <label>排序号（留空则自动放到末尾）</label>
        <el-input-number v-model="lessonForm.sort_order" :min="0" :step="1" step-strictly controls-position="right" placeholder="自动" style="width: 160px" />
      </div>
      <div class="form-group">
        <div class="editor-label-row">
          <label>课时内容</label>
          <el-button type="primary" size="small" @click="openMaterialSelector">插入资料</el-button>
        </div>
        <LessonEditor ref="lessonEditorRef" v-model="lessonForm.content" @insert-material="openMaterialSelector" />
      </div>
      <template #footer>
        <el-button @click="lessonDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingLesson" @click="handleSaveLesson">保存</el-button>
      </template>
    </el-dialog>

    <!-- 资料选择器 -->
    <el-dialog v-model="materialSelectorVisible" title="选择要插入的资料" width="620px">
      <div v-loading="materialSelectorLoading" class="material-selector-list">
        <el-empty v-if="!courseMaterials.length && !materialSelectorLoading" description="暂无可插入的资料" />
        <div
          v-for="material in courseMaterials"
          :key="material.id"
          class="material-selector-item"
          @click="handleInsertMaterial(material)"
        >
          <div class="material-info">
            <span class="material-title">{{ material.title }}</span>
            <el-tag size="small" :type="material.type === 'video' ? 'primary' : 'warning'">
              {{ material.type === 'video' ? '视频' : 'PDF' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-dialog>

    <MaterialPreviewDialog v-model:visible="previewVisible" :material="selectedMaterial" />
  </div>
</template>

<style scoped>
.course-detail-manage-page { padding: var(--space-lg); }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-lg); }
.header-left { display: flex; align-items: center; gap: var(--space-md); }
.page-header h1 { font-size: 1.5rem; font-weight: 800; color: var(--color-text); font-family: var(--font-serif); letter-spacing: 0.05em; margin: 0; }
.course-info-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-lg); margin-bottom: var(--space-lg); }
.course-desc { color: var(--color-text-secondary); line-height: 1.8; margin-bottom: var(--space-md); }
.course-stats { display: flex; gap: var(--space-xl); color: var(--color-text-muted); font-size: 0.9rem; }
.section-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-lg); margin-bottom: var(--space-lg); }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-md); }
.section-header h2 { font-size: 1.1rem; font-weight: 700; color: var(--color-text); margin: 0; }
.stage-add { display: flex; align-items: center; gap: var(--space-sm); }
.stage-list { display: flex; flex-direction: column; gap: var(--space-sm); }
.stage-row { display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; padding: var(--space-sm); background: var(--color-bg-alt); border-radius: var(--radius-sm); }
.stage-meta { color: var(--color-text-muted); font-size: 0.85rem; flex: 1; }
.materials-section { min-height: 200px; }
.stage-materials { margin-bottom: var(--space-lg); }
.stage-materials h3 {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 var(--space-sm);
  display: flex;
  align-items: center;
}
.stage-tag { font-size: 0.65rem; padding: 0.15rem 0.5rem; background: var(--color-learn); color: #fff; border-radius: var(--radius-full); margin-right: var(--space-sm); }
.stage-tag.other { background: var(--color-text-muted); }
.scope-tag { margin-left: var(--space-sm); }
/* 阶段资料扁平列表：单列紧凑行，避免大卡片 + 长摘要把页面撑得过高 */
.material-flat-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.material-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-md); }
.material-card { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-md); background: var(--color-bg-card); transition: all 0.2s; }
.material-card:hover { box-shadow: var(--shadow-md); border-color: rgba(45, 106, 122, 0.2); }
.card-head { margin-bottom: var(--space-sm); }
.material-card h4 { font-size: 0.95rem; font-weight: 700; color: var(--color-text); margin: 0 0 var(--space-xs); line-height: 1.4; min-height: 2.8em; }
.material-meta { color: var(--color-text-muted); font-size: 0.8rem; margin-bottom: var(--space-sm); }
.card-actions { display: flex; gap: var(--space-xs); }
.form-group { margin-bottom: var(--space-lg); }
.form-group label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: var(--space-sm); }
.upload-zone { padding: var(--space-xl); border: 2px dashed var(--color-border); border-radius: var(--radius-md); text-align: center; color: var(--color-text-muted); cursor: pointer; }
.upload-zone:hover { border-color: var(--color-primary); color: var(--color-primary); }
.file-name { color: var(--color-text); }
.detail-tabs { margin-bottom: var(--space-lg); }
.lessons-section { min-height: 200px; }
.lesson-actions { display: flex; justify-content: flex-end; margin-top: var(--space-md); }
.analytics-section { min-height: 260px; }
.analytics-overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--space-md); margin-bottom: var(--space-lg); }
.analytics-card { padding: var(--space-md); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-alt); }
.analytics-label { display: block; color: var(--color-text-muted); font-size: 0.82rem; margin-bottom: var(--space-xs); }
.analytics-card strong { font-size: 1.35rem; color: var(--color-primary); }
.student-progress-table { margin-bottom: var(--space-md); }
.analytics-pagination { display: flex; justify-content: flex-end; overflow-x: auto; padding-bottom: 2px; margin-bottom: var(--space-lg); }
.analytics-columns { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--space-md); }
.analytics-list { border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-md); background: var(--color-bg-card); }
.analytics-list h3 { margin: 0 0 var(--space-md); font-size: 1rem; color: var(--color-text); }
.analytics-list-item { display: flex; flex-direction: column; gap: 4px; padding: var(--space-sm) 0; border-bottom: 1px solid var(--color-border-light); }
.analytics-list-item:last-child { border-bottom: none; }
.analytics-list-item span { font-weight: 700; color: var(--color-text); }
.analytics-list-item small { color: var(--color-text-muted); }
.analytics-list-item.warning span { color: #b88230; }
.editor-label-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-sm); }
.editor-label-row label { margin-bottom: 0; }
.material-selector-list { display: flex; flex-direction: column; gap: var(--space-sm); max-height: 420px; overflow-y: auto; }
.material-selector-item { padding: var(--space-md); border: 1px solid var(--color-border); border-radius: var(--radius-md); cursor: pointer; transition: all 0.2s; }
.material-selector-item:hover { border-color: var(--color-primary); background: var(--color-bg-alt); }
.material-info { display: flex; align-items: center; justify-content: space-between; gap: var(--space-sm); }
.material-title { font-weight: 500; color: var(--color-text); }
</style>

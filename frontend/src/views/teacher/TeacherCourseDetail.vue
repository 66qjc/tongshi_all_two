<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
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
import { createMaterial, deleteMaterial, updateMaterial, rebuildMaterialPreview } from '@/api/material'
import { useUploadWithProgress } from '@/composables/useUploadWithProgress'
import { resolveFileUrl } from '@/utils/url'
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'
import MaterialPreviewDialog from '@/components/common/MaterialPreviewDialog.vue'

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
const materialForm = reactive<{
  title: string
  type: 'video' | 'pdf'
  stage_id: number | null
  file: File | null
}>({
  title: '',
  type: 'video',
  stage_id: null,
  file: null,
})

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
    ElMessage.warning('该阶段下仍有资料，请先删除或移出资料')
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

function materialUrl(material: Material) {
  return resolveFileUrl(material.file_id ? `/api/files/${material.file_id}` : material.url)
}

function openMaterial(material: Material) {
  const url = materialUrl(material)
  if (!url) {
    ElMessage.warning('该资料暂无可访问文件')
    return
  }
  window.open(url, '_blank', 'noopener')
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
  materialForm.stage_id = defaultStageId.value
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
  materialForm.stage_id = material.stage_id ?? null
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
        stage_id: materialForm.stage_id,
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
        stage_id: materialForm.stage_id,
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
    await ElMessageBox.confirm(`确定删除资料「${material.title}」？这只会删除你课程里的这份资料，不会影响公共课程源内容。`, '删除确认', { type: 'warning' })
    await deleteMaterial(material.id)
    ElMessage.success('已删除')
    await loadCourse()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

onMounted(loadCourse)
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
        <div v-if="stage.materials.length" class="material-grid">
          <MaterialRichCard
            v-for="material in stage.materials"
            :key="material.id"
            :material="material"
            manage
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
        <div class="material-grid">
          <MaterialRichCard
            v-for="material in course.uncategorized_materials"
            :key="material.id"
            :material="material"
            manage
            @preview="previewMaterial"
            @edit="openEditMaterial"
            @delete="handleDeleteMaterial"
            @rebuild="handleRebuildPreview"
          />
        </div>
      </div>

      <el-empty v-if="!sortedStages.length && !course?.uncategorized_materials.length" description="暂无资料" />
    </div>

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
          <el-option label="未分类" :value="null" />
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
.stage-materials { margin-bottom: var(--space-xl); }
.stage-materials h3 { font-size: 1rem; font-weight: 700; color: var(--color-text); margin-bottom: var(--space-md); }
.stage-tag { font-size: 0.65rem; padding: 0.15rem 0.5rem; background: var(--color-learn); color: #fff; border-radius: var(--radius-full); margin-right: var(--space-sm); }
.stage-tag.other { background: var(--color-text-muted); }
.scope-tag { margin-left: var(--space-sm); }
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
</style>

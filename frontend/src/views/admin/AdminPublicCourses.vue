<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Material } from '../../api/material'
import PdfPreviewDialog from '../../components/common/PdfPreviewDialog.vue'
import { useUploadWithProgress } from '../../composables/useUploadWithProgress'
import {
  createAdminPublicCourse,
  createAdminPublicCourseStage,
  createAdminPublicMaterial,
  deleteAdminPublicCourse,
  deleteAdminPublicCourseStage,
  deleteAdminPublicMaterial,
  getAdminPublicCourseStages,
  getAdminPublicCourses,
  getAdminPublicMaterials,
  updateAdminPublicCourse,
  updateAdminPublicCourseStage,
  updateAdminPublicMaterial,
  type AdminCourseStage,
  type AdminPublicCourse,
} from '../../api/adminPublicCourse'

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

const courses = ref<AdminPublicCourse[]>([])
const selectedCourse = ref<AdminPublicCourse | null>(null)
const activeTab = ref<'stages' | 'materials'>('stages')

const courseLoading = ref(false)
const contentLoading = ref(false)
const saving = ref(false)
const { uploading, percent: uploadPercent, upload } = useUploadWithProgress()

const materials = ref<Material[]>([])
const stages = ref<AdminCourseStage[]>([])
const stageLoading = ref(false)
const newStageName = ref('')
const newStageOrder = ref(0)
const savingStage = ref(false)
const defaultStageId = ref<number | null>(null)

const showCourseDialog = ref(false)
const editingCourseId = ref<number | null>(null)
const courseForm = ref({ name: '' })

const showMaterialDialog = ref(false)
const editingMaterialId = ref<number | null>(null)
const uploadInput = ref<HTMLInputElement | null>(null)
const materialForm = ref({
  type: 'pdf' as 'video' | 'pdf',
  title: '',
  url: '',
  size: '0 MB',
  file_id: undefined as number | undefined,
  stage_id: '' as number | '',
  file: null as File | null,
})

const previewVisible = ref(false)
const previewUrl = ref('')
const previewFileId = ref<number | undefined>(undefined)

function previewMaterial(row: Material) {
  previewFileId.value = row.file_id
  previewUrl.value = row.url || ''
  previewVisible.value = true
}

const materialDialogTitle = computed(() => editingMaterialId.value ? '编辑公共资料' : '新增公共资料')

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

async function fetchCourses(keepCourseId?: number) {
  courseLoading.value = true
  try {
    courses.value = await getAdminPublicCourses() || []
    const nextId = keepCourseId || selectedCourse.value?.id
    selectedCourse.value = courses.value.find(course => course.id === nextId) || courses.value[0] || null
    if (selectedCourse.value) await fetchContent()
  } catch (err: any) {
    ElMessage.error(err?.message || '加载公共课程失败')
  } finally {
    courseLoading.value = false
  }
}

async function fetchContent() {
  if (!selectedCourse.value) {
    materials.value = []
    stages.value = []
    return
  }
  contentLoading.value = true
  stageLoading.value = true
  try {
    const courseId = selectedCourse.value.id
    const [materialData, stageData] = await Promise.all([
      getAdminPublicMaterials(courseId),
      getAdminPublicCourseStages(courseId),
    ])
    materials.value = materialData || []
    stages.value = stageData || []
  } catch (err: any) {
    ElMessage.error(err?.message || '加载课程内容失败')
  } finally {
    contentLoading.value = false
    stageLoading.value = false
  }
}

function selectCourse(course: AdminPublicCourse) {
  selectedCourse.value = course
  activeTab.value = 'stages'
  fetchContent()
}

function openCreateCourse() {
  editingCourseId.value = null
  courseForm.value = { name: '' }
  showCourseDialog.value = true
}

function openEditCourse(course: AdminPublicCourse) {
  editingCourseId.value = course.id
  courseForm.value = { name: course.name }
  showCourseDialog.value = true
}

async function saveCourse() {
  const name = courseForm.value.name.trim()
  if (!name) {
    ElMessage.warning('请填写公共课程名称')
    return
  }
  saving.value = true
  try {
    let courseId = editingCourseId.value
    if (courseId) {
      await updateAdminPublicCourse(courseId, { name })
      ElMessage.success('公共课程已更新')
    } else {
      const created = await createAdminPublicCourse({ name })
      courseId = created.id
      ElMessage.success('公共课程已创建')
    }
    showCourseDialog.value = false
    await fetchCourses(courseId || undefined)
  } catch (err: any) {
    ElMessage.error(err?.message || '保存公共课程失败')
  } finally {
    saving.value = false
  }
}

async function removeCourse(course: AdminPublicCourse) {
  try {
    await ElMessageBox.confirm(
      `确定删除公共课程「${course.name}」吗？共享题目不随课程删除、不转挂，仍保留在全站题库。教师已添加的课程副本不会被删除，但后续不再从该公共课程源同步资料和阶段。`,
      '删除公共课程',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
    await deleteAdminPublicCourse(course.id)
    ElMessage.success('公共课程已删除')
    await fetchCourses()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除公共课程失败')
  }
}

function openCreateMaterial(stageId: number | null = null) {
  if (!selectedCourse.value) return
  editingMaterialId.value = null
  defaultStageId.value = stageId
  materialForm.value = { type: 'pdf', title: '', url: '', size: '0 MB', file_id: undefined, stage_id: stageId ?? '', file: null }
  if (uploadInput.value) uploadInput.value.value = ''
  showMaterialDialog.value = true
}

function openEditMaterial(material: Material) {
  if (material.type === 'link') {
    ElMessage.warning('该链接资料来自公开学习内容源，本页仅维护上传文件；请到原创建入口修改链接。')
    return
  }
  editingMaterialId.value = material.id
  materialForm.value = {
    type: material.type,
    title: material.title,
    url: material.url || '',
    size: material.size || '0 MB',
    file_id: material.file_id,
    stage_id: material.stage_id ?? '',
    file: null,
  }
  if (uploadInput.value) uploadInput.value.value = ''
  showMaterialDialog.value = true
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] || null
  materialForm.value.file = file
  if (file) {
    materialForm.value.size = formatFileSize(file.size)
  }
}

async function saveMaterial() {
  if (!selectedCourse.value) return
  if (!materialForm.value.title.trim()) {
    ElMessage.warning('请填写资料标题')
    return
  }
  if (!editingMaterialId.value && !materialForm.value.file && !materialForm.value.url) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  saving.value = true
  try {
    if (materialForm.value.file) {
      const uploaded = await upload(materialForm.value.file, 'public_course_material')
      materialForm.value.url = uploaded.url
      materialForm.value.size = formatFileSize(uploaded.size)
      materialForm.value.file_id = uploaded.file_id
    }
    const payload = {
      type: materialForm.value.type,
      title: materialForm.value.title.trim(),
      url: materialForm.value.url.trim(),
      size: materialForm.value.size || '0 MB',
      file_id: materialForm.value.file_id,
      stage_id: typeof materialForm.value.stage_id === 'number' ? materialForm.value.stage_id : null,
    }
    if (editingMaterialId.value) {
      await updateAdminPublicMaterial(selectedCourse.value.id, editingMaterialId.value, payload)
      ElMessage.success('公共资料已更新，并同步到教师课程副本')
    } else {
      await createAdminPublicMaterial(selectedCourse.value.id, payload)
      ElMessage.success('公共资料已新增，并同步到教师课程副本')
    }
    showMaterialDialog.value = false
    await Promise.all([fetchContent(), fetchCourses(selectedCourse.value.id)])
  } catch (err: any) {
    ElMessage.error(err?.message || '保存公共资料失败')
  } finally {
    saving.value = false
  }
}

async function removeMaterial(material: Material) {
  if (!selectedCourse.value) return
  try {
    await ElMessageBox.confirm('确定删除该公共资料吗？将软删除公共课程源资料；已同步到教师课程副本的资料会保留，教师自行新增资料不受影响。', '删除公共资料', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    })
    await deleteAdminPublicMaterial(selectedCourse.value.id, material.id)
    ElMessage.success('公共资料已删除')
    await Promise.all([fetchContent(), fetchCourses(selectedCourse.value.id)])
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除公共资料失败')
  }
}

const sortedStages = computed(() => [...stages.value].sort((a, b) => a.sort_order - b.sort_order))
function stageMaterials(stageId: number) {
  return materials.value.filter(m => m.stage_id === stageId)
}
function uncategorizedMaterials() {
  return materials.value.filter(m => m.stage_id === null || m.stage_id === undefined)
}

async function handleAddStage() {
  if (!selectedCourse.value) return
  const name = newStageName.value.trim()
  if (!name) {
    ElMessage.warning('请输入阶段名称')
    return
  }
  savingStage.value = true
  try {
    await createAdminPublicCourseStage(selectedCourse.value.id, { name, sort_order: newStageOrder.value })
    ElMessage.success('阶段已添加')
    newStageName.value = ''
    newStageOrder.value = sortedStages.value.length
    await fetchContent()
  } catch (err: any) {
    ElMessage.error(err?.message || '添加阶段失败')
  } finally {
    savingStage.value = false
  }
}

async function handleStageNameChange(stage: AdminCourseStage) {
  const name = stage.name.trim()
  if (!name) {
    ElMessage.warning('阶段名称不能为空')
    await fetchContent()
    return
  }
  try {
    await updateAdminPublicCourseStage(stage.course_id, stage.id, { name, sort_order: stage.sort_order })
    ElMessage.success('阶段已更新')
  } catch (err: any) {
    ElMessage.error(err?.message || '更新阶段失败')
    await fetchContent()
  }
}

async function handleStageOrderChange(stage: AdminCourseStage) {
  try {
    await updateAdminPublicCourseStage(stage.course_id, stage.id, { name: stage.name, sort_order: stage.sort_order })
    await fetchContent()
  } catch (err: any) {
    ElMessage.error(err?.message || '排序更新失败')
    await fetchContent()
  }
}

async function handleDeleteStage(stage: AdminCourseStage) {
  if (!selectedCourse.value) return
  const count = stageMaterials(stage.id).length
  const tip = count > 0
    ? `确定删除阶段「${stage.name}」？将同时删除该阶段下的 ${count} 份公共资料（软删除），对应同步资料会软删除；教师自行新增资料会保留并移至未分类。`
    : `确定删除阶段「${stage.name}」？`
  try {
    await ElMessageBox.confirm(tip, '删除确认', { type: 'warning', confirmButtonText: '确定删除' })
    await deleteAdminPublicCourseStage(selectedCourse.value.id, stage.id, { cascadeMaterials: true })
    ElMessage.success('已删除')
    await Promise.all([fetchContent(), fetchCourses(selectedCourse.value.id)])
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err?.message || '删除阶段失败')
    }
  }
}

onMounted(() => fetchCourses())
</script>

<template>
  <div class="public-courses-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">公共课程管理</h1>
        <p class="page-subtitle">公共课程资料与阶段由管理员维护，会同步到教师课程副本；全站共享题库请到「共享题库」菜单维护。</p>
      </div>
      <el-button type="primary" @click="openCreateCourse">新建公共课程</el-button>
    </div>

    <div class="course-grid">
      <section class="course-panel">
        <el-table
          :data="courses"
          v-loading="courseLoading"
          border
          stripe
          highlight-current-row
          style="width: 100%"
          @row-click="selectCourse"
        >
          <el-table-column prop="name" label="课程名称" min-width="160" />
          <el-table-column prop="material_count" label="资料" width="80" align="center" />
          <el-table-column prop="question_count" label="全站题数" width="90" align="center" />
          <el-table-column label="同步状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag
                :type="row.sync_status === 'synced' ? 'success' : row.sync_status === 'partial' ? 'warning' : 'info'"
                size="small"
                effect="plain"
              >
                {{ row.sync_status === 'synced' ? '已同步' : row.sync_status === 'partial' ? '部分同步' : '未同步' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="教师课程副本" width="110" align="center">
            <template #default="{ row }">{{ row.sync_copy_count || 0 }}</template>
          </el-table-column>
          <el-table-column label="创建时间" width="120">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click.stop="openEditCourse(row)">编辑</el-button>
              <el-button size="small" type="danger" text @click.stop="removeCourse(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无公共课程，点击右上角新建" />
          </template>
        </el-table>
      </section>

      <section class="content-panel">
        <template v-if="selectedCourse">
          <div class="selected-header">
            <div>
              <div class="selected-label">当前公共课程</div>
              <h2>{{ selectedCourse.name }}</h2>
            </div>
          </div>

          <el-tabs v-model="activeTab">
            <el-tab-pane label="阶段与资料" name="stages">
              <div class="tab-toolbar stage-toolbar">
                <span class="toolbar-tip">阶段名称与排序修改后会同步到教师课程副本。题库维护请前往「共享题库」。</span>
                <el-button type="primary" size="small" @click="openCreateMaterial(null)">新增资料</el-button>
              </div>
              <div v-loading="stageLoading" class="stage-section">
                <div class="stage-add-row">
                  <el-input v-model="newStageName" placeholder="新阶段名称" style="width: 220px" />
                  <el-input-number v-model="newStageOrder" :min="0" :step="1" step-strictly controls-position="right" style="width: 110px" />
                  <el-button type="primary" :loading="savingStage" @click="handleAddStage">添加阶段</el-button>
                </div>
                <el-empty v-if="sortedStages.length === 0" description="暂无阶段，可在上方添加" />
                <div v-else class="stage-list">
                  <div v-for="(stage, index) in sortedStages" :key="stage.id" class="stage-card">
                    <div class="stage-header">
                      <span class="stage-index">阶段 {{ index + 1 }}</span>
                      <el-input v-model="stage.name" style="width: 220px" @change="handleStageNameChange(stage)" />
                      <el-input-number v-model="stage.sort_order" :min="0" :step="1" step-strictly controls-position="right" style="width: 110px" @change="handleStageOrderChange(stage)" />
                      <span class="stage-meta">{{ stageMaterials(stage.id).length }} 份资料</span>
                      <el-button type="primary" size="small" @click="openCreateMaterial(stage.id)">上传资料</el-button>
                      <el-button type="danger" text size="small" @click="handleDeleteStage(stage)">删除</el-button>
                    </div>
                    <div v-if="stageMaterials(stage.id).length" class="material-grid">
                      <div v-for="material in stageMaterials(stage.id)" :key="material.id" class="material-card">
                        <div class="card-head">
                          <el-tag size="small" effect="plain">{{ material.type === 'video' ? '视频' : 'PDF' }}</el-tag>
                        </div>
                        <h4>{{ material.title }}</h4>
                        <p class="material-meta">{{ material.size }} · {{ material.date || '未记录日期' }}</p>
                        <div class="card-actions">
                          <el-button type="primary" size="small" @click="previewMaterial(material)">预览</el-button>
                          <el-button size="small" @click="openEditMaterial(material)">编辑</el-button>
                          <el-button type="danger" size="small" @click="removeMaterial(material)">删除</el-button>
                        </div>
                      </div>
                    </div>
                    <el-empty v-else description="该阶段暂无资料" :image-size="60" />
                  </div>
                  <div v-if="uncategorizedMaterials().length" class="stage-card">
                    <div class="stage-header">
                      <span class="stage-index other">其他</span>
                      <span class="stage-title-other">未分类资料</span>
                      <span class="stage-meta">{{ uncategorizedMaterials().length }} 份资料</span>
                      <el-button type="primary" size="small" @click="openCreateMaterial(null)">上传资料</el-button>
                    </div>
                    <div class="material-grid">
                      <div v-for="material in uncategorizedMaterials()" :key="material.id" class="material-card">
                        <div class="card-head">
                          <el-tag size="small" effect="plain">{{ material.type === 'video' ? '视频' : 'PDF' }}</el-tag>
                        </div>
                        <h4>{{ material.title }}</h4>
                        <p class="material-meta">{{ material.size }} · {{ material.date || '未记录日期' }}</p>
                        <div class="card-actions">
                          <el-button type="primary" size="small" @click="previewMaterial(material)">预览</el-button>
                          <el-button size="small" @click="openEditMaterial(material)">编辑</el-button>
                          <el-button type="danger" size="small" @click="removeMaterial(material)">删除</el-button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="全部资料" name="materials">
              <div class="tab-toolbar">
                <el-button type="primary" size="small" @click="openCreateMaterial(null)">新增资料</el-button>
              </div>
              <el-table :data="materials" v-loading="contentLoading" border stripe style="width: 100%">
                <el-table-column prop="title" label="资料标题" min-width="180" />
                <el-table-column prop="type" label="类型" width="90" />
                <el-table-column label="所属阶段" min-width="140">
                  <template #default="{ row }">
                    <span>{{ sortedStages.find(s => s.id === row.stage_id)?.name || '未分类' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="size" label="大小" width="100" />
                <el-table-column prop="url" label="地址" min-width="160" show-overflow-tooltip />
                <el-table-column label="操作" width="180" fixed="right">
                  <template #default="{ row }">
                    <el-button v-if="row.url || row.file_id" size="small" text @click="previewMaterial(row)">预览</el-button>
                    <el-button size="small" text @click="openEditMaterial(row)">编辑</el-button>
                    <el-button size="small" type="danger" text @click="removeMaterial(row)">删除</el-button>
                  </template>
                </el-table-column>
                <template #empty>
                  <el-empty description="暂无资料，新增后会同步给教师课程副本" />
                </template>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </template>
        <el-empty v-else description="请先新建或选择一个公共课程" />
      </section>
    </div>

    <el-dialog v-model="showCourseDialog" :title="editingCourseId ? '编辑公共课程' : '新建公共课程'" width="420px" :close-on-click-modal="false">
      <el-form :model="courseForm" label-width="90px">
        <el-form-item label="课程名称" required>
          <el-input v-model="courseForm.name" placeholder="请输入公共课程名称" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCourseDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCourse">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showMaterialDialog" :title="materialDialogTitle" width="520px" :close-on-click-modal="false">
      <el-form :model="materialForm" label-width="90px">
        <el-form-item label="资料类型" required>
          <el-select v-model="materialForm.type" style="width: 160px">
            <el-option label="PDF" value="pdf" />
            <el-option label="视频" value="video" />
          </el-select>
        </el-form-item>
        <el-form-item label="资料标题" required>
          <el-input v-model="materialForm.title" placeholder="请输入资料标题" clearable />
        </el-form-item>
        <el-form-item label="所属阶段">
          <el-select v-model="materialForm.stage_id" placeholder="未分类" clearable style="width: 100%">
            <el-option label="未分类" value="" />
            <el-option v-for="stage in sortedStages" :key="stage.id" :label="stage.name" :value="stage.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="上传文件">
          <input ref="uploadInput" type="file" accept=".pdf,video/*" hidden @change="handleFileChange" />
          <div class="upload-zone" @click="uploadInput?.click()">
            <span v-if="!materialForm.file">{{ materialForm.file_id ? '已关联文件，点击更换' : '点击选择要上传的文件' }}</span>
            <span v-else class="file-name">{{ materialForm.file.name }}</span>
          </div>
          <el-progress v-if="uploading" :percentage="uploadPercent" style="margin-top: 12px" />
        </el-form-item>
        <el-form-item label="资料大小">
          <span class="size-display">{{ materialForm.size }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMaterialDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving || uploading" @click="saveMaterial">保存并同步</el-button>
      </template>
    </el-dialog>

    <PdfPreviewDialog
      v-model:visible="previewVisible"
      :url="previewUrl"
      :file-id="previewFileId"
    />
  </div>
</template>

<style scoped>
.public-courses-page {
  max-width: 1180px;
  min-width: 0;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: var(--font-serif);
  color: var(--color-text);
  margin: 0 0 6px;
}

.page-subtitle {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.course-grid {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.course-panel,
.content-panel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
  min-width: 0;
}

.selected-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.selected-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.selected-header h2 {
  margin: 0;
  font-size: 1rem;
  color: var(--color-text);
}

.tab-toolbar {
  display: flex;
  justify-content: flex-end;
  margin: 4px 0 12px;
}

.toolbar-tip {
  margin-right: auto;
  color: var(--color-text-muted);
  font-size: 0.8125rem;
}

.upload-zone {
  padding: var(--space-xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: border-color var(--duration-fast), color var(--duration-fast);
}

.upload-zone:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.file-name {
  color: var(--color-primary);
  font-weight: 500;
}

.size-display {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 32px;
}

.stage-toolbar {
  justify-content: space-between;
}

.stage-section {
  min-height: 160px;
}

.stage-add-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.stage-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stage-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
  background: var(--color-bg-card);
}

.stage-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.stage-index {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  background: var(--color-learn);
  color: #fff;
  border-radius: 12px;
}

.stage-index.other {
  background: var(--color-text-muted);
}

.stage-title-other {
  font-weight: 700;
  color: var(--color-text);
  margin-right: auto;
}

.stage-meta {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  margin-right: auto;
}

.material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.material-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
  background: var(--color-bg-card);
}

.material-card h4 {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 8px 0 4px;
  line-height: 1.4;
  min-height: 2.8em;
}

.material-meta {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  margin-bottom: 12px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 640px) {
  .public-courses-page {
    max-width: 100%;
  }

  .page-header,
  .selected-header,
  .tab-toolbar,
  .stage-add-row,
  .stage-header {
    align-items: stretch;
    flex-direction: column;
  }

  .page-header {
    gap: 12px;
  }

  .page-title {
    font-size: 1.1rem;
  }

  .page-subtitle {
    font-size: 0.8rem;
    line-height: 1.6;
  }

  .course-panel,
  .content-panel {
    overflow-x: auto;
    padding: 12px;
  }

  .toolbar-tip,
  .stage-meta,
  .stage-title-other {
    margin-right: 0;
  }

  .stage-add-row :deep(.el-input),
  .stage-add-row :deep(.el-input-number),
  .stage-header :deep(.el-input),
  .stage-header :deep(.el-input-number) {
    width: 100% !important;
  }

  .material-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .card-actions {
    flex-wrap: wrap;
  }
}
</style>

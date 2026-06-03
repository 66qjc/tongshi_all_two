<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Material } from '../../api/material'
import type { Question } from '../../api/question'
import { uploadFile } from '../../api/upload'
import {
  createAdminPublicCourse,
  createAdminPublicMaterial,
  createAdminPublicQuestion,
  deleteAdminPublicCourse,
  deleteAdminPublicMaterial,
  deleteAdminPublicQuestion,
  getAdminPublicCourses,
  getAdminPublicMaterials,
  getAdminPublicQuestions,
  updateAdminPublicCourse,
  updateAdminPublicMaterial,
  updateAdminPublicQuestion,
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
const activeTab = ref<'materials' | 'questions'>('materials')

const courseLoading = ref(false)
const contentLoading = ref(false)
const saving = ref(false)

const materials = ref<Material[]>([])
const questions = ref<Question[]>([])

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
  file: null as File | null,
})

const showQuestionDialog = ref(false)
const editingQuestionId = ref<number | null>(null)
const questionForm = ref({
  type: 'choice' as 'choice' | 'fill' | 'multi_choice',
  stem: '',
  optionsText: '',
  answer: '',
  explanation: '',
})

const selectedCourseId = computed(() => selectedCourse.value?.id || 0)
const questionDialogTitle = computed(() => editingQuestionId.value ? '编辑公共题目' : '新增公共题目')
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
    questions.value = []
    return
  }
  contentLoading.value = true
  try {
    const courseId = selectedCourse.value.id
    const [materialData, questionData] = await Promise.all([
      getAdminPublicMaterials(courseId),
      getAdminPublicQuestions(courseId),
    ])
    materials.value = materialData || []
    questions.value = questionData || []
  } catch (err: any) {
    ElMessage.error(err?.message || '加载课程内容失败')
  } finally {
    contentLoading.value = false
  }
}

function selectCourse(course: AdminPublicCourse) {
  selectedCourse.value = course
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
      `确定删除公共课程「${course.name}」吗？教师已添加的副本不会被删除，但后续不再从该公共源同步。`,
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

function openCreateMaterial() {
  if (!selectedCourse.value) return
  editingMaterialId.value = null
  materialForm.value = { type: 'pdf', title: '', url: '', size: '0 MB', file_id: undefined, file: null }
  if (uploadInput.value) uploadInput.value.value = ''
  showMaterialDialog.value = true
}

function openEditMaterial(material: Material) {
  editingMaterialId.value = material.id
  materialForm.value = {
    type: material.type,
    title: material.title,
    url: material.url || '',
    size: material.size || '0 MB',
    file_id: material.file_id,
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
      const uploaded = await uploadFile(materialForm.value.file)
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
    }
    if (editingMaterialId.value) {
      await updateAdminPublicMaterial(selectedCourse.value.id, editingMaterialId.value, payload)
      ElMessage.success('公共资料已更新，并同步到教师副本')
    } else {
      await createAdminPublicMaterial(selectedCourse.value.id, payload)
      ElMessage.success('公共资料已新增，并同步到教师副本')
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
    await ElMessageBox.confirm('确定删除该公共资料吗？教师副本中的同步资料也会同步删除。', '删除公共资料', {
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

function openCreateQuestion() {
  if (!selectedCourse.value) return
  editingQuestionId.value = null
  questionForm.value = { type: 'choice', stem: '', optionsText: '', answer: '', explanation: '' }
  showQuestionDialog.value = true
}

function openEditQuestion(question: Question) {
  editingQuestionId.value = question.id
  questionForm.value = {
    type: question.type,
    stem: question.stem,
    optionsText: (question.options || []).join('\n'),
    answer: question.answer,
    explanation: question.explanation || '',
  }
  showQuestionDialog.value = true
}

async function saveQuestion() {
  if (!selectedCourse.value) return
  if (!questionForm.value.stem.trim() || !questionForm.value.answer.trim()) {
    ElMessage.warning('请填写题干和答案')
    return
  }
  const options = questionForm.value.optionsText
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
  if ((questionForm.value.type === 'choice' || questionForm.value.type === 'multi_choice') && options.length === 0) {
    ElMessage.warning('选择题/多选题请至少填写一个选项')
    return
  }
  saving.value = true
  try {
    const payload = {
      type: questionForm.value.type,
      stem: questionForm.value.stem.trim(),
      options,
      answer: questionForm.value.answer.trim(),
      explanation: questionForm.value.explanation.trim(),
    }
    if (editingQuestionId.value) {
      await updateAdminPublicQuestion(selectedCourse.value.id, editingQuestionId.value, payload)
      ElMessage.success('公共题目已更新，并同步到教师副本')
    } else {
      await createAdminPublicQuestion(selectedCourse.value.id, payload)
      ElMessage.success('公共题目已新增，并同步到教师副本')
    }
    showQuestionDialog.value = false
    await Promise.all([fetchContent(), fetchCourses(selectedCourse.value.id)])
  } catch (err: any) {
    ElMessage.error(err?.message || '保存公共题目失败')
  } finally {
    saving.value = false
  }
}

async function removeQuestion(question: Question) {
  if (!selectedCourse.value) return
  try {
    await ElMessageBox.confirm('确定删除该公共题目吗？教师副本中的同步题目也会同步删除。', '删除公共题目', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    })
    await deleteAdminPublicQuestion(selectedCourse.value.id, question.id)
    ElMessage.success('公共题目已删除')
    await Promise.all([fetchContent(), fetchCourses(selectedCourse.value.id)])
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除公共题目失败')
  }
}

onMounted(() => fetchCourses())
</script>

<template>
  <div class="public-courses-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">公共课程管理</h1>
        <p class="page-subtitle">公共课程资料和题库由管理员维护，变更会同步到已添加该课程的教师副本。</p>
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
          <el-table-column prop="question_count" label="题目" width="80" align="center" />
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
            <el-tab-pane label="资料" name="materials">
              <div class="tab-toolbar">
                <el-button type="primary" size="small" @click="openCreateMaterial">新增资料</el-button>
              </div>
              <el-table :data="materials" v-loading="contentLoading" border stripe style="width: 100%">
                <el-table-column prop="title" label="资料标题" min-width="180" />
                <el-table-column prop="type" label="类型" width="90" />
                <el-table-column prop="size" label="大小" width="100" />
                <el-table-column prop="url" label="地址" min-width="180" show-overflow-tooltip />
                <el-table-column label="操作" width="130" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" text @click="openEditMaterial(row)">编辑</el-button>
                    <el-button size="small" type="danger" text @click="removeMaterial(row)">删除</el-button>
                  </template>
                </el-table-column>
                <template #empty>
                  <el-empty description="暂无资料，新增后会同步给教师副本" />
                </template>
              </el-table>
            </el-tab-pane>

            <el-tab-pane label="题库" name="questions">
              <div class="tab-toolbar">
                <el-button type="primary" size="small" @click="openCreateQuestion">新增题目</el-button>
              </div>
              <el-table :data="questions" v-loading="contentLoading" border stripe style="width: 100%">
                <el-table-column prop="stem" label="题干" min-width="220" show-overflow-tooltip />
                <el-table-column prop="type" label="题型" width="90" />
                <el-table-column prop="answer" label="答案" width="120" show-overflow-tooltip />
                <el-table-column label="操作" width="130" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" text @click="openEditQuestion(row)">编辑</el-button>
                    <el-button size="small" type="danger" text @click="removeQuestion(row)">删除</el-button>
                  </template>
                </el-table-column>
                <template #empty>
                  <el-empty description="暂无题目，新增后会同步给教师副本" />
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
        <el-form-item label="上传文件">
          <input ref="uploadInput" type="file" accept=".pdf,video/*" hidden @change="handleFileChange" />
          <div class="upload-zone" @click="uploadInput?.click()">
            <span v-if="!materialForm.file">{{ materialForm.file_id ? '已关联文件，点击更换' : '点击选择要上传的文件' }}</span>
            <span v-else class="file-name">{{ materialForm.file.name }}</span>
          </div>
        </el-form-item>
        <el-form-item label="资料大小">
          <span class="size-display">{{ materialForm.size }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMaterialDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMaterial">保存并同步</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showQuestionDialog" :title="questionDialogTitle" width="620px" :close-on-click-modal="false">
      <el-form :model="questionForm" label-width="90px">
        <el-form-item label="题型" required>
          <el-select v-model="questionForm.type" style="width: 160px">
            <el-option label="选择题" value="choice" />
            <el-option label="多选题" value="multi_choice" />
            <el-option label="填空题" value="fill" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干" required>
          <el-input v-model="questionForm.stem" type="textarea" :rows="3" placeholder="请输入题干" />
        </el-form-item>
        <el-form-item v-if="questionForm.type === 'choice' || questionForm.type === 'multi_choice'" label="选项">
          <el-input v-model="questionForm.optionsText" type="textarea" :rows="4" placeholder="每行一个选项，例如：A. 图灵" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="questionForm.answer" placeholder="请输入标准答案" clearable />
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="questionForm.explanation" type="textarea" :rows="3" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showQuestionDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveQuestion">保存并同步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.public-courses-page {
  max-width: 1180px;
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
  display: grid;
  grid-template-columns: minmax(480px, 0.95fr) minmax(460px, 1.05fr);
  gap: 18px;
  align-items: flex-start;
}

.course-panel,
.content-panel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
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

@media (max-width: 1100px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>

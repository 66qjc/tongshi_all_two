<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createMaterial, deleteMaterial as apiDeleteMaterial, getAllMaterials, type Material } from '@/api/material'
import {
  createChapter,
  deleteChapter as apiDeleteChapter,
  getChapters,
  updateChapter,
  updateChapterSchedule,
  type Chapter,
  type ChapterManagePayload,
} from '@/api/chapter'
import {
  createCourse,
  deleteCourse as apiDeleteCourse,
  getCourseDetail,
  getCourses,
  updateCourse,
  type Course,
  type CourseDetail,
} from '@/api/course'
import { uploadFile } from '@/api/upload'

const materials = ref<Material[]>([])
const chapters = ref<Chapter[]>([])
const courses = ref<Course[]>([])
const loading = ref(true)
const courseLoading = ref(false)
const filterChapter = ref<number | ''>('')
const dialogVisible = ref(false)
const scheduleDialogVisible = ref(false)
const courseDialogVisible = ref(false)
const courseDetailVisible = ref(false)
const chapterDialogVisible = ref(false)
const scheduleChapter = ref<Chapter | null>(null)
const selectedCourse = ref<CourseDetail | null>(null)
const uploading = ref(false)
const courseSaving = ref(false)
const chapterSaving = ref(false)
const editingCourseId = ref<number | null>(null)
const editingChapterId = ref<number | null>(null)
const uploadInput = ref<HTMLInputElement | null>(null)

const newMaterial = reactive<{
  chapter_id: number | ''
  type: 'video' | 'pdf'
  title: string
  file: File | null
}>({
  chapter_id: '',
  type: 'video',
  title: '',
  file: null,
})

const scheduleForm = reactive({
  course_id: null as number | null,
  day_of_week: '',
  class_periods: '',
  schedule_note: '',
})

const courseForm = reactive({
  name: '',
})

const chapterForm = reactive<ChapterManagePayload>({
  num: '',
  title: '',
  desc: '',
  topics: [],
  status: '即将发布',
  sort_order: 0,
  course_id: null,
  day_of_week: '',
  class_periods: '',
  schedule_note: '',
})
const chapterTopicText = ref('')

const dayOptions = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const statusOptions = ['已发布', '即将发布']

const filteredMaterials = computed(() => {
  if (!filterChapter.value) return materials.value
  return materials.value.filter(item => item.chapter_id === filterChapter.value)
})

const groupedChapters = computed(() => {
  const groups = courses.value.map(course => ({
    id: course.id,
    name: course.name,
    chapters: chapters.value.filter(chapter => chapter.course_id === course.id),
  }))
  const unassigned = chapters.value.filter(chapter => !chapter.course_id)
  if (unassigned.length > 0) {
    groups.push({ id: 0, name: '未分配课程', chapters: unassigned })
  }
  return groups.filter(group => group.chapters.length > 0)
})

const hasUnassignedChapters = computed(() => chapters.value.some(chapter => !chapter.course_id))

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback
}

function formatFileSize(bytes: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size >= 10 || unitIndex === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[unitIndex]}`
}

function getChapterTitle(chapterId: number) {
  const chapter = chapters.value.find(item => item.id === chapterId)
  if (!chapter) return `章节 ${chapterId}`
  return `${chapter.num} ${chapter.title}`
}

function resetUploadForm() {
  newMaterial.chapter_id = ''
  newMaterial.type = 'video'
  newMaterial.title = ''
  newMaterial.file = null
  if (uploadInput.value) {
    uploadInput.value.value = ''
  }
}

function resetCourseForm() {
  courseForm.name = ''
  editingCourseId.value = null
}

function resetChapterForm(courseId: number | null = null) {
  Object.assign(chapterForm, {
    num: '',
    title: '',
    desc: '',
    topics: [],
    status: '即将发布',
    sort_order: chapters.value.length + 1,
    course_id: courseId,
    day_of_week: '',
    class_periods: '',
    schedule_note: '',
  })
  chapterTopicText.value = ''
  editingChapterId.value = null
}

function openUpload() {
  resetUploadForm()
  dialogVisible.value = true
}

async function loadCourses() {
  courseLoading.value = true
  try {
    courses.value = await getCourses()
  } catch {
    ElMessage.error('课程列表加载失败，请稍后重试')
  } finally {
    courseLoading.value = false
  }
}

async function openCourseManager() {
  courseDialogVisible.value = true
  resetCourseForm()
  await loadCourses()
}

async function openCourseDetail(course: Course) {
  try {
    selectedCourse.value = await getCourseDetail(course.id)
    courseDetailVisible.value = true
  } catch {
    ElMessage.error('课程详情加载失败，请稍后重试')
  }
}

async function refreshCourseDetail() {
  if (!selectedCourse.value) return
  selectedCourse.value = await getCourseDetail(selectedCourse.value.id)
}

function openFilePicker() {
  uploadInput.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    newMaterial.file = input.files[0]
  }
}

onMounted(async () => {
  try {
    const [materialList, chapterList, courseList] = await Promise.all([getAllMaterials(), getChapters(), getCourses()])
    materials.value = materialList
    chapters.value = chapterList
    courses.value = courseList
  } catch {
    ElMessage.error('资料数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})

async function handleUpload() {
  if (typeof newMaterial.chapter_id !== 'number') {
    ElMessage.warning('请选择所属章节')
    return
  }
  if (!newMaterial.title.trim()) {
    ElMessage.warning('请填写资料标题')
    return
  }
  if (!newMaterial.file) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }

  uploading.value = true
  try {
    const uploadResult = await uploadFile(newMaterial.file)
    await createMaterial({
      chapter_id: newMaterial.chapter_id,
      type: newMaterial.type,
      title: newMaterial.title.trim(),
      url: uploadResult.url,
      size: formatFileSize(uploadResult.size),
    })
    materials.value = await getAllMaterials()
    dialogVisible.value = false
    resetUploadForm()
    ElMessage.success('资料上传成功')
  } catch {
    ElMessage.error('上传失败，请检查文件后重试')
  } finally {
    uploading.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这条资料吗？', '删除确认', { type: 'warning' })
    await apiDeleteMaterial(id)
    materials.value = materials.value.filter(item => item.id !== id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

function openSchedule(chapter: Chapter) {
  scheduleChapter.value = chapter
  Object.assign(scheduleForm, {
    course_id: chapter.course_id || null,
    day_of_week: chapter.day_of_week || '',
    class_periods: chapter.class_periods || '',
    schedule_note: chapter.schedule_note || '',
  })
  scheduleDialogVisible.value = true
}

async function handleSaveSchedule() {
  if (!scheduleChapter.value) return
  try {
    await updateChapterSchedule(scheduleChapter.value.id, scheduleForm)
    scheduleChapter.value.course_id = scheduleForm.course_id
    scheduleChapter.value.course_name = courses.value.find(course => course.id === scheduleForm.course_id)?.name || ''
    scheduleChapter.value.day_of_week = scheduleForm.day_of_week
    scheduleChapter.value.class_periods = scheduleForm.class_periods
    scheduleChapter.value.schedule_note = scheduleForm.schedule_note
    chapters.value = await getChapters()
    await refreshCourseDetail()
    ElMessage.success('课表已保存')
    scheduleDialogVisible.value = false
  } catch {
    ElMessage.error('保存失败，请稍后重试')
  }
}

function startEditCourse(course: Course) {
  editingCourseId.value = course.id
  courseForm.name = course.name
}

async function handleSaveCourse() {
  const name = courseForm.name.trim()
  if (!name) {
    ElMessage.warning('请填写课程名称')
    return
  }

  courseSaving.value = true
  try {
    if (editingCourseId.value) {
      await updateCourse(editingCourseId.value, { name })
      ElMessage.success('课程已保存')
    } else {
      await createCourse({ name })
      ElMessage.success('课程已新增')
    }
    resetCourseForm()
    await loadCourses()
    courses.value = await getCourses()
  } catch {
    ElMessage.error('课程保存失败，请稍后重试')
  } finally {
    courseSaving.value = false
  }
}

async function handleDeleteCourse(course: Course) {
  try {
    await ElMessageBox.confirm(
      `确定删除课程“${course.name}”吗？课程下没有资料、题目和学习记录的章节会一并删除。`,
      '删除确认',
      { type: 'warning' },
    )
    await apiDeleteCourse(course.id)
    if (editingCourseId.value === course.id) {
      resetCourseForm()
    }
    await loadCourses()
    courses.value = await getCourses()
    ElMessage.success('课程已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getErrorMessage(error, '课程删除失败，请先确认是否仍有关联题目或学习记录'))
    }
  }
}

function openCreateChapter(courseId: number | null = selectedCourse.value?.id || null) {
  resetChapterForm(courseId)
  chapterDialogVisible.value = true
}

function openEditChapter(chapter: Chapter) {
  editingChapterId.value = chapter.id
  Object.assign(chapterForm, {
    num: chapter.num,
    title: chapter.title,
    desc: chapter.desc,
    topics: chapter.topics || [],
    status: chapter.status,
    sort_order: chapter.sort_order || 0,
    course_id: chapter.course_id,
    day_of_week: chapter.day_of_week || '',
    class_periods: chapter.class_periods || '',
    schedule_note: chapter.schedule_note || '',
  })
  chapterTopicText.value = (chapter.topics || []).join('、')
  chapterDialogVisible.value = true
}

async function handleSaveChapter() {
  if (!chapterForm.num.trim()) {
    ElMessage.warning('请填写章节编号')
    return
  }
  if (!chapterForm.title.trim()) {
    ElMessage.warning('请填写章节标题')
    return
  }

  const payload: ChapterManagePayload = {
    ...chapterForm,
    num: chapterForm.num.trim(),
    title: chapterForm.title.trim(),
    desc: chapterForm.desc.trim(),
    topics: chapterTopicText.value.split(/[、,，]/).map(item => item.trim()).filter(Boolean),
    class_periods: chapterForm.class_periods.trim(),
    schedule_note: chapterForm.schedule_note.trim(),
  }

  chapterSaving.value = true
  try {
    if (editingChapterId.value) {
      await updateChapter(editingChapterId.value, payload)
      ElMessage.success('章节已保存')
    } else {
      await createChapter(payload)
      ElMessage.success('章节已新增')
    }
    chapters.value = await getChapters()
    courses.value = await getCourses()
    await refreshCourseDetail()
    chapterDialogVisible.value = false
  } catch {
    ElMessage.error('章节保存失败，请检查填写内容')
  } finally {
    chapterSaving.value = false
  }
}

async function handleDeleteChapter(chapter: Chapter) {
  try {
    await ElMessageBox.confirm(
      `确定删除章节“${chapter.title}”吗？章节下的资料、题目和学习记录会一并删除。`,
      '删除确认',
      { type: 'warning' },
    )
    await apiDeleteChapter(chapter.id)
    chapters.value = await getChapters()
    courses.value = await getCourses()
    await refreshCourseDetail()
    ElMessage.success('章节已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getErrorMessage(error, '章节删除失败，请稍后重试'))
    }
  }
}
</script>

<template>
  <div class="materials-page">
    <div class="page-header">
      <h1>资料管理</h1>
      <div class="header-actions">
        <el-button round @click="openCourseManager">管理课程</el-button>
        <el-button type="primary" round @click="openUpload">上传资料</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterChapter" placeholder="全部章节" clearable size="default" style="width: 240px">
        <el-option
          v-for="chapter in chapters"
          :key="chapter.id"
          :label="`${chapter.num} ${chapter.title}`"
          :value="chapter.id"
        />
      </el-select>
      <span class="filter-count">共 {{ filteredMaterials.length }} 条资料</span>
    </div>

    <div v-if="chapters.length > 0" class="schedule-section">
      <div class="section-heading">
        <h2 class="section-title">课程时间安排</h2>
        <el-button type="primary" plain @click="openCreateChapter(null)">新增章节</el-button>
      </div>
      <div class="schedule-groups">
        <div v-for="group in groupedChapters" :key="group.id" class="schedule-group">
          <div class="schedule-group-header">
            <h3>{{ group.name }}</h3>
          </div>
          <div class="schedule-grid">
            <div v-for="chapter in group.chapters" :key="chapter.id" class="schedule-card">
              <span class="schedule-num">{{ chapter.num }}</span>
              <div class="schedule-info">
                <span class="schedule-name">{{ chapter.title }}</span>
                <span v-if="chapter.day_of_week" class="schedule-time">
                  {{ chapter.day_of_week }} 第 {{ chapter.class_periods || '未设置' }} 节
                  <span v-if="chapter.schedule_note" class="schedule-note">（{{ chapter.schedule_note }}）</span>
                </span>
                <span v-else class="schedule-empty">未设置时间</span>
              </div>
              <div class="schedule-actions">
                <el-button type="primary" text size="small" @click="openSchedule(chapter)">编辑</el-button>
                <el-button type="danger" text size="small" @click="handleDeleteChapter(chapter)">删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="schedule-section">
      <div class="section-heading">
        <h2 class="section-title">课程时间安排</h2>
        <el-button type="primary" plain @click="openCreateChapter(null)">新增章节</el-button>
      </div>
      <div class="empty-state schedule-empty-state">
        <p>暂无章节，点击“新增章节”维护课程内容。</p>
      </div>
    </div>

    <el-table :data="filteredMaterials" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="title" label="资料名称" min-width="200" />
      <el-table-column label="所属章节" min-width="180">
        <template #default="{ row }">
          {{ getChapterTitle(row.chapter_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.type === 'video' ? '' : 'success'" size="small" effect="plain">
            {{ row.type === 'video' ? '视频' : 'PDF' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="110" />
      <el-table-column prop="date" label="上传时间" width="120" />
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" text size="small" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && filteredMaterials.length === 0" class="empty-state">
      <p>暂无资料，点击“上传资料”添加视频课件或 PDF 讲义。</p>
    </div>

    <el-dialog v-model="dialogVisible" title="上传资料" width="480px">
      <div class="form-group">
        <label>所属章节</label>
        <el-select v-model="newMaterial.chapter_id" placeholder="选择章节" size="large" style="width: 100%">
          <el-option
            v-for="chapter in chapters"
            :key="chapter.id"
            :label="`${chapter.num} ${chapter.title}`"
            :value="chapter.id"
          />
        </el-select>
      </div>
      <div class="form-group">
        <label>资料类型</label>
        <el-radio-group v-model="newMaterial.type" size="large">
          <el-radio-button value="video">视频</el-radio-button>
          <el-radio-button value="pdf">PDF</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>资料标题</label>
        <el-input v-model="newMaterial.title" placeholder="输入资料标题" size="large" />
      </div>
      <div class="form-group">
        <label>文件</label>
        <input ref="uploadInput" type="file" accept=".pdf,video/*" hidden @change="handleFileChange" />
        <div class="upload-zone-small" @click="openFilePicker">
          <span v-if="!newMaterial.file">点击选择要上传的文件</span>
          <span v-else class="file-name">{{ newMaterial.file.name }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">确认上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="courseDialogVisible" title="管理课程" width="560px">
      <div class="course-editor">
        <el-input
          v-model="courseForm.name"
          placeholder="输入课程名称"
          size="large"
          clearable
          @keyup.enter="handleSaveCourse"
        />
        <el-button type="primary" size="large" :loading="courseSaving" @click="handleSaveCourse">
          {{ editingCourseId ? '保存修改' : '新增课程' }}
        </el-button>
        <el-button v-if="editingCourseId" size="large" @click="resetCourseForm">取消编辑</el-button>
      </div>

      <el-table :data="courses" stripe style="width: 100%" v-loading="courseLoading">
        <el-table-column prop="name" label="课程名称" min-width="220" />
        <el-table-column prop="chapter_count" label="章节" width="80" />
        <el-table-column prop="material_count" label="资料" width="80" />
        <el-table-column prop="created_at" label="创建时间" min-width="160">
          <template #default="{ row }">
            {{ row.created_at ? row.created_at.slice(0, 10) : '未记录' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="openCourseDetail(row)">详情</el-button>
            <el-button type="primary" text size="small" @click="startEditCourse(row)">编辑</el-button>
            <el-button type="danger" text size="small" @click="handleDeleteCourse(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!courseLoading && courses.length === 0" class="empty-state course-empty">
        <p>暂无课程，输入课程名称后点击“新增课程”。</p>
      </div>
    </el-dialog>

    <el-drawer v-model="courseDetailVisible" :title="selectedCourse ? `课程详情：${selectedCourse.name}` : '课程详情'" size="620px">
      <div v-if="selectedCourse" class="course-detail">
        <div class="course-detail-actions">
          <span>共 {{ selectedCourse.chapter_count }} 个章节，{{ selectedCourse.material_count }} 份资料</span>
          <el-button type="primary" size="small" @click="openCreateChapter(selectedCourse.id)">新增章节</el-button>
        </div>
        <el-table :data="selectedCourse.chapters" stripe style="width: 100%">
          <el-table-column prop="num" label="编号" width="80" />
          <el-table-column prop="title" label="章节" min-width="160" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="课表" min-width="140">
            <template #default="{ row }">
              {{ row.day_of_week ? `${row.day_of_week} 第 ${row.class_periods || '未设置'} 节` : '未设置' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" text size="small" @click="openEditChapter(row)">编辑</el-button>
              <el-button type="danger" text size="small" @click="handleDeleteChapter(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="selectedCourse.chapters.length === 0" class="empty-state course-empty">
          <p>该课程暂无章节，点击“新增章节”开始维护。</p>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="chapterDialogVisible" :title="editingChapterId ? '编辑章节' : '新增章节'" width="560px">
      <div class="form-grid">
        <div class="form-group">
          <label>章节编号</label>
          <el-input v-model="chapterForm.num" placeholder="例如：01" />
        </div>
        <div class="form-group">
          <label>章节标题</label>
          <el-input v-model="chapterForm.title" placeholder="输入章节标题" />
        </div>
        <div class="form-group full">
          <label>所属课程</label>
          <el-select v-model="chapterForm.course_id" clearable placeholder="选择课程" style="width: 100%">
            <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
          </el-select>
          <p v-if="hasUnassignedChapters && !chapterForm.course_id" class="form-tip">未选择课程时，章节会显示在“未分配课程”。</p>
        </div>
        <div class="form-group full">
          <label>简介</label>
          <el-input v-model="chapterForm.desc" type="textarea" :rows="3" placeholder="输入章节简介" />
        </div>
        <div class="form-group full">
          <label>主题</label>
          <el-input v-model="chapterTopicText" placeholder="用顿号或逗号分隔，例如：AI 概述、机器学习" />
        </div>
        <div class="form-group">
          <label>状态</label>
          <el-select v-model="chapterForm.status" style="width: 100%">
            <el-option v-for="status in statusOptions" :key="status" :label="status" :value="status" />
          </el-select>
        </div>
        <div class="form-group">
          <label>排序</label>
          <el-input-number v-model="chapterForm.sort_order" :min="0" style="width: 100%" />
        </div>
        <div class="form-group">
          <label>星期</label>
          <el-select v-model="chapterForm.day_of_week" placeholder="选择星期" style="width: 100%" clearable>
            <el-option v-for="day in dayOptions" :key="day" :label="day" :value="day" />
          </el-select>
        </div>
        <div class="form-group">
          <label>节次</label>
          <el-input v-model="chapterForm.class_periods" placeholder="例如：1-3 或 3-5" />
        </div>
        <div class="form-group full">
          <label>备注</label>
          <el-input v-model="chapterForm.schedule_note" placeholder="例如：双周" />
        </div>
      </div>
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="chapterSaving" @click="handleSaveChapter">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scheduleDialogVisible" :title="scheduleChapter ? `设置课表：${scheduleChapter.title}` : '设置课表'" width="420px">
      <div class="form-group">
        <label>所属课程</label>
        <el-select v-model="scheduleForm.course_id" placeholder="选择课程" size="large" style="width: 100%" clearable>
          <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>星期</label>
        <el-select v-model="scheduleForm.day_of_week" placeholder="选择星期" size="large" style="width: 100%" clearable>
          <el-option v-for="day in dayOptions" :key="day" :label="day" :value="day" />
        </el-select>
      </div>
      <div class="form-group">
        <label>节次</label>
        <el-input v-model="scheduleForm.class_periods" placeholder="例如：1-3 或 3-5" size="large" />
      </div>
      <div class="form-group">
        <label>备注</label>
        <el-input v-model="scheduleForm.schedule_note" placeholder="例如：双周" size="large" />
      </div>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveSchedule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.filter-count {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.section-heading,
.schedule-group-header,
.course-detail-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}

.form-group {
  margin-bottom: var(--space-lg);
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.form-group.full {
  grid-column: 1 / -1;
}

.course-editor {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
}

.upload-zone-small {
  padding: var(--space-xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.upload-zone-small:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.file-name {
  color: var(--color-primary);
  font-weight: 600;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-md);
}

.schedule-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.schedule-group-header {
  margin-bottom: var(--space-sm);
}

.schedule-group-header h3 {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
}

.schedule-section {
  margin-bottom: var(--space-xl);
  padding-bottom: var(--space-xl);
  border-bottom: 1px solid var(--color-border-light);
}

.schedule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-sm);
}

.schedule-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.schedule-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-xs);
}

.schedule-num {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-border);
  font-family: var(--font-mono);
  flex-shrink: 0;
  width: 32px;
}

.schedule-info {
  flex: 1;
  min-width: 0;
}

.schedule-name {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
}

.schedule-time {
  display: block;
  font-size: 0.8rem;
  color: var(--color-primary);
  font-weight: 500;
}

.schedule-note,
.schedule-empty {
  color: var(--color-text-muted);
  font-weight: 400;
}

.schedule-empty {
  display: block;
  font-size: 0.8rem;
}

.schedule-actions {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  flex-shrink: 0;
}

.form-tip {
  margin-top: var(--space-xs);
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.course-empty {
  padding: var(--space-xl) 0 0;
}

.schedule-empty-state {
  padding: var(--space-xl) 0;
}

@media (max-width: 768px) {
  .page-header,
  .header-actions,
  .course-editor,
  .section-heading,
  .course-detail-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .schedule-grid {
    grid-template-columns: 1fr;
  }
}
</style>

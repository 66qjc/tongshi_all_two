<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createMaterial, deleteMaterial, getAllMaterials, type Material } from '@/api/material'
import { getCourses, type Course } from '@/api/course'
import { uploadFile } from '@/api/upload'
import { resolveFileUrl } from '@/utils/url'

const route = useRoute()
const materials = ref<Material[]>([])
const courses = ref<Course[]>([])
const loading = ref(true)
const filterCourse = ref<number | ''>('')
const dialogVisible = ref(false)
const uploading = ref(false)
const uploadInput = ref<HTMLInputElement | null>(null)

const form = reactive<{
  course_id: number | ''
  type: 'video' | 'pdf'
  title: string
  file: File | null
}>({
  course_id: '',
  type: 'video',
  title: '',
  file: null,
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

async function loadCourses() {
  courses.value = await getCourses()
}

async function loadMaterials() {
  loading.value = true
  try {
    materials.value = await getAllMaterials(filterCourse.value ? { course_id: filterCourse.value } : undefined)
  } catch {
    ElMessage.error('资料数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.course_id = filterCourse.value || ''
  form.type = 'video'
  form.title = ''
  form.file = null
  if (uploadInput.value) uploadInput.value.value = ''
}

function openUpload() {
  resetForm()
  dialogVisible.value = true
}

function openMaterial(row: Material) {
  const url = resolveFileUrl(row.file_id ? `/api/files/${row.file_id}` : row.url)
  if (!url) {
    ElMessage.warning('该资料暂无可访问文件')
    return
  }
  window.open(url, '_blank', 'noopener')
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  form.file = input.files?.[0] || null
}

async function handleUpload() {
  if (typeof form.course_id !== 'number') {
    ElMessage.warning('请选择所属课程')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请填写资料标题')
    return
  }
  if (!form.file) {
    ElMessage.warning('请选择要上传的文件')
    return
  }

  uploading.value = true
  try {
    const uploaded = await uploadFile(form.file)
    await createMaterial({
      course_id: form.course_id,
      type: form.type,
      title: form.title.trim(),
      url: uploaded.url,
      size: formatFileSize(uploaded.size),
      file_id: uploaded.file_id,
    })
    ElMessage.success('资料上传成功')
    dialogVisible.value = false
    await loadMaterials()
  } catch {
    ElMessage.error('上传失败，请检查文件后重试')
  } finally {
    uploading.value = false
  }
}

async function handleDelete(row: Material) {
  try {
    await ElMessageBox.confirm(`确定删除资料“${row.title}”？`, '删除确认', { type: 'warning' })
    await deleteMaterial(row.id)
    materials.value = materials.value.filter(item => item.id !== row.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('删除失败，请稍后重试')
  }
}

onMounted(async () => {
  const courseId = Number(route.query.course_id)
  if (Number.isFinite(courseId) && courseId > 0) filterCourse.value = courseId
  try {
    await loadCourses()
    await loadMaterials()
  } catch {
    ElMessage.error('页面初始化失败')
  }
})

watch(filterCourse, () => {
  loadMaterials()
})
</script>

<template>
  <div class="materials-page">
    <div class="page-header">
      <h1>资料管理</h1>
      <el-button type="primary" round @click="openUpload">上传资料</el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterCourse" placeholder="全部课程" clearable style="width: 240px">
        <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
      </el-select>
      <span class="filter-count">共 {{ materials.length }} 条资料</span>
    </div>

    <el-table :data="materials" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="title" label="资料名称" min-width="220" />
      <el-table-column prop="course_name" label="所属课程" min-width="180" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.type === 'video' ? '' : 'success'" size="small" effect="plain">
            {{ row.type === 'video' ? '视频' : 'PDF' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="110" />
      <el-table-column prop="date" label="上传时间" width="130" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" text size="small" @click="openMaterial(row)">查看</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && materials.length === 0" class="empty-state">
      暂无资料，点击“上传资料”添加视频课件或 PDF 讲义。
    </div>

    <el-dialog v-model="dialogVisible" title="上传资料" width="480px">
      <div class="form-group">
        <label>所属课程</label>
        <el-select v-model="form.course_id" placeholder="选择课程" size="large" style="width: 100%">
          <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>资料类型</label>
        <el-radio-group v-model="form.type" size="large">
          <el-radio-button value="video">视频</el-radio-button>
          <el-radio-button value="pdf">PDF</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>资料标题</label>
        <el-input v-model="form.title" placeholder="输入资料标题" size="large" />
      </div>
      <div class="form-group">
        <label>文件</label>
        <input ref="uploadInput" type="file" accept=".pdf,video/*" hidden @change="handleFileChange" />
        <div class="upload-zone" @click="uploadInput?.click()">
          <span v-if="!form.file">点击选择要上传的文件</span>
          <span v-else class="file-name">{{ form.file.name }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">确认上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header,
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
}

.filter-bar {
  justify-content: flex-start;
}

.filter-count,
.empty-state {
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.empty-state {
  padding: var(--space-3xl) 0;
  text-align: center;
}

.form-group {
  margin-bottom: var(--space-lg);
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: var(--space-sm);
}

.upload-zone {
  padding: var(--space-xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--color-text-muted);
  cursor: pointer;
}

.upload-zone:hover,
.file-name {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
</style>

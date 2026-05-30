<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createClass, deleteClass, getClassStudents, getClasses, type ClassInfo, type ClassStudent } from '@/api/class'
import { getCourses, type Course } from '@/api/course'

const router = useRouter()
const classes = ref<ClassInfo[]>([])
const courses = ref<Course[]>([])
const students = ref<ClassStudent[]>([])
const loading = ref(true)
const studentLoading = ref(false)
const createDialogVisible = ref(false)
const studentDialogVisible = ref(false)
const selectedClass = ref<ClassInfo | null>(null)

const filters = reactive({
  course_id: '' as number | '',
  keyword: '',
})
const form = reactive({
  name: '',
  course_id: '' as number | '',
})

async function loadCourses() {
  courses.value = await getCourses()
}

async function loadClasses() {
  loading.value = true
  try {
    classes.value = await getClasses({
      course_id: filters.course_id || undefined,
      keyword: filters.keyword.trim() || undefined,
    })
  } catch {
    ElMessage.error('班级数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.name = ''
  form.course_id = filters.course_id || ''
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写班级名称')
    return
  }
  if (typeof form.course_id !== 'number') {
    ElMessage.warning('请选择所属课程')
    return
  }
  try {
    await createClass({ name: form.name.trim(), course_id: form.course_id })
    ElMessage.success('班级创建成功')
    createDialogVisible.value = false
    await loadClasses()
  } catch {
    ElMessage.error('创建失败，请确认课程和班级名称')
  }
}

async function openStudents(row: ClassInfo) {
  selectedClass.value = row
  studentDialogVisible.value = true
  studentLoading.value = true
  try {
    students.value = await getClassStudents(row.id)
  } catch {
    ElMessage.error('学生列表加载失败，请稍后重试')
  } finally {
    studentLoading.value = false
  }
}

function openStudentAdmin(row: ClassInfo) {
  router.push({ path: '/teacher/student-admin', query: { class_id: row.id } })
}

async function handleDelete(row: ClassInfo) {
  try {
    await ElMessageBox.confirm(`确定删除班级「${row.name}」？有学生的班级需要先在学生管理中移除学生。`, '删除确认', { type: 'warning' })
    await deleteClass(row.id)
    classes.value = classes.value.filter(item => item.id !== row.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error instanceof Error ? error.message : '删除失败，请先移除班级内学生')
    }
  }
}

onMounted(async () => {
  try {
    await loadCourses()
    await loadClasses()
  } catch {
    ElMessage.error('页面初始化失败')
  }
})
</script>

<template>
  <div class="classes-page">
    <div class="page-header">
      <h1>班级管理</h1>
      <el-button type="primary" round @click="openCreate">新增班级</el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filters.course_id" placeholder="全部课程" clearable style="width: 220px" @change="loadClasses">
        <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
      </el-select>
      <el-input v-model="filters.keyword" placeholder="搜索班级名称" clearable style="width: 220px" @keyup.enter="loadClasses" />
      <el-button @click="loadClasses">搜索</el-button>
      <el-button @click="filters.course_id = ''; filters.keyword = ''; loadClasses()">重置</el-button>
    </div>

    <el-table :data="classes" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="name" label="班级名称" min-width="180" />
      <el-table-column prop="course_name" label="所属课程" min-width="180" />
      <el-table-column label="学生人数" width="100" align="center">
        <template #default="{ row }">
          <span class="count-badge">{{ row.student_count }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ row.created_at ? row.created_at.slice(0, 10) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openStudents(row)">查看学生</el-button>
          <el-button text size="small" @click="openStudentAdmin(row)">学生管理</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && classes.length === 0" class="empty-state">暂无班级</div>

    <el-dialog v-model="createDialogVisible" title="新增班级" width="420px">
      <div class="form-group">
        <label>所属课程</label>
        <el-select v-model="form.course_id" placeholder="选择课程" size="large" style="width: 100%">
          <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>班级名称</label>
        <el-input v-model="form.name" placeholder="如：2025级1班" size="large" />
      </div>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="studentDialogVisible" :title="selectedClass ? `${selectedClass.name} 学生列表` : '学生列表'" width="560px">
      <div class="student-toolbar">
        <span>共 {{ students.length }} 名学生</span>
      </div>
      <el-table :data="students" stripe v-loading="studentLoading" style="width: 100%">
        <el-table-column prop="id" label="学号" width="140" />
        <el-table-column prop="name" label="姓名" width="140" />
        <el-table-column prop="major" label="专业" min-width="160" />
      </el-table>
      <div v-if="!studentLoading && students.length === 0" class="empty-state small">该班级暂无学生</div>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header,
.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.page-header {
  justify-content: space-between;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
}

.count-badge {
  font-weight: 700;
  color: var(--color-primary);
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

.student-toolbar {
  margin-bottom: var(--space-md);
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.empty-state.small {
  padding: var(--space-xl) 0;
}
</style>

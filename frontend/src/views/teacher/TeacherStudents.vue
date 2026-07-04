<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, type Student } from '@/api/teacher'
import { getClasses, type ClassInfo } from '@/api/class'
import { getCourses, type Course } from '@/api/course'

const students = ref<Student[]>([])
const classes = ref<ClassInfo[]>([])
const courses = ref<Course[]>([])
const loading = ref(true)
const selectedCourseId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const searchQuery = ref('')
const scoreDialogVisible = ref(false)
const selectedScoreStudent = ref<Student | null>(null)

const filteredClasses = computed(() => {
  if (!selectedCourseId.value) return classes.value
  return classes.value.filter(cls => cls.course_id === selectedCourseId.value)
})

const exportButtonText = computed(() => {
  if (selectedClassId.value) return '导出当前班级'
  if (selectedCourseId.value) return '导出当前课程'
  return '导出全部学生'
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(async () => {
  try {
    const [s, c, courseList] = await Promise.all([
      getStudents(undefined, currentPage.value, pageSize.value),
      getClasses(),
      getCourses(),
    ])
    students.value = s.items
    total.value = s.total
    classes.value = c
    courses.value = courseList.filter(course => course.is_owner)
  } catch {
    ElMessage.error('学生成绩加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})

async function loadStudents() {
  loading.value = true
  try {
    const res = await getStudents(
      selectedClassId.value || undefined,
      currentPage.value,
      pageSize.value,
      searchQuery.value.trim() || undefined,
      selectedCourseId.value || undefined
    )
    students.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('学生成绩加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function handleCourseChange() {
  currentPage.value = 1
  if (
    selectedClassId.value &&
    !filteredClasses.value.some(cls => cls.id === selectedClassId.value)
  ) {
    selectedClassId.value = null
  }
  await loadStudents()
}

function handleClassChange() {
  currentPage.value = 1
  loadStudents()
}

function handleSearch() {
  currentPage.value = 1
  loadStudents()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadStudents()
}

function visibleTaskScores(row: Student) {
  return (row.task_scores || []).slice(0, 3)
}

function hasMoreTaskScores(row: Student) {
  return (row.task_scores || []).length > 3
}

function formatTaskScore(score: number | null, isCompleted: boolean) {
  if (score !== null && score !== undefined) return `${score}分`
  return isCompleted ? '0分' : '未完成'
}

function openScoreDetail(row: Student) {
  selectedScoreStudent.value = row
  scoreDialogVisible.value = true
}

// 导出 loading 状态
const exporting = ref(false)

// 导出学生成绩为 Excel
async function exportExcel() {
  if (exporting.value) return
  exporting.value = true
  try {
    // 从 localStorage 获取认证 token（与现有下载逻辑保持一致）
    const token = localStorage.getItem('auth_token')
    const params = new URLSearchParams()
    if (selectedClassId.value) params.set('class_id', String(selectedClassId.value))
    if (selectedCourseId.value) params.set('course_id', String(selectedCourseId.value))
    const url = params.toString()
      ? `/api/teacher/students/export?${params.toString()}`
      : '/api/teacher/students/export'
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('导出失败')
    const blob = await res.blob()
    const disposition = res.headers.get('Content-Disposition') ?? ''
    const match = disposition.match(/filename\*=UTF-8''(.+)/)
    const filename = match?.[1] ? decodeURIComponent(match[1]) : '学生成绩.xlsx'
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="students-page">
    <div class="page-header">
      <h1>学生成绩</h1>
    </div>

    <div class="filter-bar">
        <el-select
          v-model="selectedCourseId"
          placeholder="全部课程"
          clearable
          filterable
          size="default"
          style="width: 220px"
          @change="handleCourseChange"
        >
          <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
        <el-select
          v-model="selectedClassId"
          placeholder="全部班级"
          clearable
          size="default"
          style="width: 220px"
          @change="handleClassChange"
        >
          <el-option v-for="cls in filteredClasses" :key="cls.id" :label="`${cls.course_name} · ${cls.name}`" :value="cls.id" />
        </el-select>
        <el-input
          v-model="searchQuery"
          placeholder="搜索学号或姓名"
          size="default"
          style="width: 240px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <span class="filter-count">共 {{ total }} 名学生</span>
        <el-button
          type="primary"
          :loading="exporting"
          style="margin-left: auto"
          @click="exportExcel"
        >{{ exportButtonText }}</el-button>
      </div>

      <el-table :data="students" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="serial_no" label="序号" width="80" align="center" />
        <el-table-column prop="id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="major" label="专业" width="140" />
        <el-table-column prop="class_name" label="班级" width="140">
          <template #default="{ row }">
            {{ row.class_name || '未分班' }}
          </template>
        </el-table-column>
        <el-table-column prop="completed_tasks" label="已完成" width="100" align="center" />
        <el-table-column prop="incomplete_tasks" label="未完成" width="100" align="center" />
        <el-table-column label="完成率" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.task_completion_rate >= 80 ? '#10b981' : row.task_completion_rate >= 60 ? '#f59e0b' : '#ef4444' }">
              {{ row.task_completion_rate }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="作业成绩" min-width="260">
          <template #default="{ row }">
            <div v-if="row.task_scores?.length" class="task-score-list">
              <el-tag
                v-for="task in visibleTaskScores(row)"
                :key="task.announcement_id"
                size="small"
                :type="task.is_completed ? 'success' : 'info'"
              >
                {{ task.title }}：{{ formatTaskScore(task.score, task.is_completed) }}
              </el-tag>
              <el-button
                v-if="hasMoreTaskScores(row)"
                text
                size="small"
                @click="openScoreDetail(row)"
              >
                详细
              </el-button>
            </div>
            <span v-else class="muted-text">暂无作业</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && students.length === 0" class="empty-state">
        当前筛选条件下暂无学生成绩。可调整筛选条件，或到「学生管理」导入学生。
      </div>

      <div v-if="total > pageSize" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          background
          @current-change="handlePageChange"
        />
      </div>

    <el-dialog
      v-model="scoreDialogVisible"
      :title="selectedScoreStudent ? `${selectedScoreStudent.name}的作业成绩` : '作业成绩'"
      width="560px"
    >
      <el-table
        v-if="selectedScoreStudent"
        :data="selectedScoreStudent.task_scores || []"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="title" label="作业名称" min-width="180" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_completed ? 'success' : 'info'" size="small">
              {{ row.is_completed ? '已完成' : '未完成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="成绩" width="100" align="center">
          <template #default="{ row }">
            {{ formatTaskScore(row.score, row.is_completed) }}
          </template>
        </el-table-column>
      </el-table>
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
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
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

.loading-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: var(--space-xl);
}

.task-score-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.muted-text {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
</style>

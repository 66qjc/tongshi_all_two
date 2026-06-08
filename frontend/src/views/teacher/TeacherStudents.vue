<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, type Student } from '@/api/teacher'
import { getClasses, type ClassInfo } from '@/api/class'
import { getTaskOverview, type TaskOverview } from '@/api/announcement'
import TeacherTaskDetail from './TeacherTaskDetail.vue'

const students = ref<Student[]>([])
const classes = ref<ClassInfo[]>([])
const loading = ref(true)
const selectedClassId = ref<number | null>(null)
const taskOverview = ref<TaskOverview | null>(null)
const selectedTaskId = ref<number | null>(null)
const drawerVisible = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(async () => {
  try {
    const [s, c, overview] = await Promise.all([
      getStudents(undefined, currentPage.value, pageSize.value),
      getClasses(),
      getTaskOverview(),
    ])
    students.value = s.items
    total.value = s.total
    classes.value = c
    taskOverview.value = overview
  } catch {
    ElMessage.error('学生成绩加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})

function openTaskDetail(taskId: number) {
  selectedTaskId.value = taskId
  drawerVisible.value = true
}

const searchQuery = ref('')

async function loadStudents() {
  loading.value = true
  try {
    const res = await getStudents(
      selectedClassId.value || undefined,
      currentPage.value,
      pageSize.value,
      searchQuery.value.trim() || undefined
    )
    students.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('学生成绩加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
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

// 导出 loading 状态
const exporting = ref(false)

// 导出学生成绩为 Excel
async function exportExcel() {
  if (exporting.value) return
  exporting.value = true
  try {
    // 从 localStorage 获取认证 token（与现有下载逻辑保持一致）
    const token = localStorage.getItem('auth_token')
    const url = selectedClassId.value
      ? `/api/teacher/students/export?class_id=${selectedClassId.value}`
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

    <!-- 任务概览卡片 -->
    <div v-if="taskOverview && taskOverview.total_tasks > 0" class="overview-cards">
      <div class="overview-card">
        <span class="overview-num">{{ taskOverview.total_tasks }}</span>
        <span class="overview-label">总任务数</span>
      </div>
      <div class="overview-card">
        <span class="overview-num success">{{ taskOverview.total_completed }}</span>
        <span class="overview-label">已完成</span>
      </div>
      <div class="overview-card">
        <span class="overview-num warn">{{ taskOverview.total_incomplete }}</span>
        <span class="overview-label">未完成</span>
      </div>
    </div>

    <!-- 作业列表 -->
    <div v-if="taskOverview && taskOverview.tasks.length > 0" class="task-list">
      <h3 class="section-title">作业列表</h3>
      <div class="task-cards">
        <div
          v-for="task in taskOverview.tasks"
          :key="task.id"
          class="task-card"
          @click="openTaskDetail(task.id)"
        >
          <div class="task-card-header">
            <span class="task-title">{{ task.title }}</span>
            <el-tag
              :type="task.is_expired ? 'warning' : 'success'"
              size="small"
            >
              {{ task.is_expired ? '已截止' : '进行中' }}
            </el-tag>
          </div>
          <div class="task-card-body">
            <span class="task-classes">{{ task.class_names.join('、') }}</span>
            <span class="task-progress">
              完成 <strong>{{ task.completed_count }}</strong> / {{ task.total_students }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="filter-bar">
        <el-select
          v-model="selectedClassId"
          placeholder="全部班级"
          clearable
          size="default"
          style="width: 220px"
          @change="handleClassChange"
        >
          <el-option v-for="cls in classes" :key="cls.id" :label="`${cls.course_name} · ${cls.name}`" :value="cls.id" />
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
        >{{ selectedClassId ? '导出当前班级' : '导出全部学生' }}</el-button>
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
      </el-table>

      <div v-if="!loading && students.length === 0" class="empty-state">
        暂无学生成绩，请先导入学生或创建班级。
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

    <!-- 作业详情 Drawer -->
    <TeacherTaskDetail v-model="drawerVisible" :announcement-id="selectedTaskId" />
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

.overview-cards {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.overview-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: var(--space-lg) var(--space-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.overview-num {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary);
}

.overview-num.success {
  color: #10b981;
}

.overview-num.warn {
  color: #ef4444;
}

.overview-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: var(--space-xs);
}

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  padding-left: var(--space-sm);
  border-left: 3px solid var(--color-primary);
}

.task-list {
  margin-bottom: var(--space-xl);
}

.task-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.task-card {
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.task-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.task-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-xs);
}

.task-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
}

.task-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.task-progress strong {
  color: var(--color-primary);
  font-weight: 700;
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
</style>

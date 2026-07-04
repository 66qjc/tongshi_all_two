<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTaskOverview, type TaskOverview } from '@/api/announcement'
import { getCourses, type Course } from '@/api/course'

const router = useRouter()
const route = useRoute()

const courses = ref<Course[]>([])
const taskOverview = ref<TaskOverview | null>(null)
const loading = ref(true)
const selectedCourseId = ref<number | null>(null)
const taskSearchQuery = ref('')

const tasks = computed(() => taskOverview.value?.tasks ?? [])

const filteredTasks = computed(() => {
  const keyword = taskSearchQuery.value.trim().toLowerCase()
  if (!keyword) return tasks.value
  return tasks.value.filter(task => {
    const searchable = `${task.title} ${task.course_name} ${task.class_names.join(' ')}`.toLowerCase()
    return searchable.includes(keyword)
  })
})

async function loadTaskOverview() {
  taskOverview.value = await getTaskOverview(selectedCourseId.value || undefined)
}

async function handleCourseChange() {
  loading.value = true
  try {
    await loadTaskOverview()
  } catch {
    ElMessage.error('作业列表加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function goToDetail(taskId: number) {
  router.push({ name: 'teacher-task-report-detail', params: { taskId } })
}

function openTaskFromQuery() {
  const queryTaskId = Number(route.query.task_id)
  if (!Number.isInteger(queryTaskId) || queryTaskId <= 0) return
  if (tasks.value.some(task => task.id === queryTaskId)) {
    goToDetail(queryTaskId)
    return
  }
  ElMessage.warning('未找到对应作业，请在列表中选择')
}

onMounted(async () => {
  try {
    const [courseList] = await Promise.all([
      getCourses(),
      loadTaskOverview(),
    ])
    courses.value = courseList.filter(course => course.is_owner)
    openTaskFromQuery()
  } catch {
    ElMessage.error('作业数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="task-report-page">
    <div class="page-header">
      <h1>作业完成</h1>
    </div>

    <section class="task-list-section">
      <div class="task-list-header">
        <h2 class="section-title">作业列表</h2>
        <div class="task-filters">
          <el-input
            v-model="taskSearchQuery"
            placeholder="搜索作业名称、课程或班级"
            clearable
            size="default"
            style="width: 260px"
          />
          <el-select
            v-model="selectedCourseId"
            placeholder="全部课程"
            clearable
            filterable
            size="default"
            style="width: 220px"
            @change="handleCourseChange"
          >
            <el-option
              v-for="course in courses"
              :key="course.id"
              :label="course.name"
              :value="course.id"
            />
          </el-select>
        </div>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="tasks.length === 0" class="empty-state">暂无已发布作业。请先在「发布作业」中发布到班级。</div>
      <div v-else-if="filteredTasks.length === 0" class="empty-state">没有匹配的作业，请调整搜索条件。</div>
      <div v-else class="task-cards">
        <button
          v-for="task in filteredTasks"
          :key="task.id"
          class="task-card"
          type="button"
          @click="goToDetail(task.id)"
        >
          <div class="task-card-main">
            <div class="task-card-title">
              <strong>{{ task.title }}</strong>
              <span>（{{ task.course_name || '未命名课程' }}）</span>
            </div>
            <div class="task-card-classes">{{ task.class_names.join('、') || '未设置班级' }}</div>
          </div>
          <div class="task-card-side">
            <el-tag :type="task.is_expired ? 'warning' : 'success'" size="small">
              {{ task.is_expired ? '已截止' : '进行中' }}
            </el-tag>
            <span class="task-progress">
              完成 <strong>{{ task.completed_count }}</strong> / {{ task.total_students }}
            </span>
          </div>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.task-report-page {
  padding-bottom: var(--space-2xl);
}

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

.task-list-section {
  margin-bottom: var(--space-xl);
}

.task-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.task-filters {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--space-md);
  padding-left: var(--space-sm);
  border-left: 3px solid var(--color-primary);
}

.task-list-header .section-title {
  margin-bottom: 0;
}

.task-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.task-card {
  width: 100%;
  min-height: 106px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast), background var(--duration-fast);
}

.task-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.task-card-main {
  min-width: 0;
}

.task-card-title {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 2px;
  font-size: 0.98rem;
  color: var(--color-text);
}

.task-card-title strong {
  font-weight: 700;
}

.task-card-classes {
  margin-top: var(--space-sm);
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.task-card-side {
  display: flex;
  min-width: 130px;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-sm);
  color: var(--color-text-muted);
  font-size: 0.88rem;
}

.task-progress strong {
  color: var(--color-primary);
  font-weight: 700;
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

@media (max-width: 760px) {
  .task-list-header,
  .task-card {
    align-items: stretch;
    flex-direction: column;
  }

  .task-filters,
  .task-filters :deep(.el-input),
  .task-filters :deep(.el-select) {
    width: 100% !important;
  }

  .task-card-side {
    min-width: 0;
    align-items: flex-start;
  }
}
</style>

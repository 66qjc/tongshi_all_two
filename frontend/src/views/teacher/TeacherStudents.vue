<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents, type Student } from '@/api/teacher'
import { getAnnouncements, getCompletionReport, type Announcement, type CompletionReport } from '@/api/announcement'

const students = ref<Student[]>([])
const announcements = ref<Announcement[]>([])
const loading = ref(true)
const activeTab = ref('students')

onMounted(async () => {
  try {
    const [s, a] = await Promise.all([getStudents(), getAnnouncements()])
    students.value = s
    announcements.value = a
  } catch {
    ElMessage.error('学生数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})

const searchQuery = ref('')

const filteredStudents = computed(() => {
  if (!searchQuery.value.trim()) return students.value
  const q = searchQuery.value.trim().toLowerCase()
  return students.value.filter(s =>
    s.id.toLowerCase().includes(q) || s.name.toLowerCase().includes(q),
  )
})

// Task completion
const selectedAnnouncementId = ref<number | null>(null)
const reportData = ref<CompletionReport | null>(null)
const reportLoading = ref(false)

async function loadReport(id: number) {
  reportLoading.value = true
  try {
    reportData.value = await getCompletionReport(id)
  } catch {
    ElMessage.error('任务完成情况加载失败，请稍后重试')
  } finally {
    reportLoading.value = false
  }
}

function handleAnnouncementChange(val: number | null) {
  if (val) loadReport(val)
  else reportData.value = null
}
</script>

<template>
  <div class="students-page">
    <div class="page-header">
      <h1>学生数据</h1>
      <div class="tab-bar">
        <button class="tab-btn" :class="{ active: activeTab === 'students' }" @click="activeTab = 'students'">学生列表</button>
        <button class="tab-btn" :class="{ active: activeTab === 'tasks' }" @click="activeTab = 'tasks'">任务完成</button>
      </div>
    </div>

    <!-- Students tab -->
    <template v-if="activeTab === 'students'">
      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索学号或姓名"
          size="default"
          style="width: 240px"
          clearable
        />
        <span class="filter-count">共 {{ filteredStudents.length }} 名学生</span>
      </div>

      <el-table :data="filteredStudents" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="major" label="专业" width="140" />
        <el-table-column label="学习进度" min-width="160">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress :percentage="row.progress" :stroke-width="6" :show-text="false"
                           color="var(--color-learn)" style="flex: 1" />
              <span class="progress-text">{{ row.progress }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="exercises" label="练习题数" width="100" align="center" />
        <el-table-column label="正确率" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.accuracy >= 80 ? '#10b981' : row.accuracy >= 70 ? '#f59e0b' : '#ef4444' }">
              {{ row.accuracy }}%
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && filteredStudents.length === 0" class="empty-state">
        暂无学生数据，请先导入学生或创建班级。
      </div>
    </template>

    <!-- Tasks tab -->
    <template v-if="activeTab === 'tasks'">
      <div class="filter-bar">
        <el-select
          v-model="selectedAnnouncementId"
          placeholder="选择任务查看完成情况"
          size="default"
          style="width: 320px"
          clearable
          @change="handleAnnouncementChange"
        >
          <el-option
            v-for="a in announcements.filter(a => a.type === 'quiz')"
            :key="a.id"
            :label="a.title"
            :value="a.id"
          />
        </el-select>
      </div>

      <div v-if="reportLoading" class="loading-state">加载中...</div>

      <div v-else-if="announcements.filter(a => a.type === 'quiz').length === 0" class="empty-state">
        暂无可查看的题目任务。
      </div>

      <div v-else-if="reportData" class="report-content">
        <div class="report-header">
          <h3>{{ reportData.announcement_title }}</h3>
          <el-tag v-if="reportData.is_expired" type="warning" size="small">已过截止时间</el-tag>
        </div>
        <div class="report-stats">
          <div class="report-stat">
            <span class="stat-num">{{ reportData.completed_students }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <div class="report-stat">
            <span class="stat-num warn">{{ reportData.total_students - reportData.completed_students }}</span>
            <span class="stat-label">未完成</span>
          </div>
          <div class="report-stat">
            <span class="stat-num">{{ reportData.total_students }}</span>
            <span class="stat-label">总人数</span>
          </div>
        </div>
        <el-progress
          :percentage="reportData.total_students > 0 ? Math.round(reportData.completed_students / reportData.total_students * 100) : 0"
          :stroke-width="10"
          color="var(--color-primary)"
          style="margin-bottom: var(--space-lg)"
        />
        <div v-if="reportData.incomplete_students.length > 0">
          <h4 class="incomplete-title">未完成学生名单</h4>
          <el-table :data="reportData.incomplete_students" stripe style="width: 100%">
            <el-table-column prop="id" label="学号" width="120" />
            <el-table-column prop="name" label="姓名" width="120" />
          </el-table>
        </div>
        <div v-else class="all-done">所有学生已完成</div>
      </div>

      <div v-else-if="!selectedAnnouncementId" class="empty-state">
        请选择一个任务查看完成情况
      </div>
    </template>
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

.progress-cell {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.progress-text {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  min-width: 36px;
}

.tab-bar {
  display: flex;
  gap: var(--space-xs);
}

.tab-btn {
  padding: 0.4rem 1rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.tab-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tab-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
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

.report-content {
  max-width: 600px;
}

.report-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.report-header h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
}

.report-stats {
  display: flex;
  gap: var(--space-xl);
  margin-bottom: var(--space-lg);
}

.report-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary);
}

.stat-num.warn {
  color: #ef4444;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.incomplete-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-md);
}

.all-done {
  text-align: center;
  padding: var(--space-xl);
  color: #10b981;
  font-weight: 600;
  font-size: 1rem;
}
</style>

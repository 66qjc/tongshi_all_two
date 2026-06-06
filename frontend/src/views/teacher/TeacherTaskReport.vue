<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAnnouncements, getCompletionReport, type Announcement, type CompletionReport } from '@/api/announcement'

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '未设置'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getStatusText(isExpired: boolean, deadline: string | null): string {
  if (!deadline) return '无截止时间'
  if (isExpired) return '已过期'
  return '进行中'
}

function getStatusClass(isExpired: boolean, deadline: string | null): string {
  if (!deadline) return 'status-no-deadline'
  if (isExpired) return 'status-expired'
  return 'status-active'
}

function getScoreClass(score: number): string {
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

function getNormalizedScore(score: number, totalQuestions: number): number {
  if (totalQuestions <= 0) return 0
  // 如果分数已是一百分制（大于题目总数），直接返回
  if (score > totalQuestions) return Math.min(score, 100)
  // 否则等比例换算为百分制
  return Math.round(score / totalQuestions * 100)
}

const route = useRoute()
const announcements = ref<Announcement[]>([])
const loading = ref(true)

const selectedAnnouncementId = ref<number | null>(null)
const selectedClassId = ref<number | null>(null)
const reportData = ref<CompletionReport | null>(null)
const reportLoading = ref(false)
const completedPage = ref(1)
const completedPageSize = ref(20)
const incompletePage = ref(1)
const incompletePageSize = ref(20)

const filteredCompletedStudents = computed(() => {
  if (!reportData.value) return []
  return reportData.value.completed_students.items
})

const filteredIncompleteStudents = computed(() => {
  if (!reportData.value) return []
  return reportData.value.incomplete_students.items
})

// 班级选项（包含"全部班级"）
const classOptions = computed(() => {
  if (!reportData.value?.per_class) return []
  return [
    { label: '全部班级', value: null },
    ...reportData.value.per_class.map(c => ({
      label: c.class_name,
      value: c.class_id
    }))
  ]
})

async function loadReport(id: number, resetClass = false) {
  reportLoading.value = true
  if (resetClass) selectedClassId.value = null
  try {
    reportData.value = await getCompletionReport(id, {
      class_id: selectedClassId.value || undefined,
      completed_page: completedPage.value,
      completed_page_size: completedPageSize.value,
      incomplete_page: incompletePage.value,
      incomplete_page_size: incompletePageSize.value,
    })
  } catch {
    ElMessage.error('作业完成情况加载失败，请稍后重试')
  } finally {
    reportLoading.value = false
  }
}

function handleCompletedPageChange(newPage: number) {
  completedPage.value = newPage
  if (selectedAnnouncementId.value) loadReport(selectedAnnouncementId.value)
}

function handleIncompletePageChange(newPage: number) {
  incompletePage.value = newPage
  if (selectedAnnouncementId.value) loadReport(selectedAnnouncementId.value)
}

function handleAnnouncementChange(val: number | null) {
  completedPage.value = 1
  incompletePage.value = 1
  if (val) loadReport(val, true)
  else reportData.value = null
}

function handleClassChange() {
  completedPage.value = 1
  incompletePage.value = 1
  if (selectedAnnouncementId.value) loadReport(selectedAnnouncementId.value)
}

onMounted(async () => {
  try {
    announcements.value = await getAnnouncements()
    // 支持从 URL query 直接定位到某个任务
    const taskId = Number(route.query.task_id)
    if (Number.isFinite(taskId) && taskId > 0) {
      selectedAnnouncementId.value = taskId
      await loadReport(taskId, true)
    }
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

    <div class="filter-bar">
      <el-select
        v-model="selectedAnnouncementId"
        placeholder="选择作业查看完成情况"
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
      <el-select
        v-if="classOptions.length > 0"
        v-model="selectedClassId"
        placeholder="选择班级"
        size="default"
        style="width: 200px"
        clearable
        @change="handleClassChange"
      >
        <el-option
          v-for="opt in classOptions"
          :key="opt.value ?? 'all'"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>

    <div v-else-if="announcements.filter(a => a.type === 'quiz').length === 0" class="empty-state">
      暂无可查看的作业任务。
    </div>

    <template v-else>
      <div v-if="reportLoading" class="loading-state">加载中...</div>

      <div v-else-if="reportData" class="report-content">
        <div class="report-card">
          <div class="report-header">
            <h3>{{ reportData.announcement_title }}</h3>
            <el-tag :type="reportData.is_expired ? 'warning' : (reportData.deadline ? 'success' : 'info')" size="small">
              {{ getStatusText(reportData.is_expired, reportData.deadline) }}
            </el-tag>
          </div>
          <div class="report-meta">
            <div class="meta-item">
              <span class="meta-label">发布时间</span>
              <span class="meta-value">{{ formatDate(reportData.created_at) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">截止时间</span>
              <span class="meta-value" :class="{ 'meta-value-expired': reportData.is_expired }">
                {{ formatDate(reportData.deadline) }}
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">涉及班级</span>
              <span class="meta-value">{{ reportData.class_names.join('、') || '无' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">题目数量</span>
              <span class="meta-value">{{ reportData.total_questions }} 题</span>
            </div>
          </div>
          <div class="report-stats">
            <div class="report-stat">
              <span class="stat-num">{{ reportData.completed_count }}</span>
              <span class="stat-label">已完成</span>
            </div>
            <div class="report-stat">
              <span class="stat-num warn">{{ reportData.total_students - reportData.completed_count }}</span>
              <span class="stat-label">未完成</span>
            </div>
            <div class="report-stat">
              <span class="stat-num">{{ reportData.total_students }}</span>
              <span class="stat-label">总人数</span>
            </div>
          </div>
          <el-progress
            :percentage="reportData.total_students > 0 ? Math.round(reportData.completed_count / reportData.total_students * 100) : 0"
            :stroke-width="10"
            color="var(--color-primary)"
            style="margin-bottom: 0"
          />
        </div>
        
        <!-- 分班小计 -->
        <div v-if="reportData.per_class?.length" class="per-class">
          <h4 class="section-title">分班小计</h4>
          <el-table :data="reportData.per_class" stripe style="width: 100%">
            <el-table-column prop="class_name" label="班级" min-width="140" />
            <el-table-column prop="total" label="总人数" width="100" />
            <el-table-column prop="completed" label="已完成" width="100" />
          </el-table>
        </div>
        
        <!-- 已完成学生名单 -->
        <div v-if="filteredCompletedStudents.length > 0" class="students-table">
          <h4 class="section-title">已完成学生名单（{{ reportData.completed_students?.total || 0 }} 人）</h4>
          <el-table :data="filteredCompletedStudents" stripe style="width: 100%; max-width: 700px;">
            <el-table-column prop="id" label="学号" width="140"/>
            <el-table-column prop="name" label="姓名" width="140" />
            <el-table-column prop="major" label="专业" width="200"/>
            <el-table-column prop="class_name" label="班级" width="220"/>
            <el-table-column
              label="成绩"
              width="100"
              align="center"
            >
              <template #default="scope">
                <span :class="getScoreClass(getNormalizedScore(scope.row.score, scope.row.total_questions))" class="score-cell">
                  {{ getNormalizedScore(scope.row.score, scope.row.total_questions) }}分
                </span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="(reportData.completed_students?.total || 0) > completedPageSize" class="pagination-wrap">
            <el-pagination
              background
              layout="prev, pager, next"
              :total="reportData.completed_students?.total || 0"
              :page-size="completedPageSize"
              :current-page="completedPage"
              @current-change="handleCompletedPageChange"
            />
          </div>
        </div>

        <!-- 未完成学生名单 -->
        <div v-if="filteredIncompleteStudents.length > 0" class="students-table">
          <h4 class="section-title">未完成学生名单（{{ reportData.incomplete_students?.total || 0 }} 人）</h4>
          <el-table :data="filteredIncompleteStudents" stripe style="width: 100%; max-width: 550px;">
            <el-table-column prop="id" label="学号" width="140" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="major" label="专业" width="130" />
            <el-table-column prop="class_name" label="班级" width="110" />
          </el-table>
          <div v-if="(reportData.incomplete_students?.total || 0) > incompletePageSize" class="pagination-wrap">
            <el-pagination
              background
              layout="prev, pager, next"
              :total="reportData.incomplete_students?.total || 0"
              :page-size="incompletePageSize"
              :current-page="incompletePage"
              @current-change="handleIncompletePageChange"
            />
          </div>
        </div>
        
        <!-- 全部完成提示 -->
        <div v-if="filteredCompletedStudents.length === 0 && filteredIncompleteStudents.length === 0" class="all-done">
          所有学生已完成
        </div>
      </div>

      <div v-else class="empty-state">
        请选择一个作业查看完成情况
      </div>
    </template>
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
  padding-bottom: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
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
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-lg);
}

.loading-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
}

.empty-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.report-content {
  max-width: 900px;
}

.report-card {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border-light);
}

.report-header h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
}

.report-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: 0.9rem;
  color: var(--color-text);
  font-weight: 500;
}

.meta-value-expired {
  color: #ef4444;
  font-weight: 600;
}

.report-stats {
  display: flex;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
}

.report-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-sm);
}

.stat-num {
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1.2;
}

.stat-num.warn {
  color: #ef4444;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.section-box {
  margin-bottom: var(--space-xl);
}

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  padding-left: var(--space-sm);
  border-left: 3px solid var(--color-primary);
}

.all-done {
  text-align: center;
  padding: var(--space-xl);
  color: #10b981;
  font-weight: 600;
  font-size: 1rem;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: var(--space-md) 0;
}

.students-table {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.per-class {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  margin-bottom: var(--space-lg);
}

.score-cell {
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 6px;
  display: inline-block;
}

.score-excellent {
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
}

.score-good {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.15);
}

.score-pass {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.15);
}

.score-fail {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.15);
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCompletionReport, type CompletionReport } from '@/api/announcement'

const route = useRoute()
const router = useRouter()

const taskId = computed(() => Number(route.params.taskId))
const ALL_CLASSES_VALUE = 'all'

// ── 状态 ──
const report = ref<CompletionReport | null>(null)
const loading = ref(true)
const selectedClassId = ref<number | typeof ALL_CLASSES_VALUE>(ALL_CLASSES_VALUE)
const activeTab = ref<'completed' | 'incomplete'>('completed')
const completedPage = ref(1)
const incompletePage = ref(1)
const pageSize = ref(20)
const searchCompleted = ref('')
const searchIncomplete = ref('')

// ── 工具函数 ──
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '未设置'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getStatusText(isExpired: boolean, deadline: string | null): string {
  if (!deadline) return '无截止时间'
  if (isExpired) return '已截止'
  return '进行中'
}

function getScoreClass(score: number, totalQuestions: number): string {
  const pct = getNormalizedScore(score, totalQuestions)
  if (pct >= 90) return 'score-excellent'
  if (pct >= 80) return 'score-good'
  if (pct >= 60) return 'score-pass'
  return 'score-fail'
}

function getNormalizedScore(score: number, totalQuestions: number): number {
  if (totalQuestions <= 0) return 0
  if (score > totalQuestions) return Math.min(score, 100)
  return Math.round((score / totalQuestions) * 100)
}

// ── 班级筛选选项 ──
const classOptions = computed(() => {
  if (!report.value?.per_class) return []
  return [
    { label: '全部班级', value: ALL_CLASSES_VALUE },
    ...report.value.per_class.map(item => ({
      label: item.class_name,
      value: item.class_id,
    })),
  ]
})

// ── 搜索过滤 ──
const filteredCompleted = computed(() => {
  if (!report.value) return []
  const items = report.value.completed_students.items
  if (!searchCompleted.value.trim()) return items
  const kw = searchCompleted.value.trim().toLowerCase()
  return items.filter(s => s.id.toLowerCase().includes(kw) || s.name.toLowerCase().includes(kw))
})

const filteredIncomplete = computed(() => {
  if (!report.value) return []
  const items = report.value.incomplete_students.items
  if (!searchIncomplete.value.trim()) return items
  const kw = searchIncomplete.value.trim().toLowerCase()
  return items.filter(s => s.id.toLowerCase().includes(kw) || s.name.toLowerCase().includes(kw))
})

// ── 数据加载 ──
async function loadReport() {
  if (!Number.isFinite(taskId.value) || taskId.value <= 0) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    report.value = await getCompletionReport(taskId.value, {
      class_id: selectedClassId.value === ALL_CLASSES_VALUE ? undefined : selectedClassId.value,
      completed_page: completedPage.value,
      completed_page_size: pageSize.value,
      incomplete_page: incompletePage.value,
      incomplete_page_size: pageSize.value,
    })
  } catch {
    ElMessage.error('作业完成情况加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function handleClassChange() {
  completedPage.value = 1
  incompletePage.value = 1
  loadReport()
}

function handleCompletedPageChange(p: number) {
  completedPage.value = p
  loadReport()
}

function handleIncompletePageChange(p: number) {
  incompletePage.value = p
  loadReport()
}

// ── 导出 CSV ──
async function exportTab(tab: 'completed' | 'incomplete') {
  if (!Number.isFinite(taskId.value)) return
  try {
    const full = await getCompletionReport(taskId.value, {
      class_id: selectedClassId.value === ALL_CLASSES_VALUE ? undefined : selectedClassId.value,
      completed_page: 1,
      completed_page_size: 9999,
      incomplete_page: 1,
      incomplete_page_size: 9999,
    })
    const students = tab === 'completed' ? full.completed_students.items : full.incomplete_students.items
    if (!students.length) {
      ElMessage.warning('没有可导出的数据')
      return
    }
    const BOM = '﻿'
    let csv: string
    if (tab === 'completed') {
      csv = BOM + '学号,姓名,专业,班级,得分,题目总数,正确率\n'
      csv += students.map(s =>
        `"${s.id}","${s.name}","${s.major}","${s.class_name}",${getNormalizedScore(s.score, s.total_questions)},${s.total_questions},${getNormalizedScore(s.score, s.total_questions)}%`
      ).join('\n')
    } else {
      csv = BOM + '学号,姓名,专业,班级\n'
      csv += students.map(s => `"${s.id}","${s.name}","${s.major}","${s.class_name}"`).join('\n')
    }
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const label = tab === 'completed' ? '已完成' : '未完成'
    a.download = `${report.value?.announcement_title ?? '作业'}-${label}学生.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  }
}

onMounted(() => {
  loadReport()
})
</script>

<template>
  <div class="detail-page">
    <!-- 顶部导航 -->
    <div class="detail-nav">
      <button class="btn-back" type="button" @click="router.back()">
        <span class="back-arrow">←</span>
        <span>返回列表</span>
      </button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">加载中...</div>

    <!-- 无效任务 ID -->
    <div v-else-if="!report" class="empty-state">无法加载作业详情，请返回重试。</div>

    <!-- 报告内容 -->
    <template v-else>
      <!-- 班级筛选 -->
      <div v-if="classOptions.length > 0" class="filter-bar">
        <span class="filter-label">筛选班级</span>
        <el-select
          v-model="selectedClassId"
          placeholder="全部班级"
          size="default"
          style="width: 200px"
          clearable
          @change="handleClassChange"
        >
          <el-option
            v-for="opt in classOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>

      <!-- 作业信息卡片 -->
      <div class="report-card">
        <div class="report-header">
          <h3>{{ report.announcement_title }}</h3>
          <el-tag
            :type="report.is_expired ? 'warning' : (report.deadline ? 'success' : 'info')"
            size="small"
          >
            {{ getStatusText(report.is_expired, report.deadline) }}
          </el-tag>
        </div>
        <div class="report-meta">
          <div class="meta-item">
            <span class="meta-label">发布时间</span>
            <span class="meta-value">{{ formatDate(report.created_at) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">截止时间</span>
            <span class="meta-value" :class="{ 'meta-value-expired': report.is_expired }">
              {{ formatDate(report.deadline) }}
            </span>
          </div>
          <div class="meta-item">
            <span class="meta-label">涉及班级</span>
            <span class="meta-value">{{ report.class_names.join('、') || '无' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">题目数量</span>
            <span class="meta-value">{{ report.total_questions }} 题</span>
          </div>
        </div>
        <div class="report-stats">
          <div class="report-stat">
            <span class="stat-num">{{ report.completed_count }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <div class="report-stat">
            <span class="stat-num warn">{{ report.total_students - report.completed_count }}</span>
            <span class="stat-label">未完成</span>
          </div>
          <div class="report-stat">
            <span class="stat-num">{{ report.total_students }}</span>
            <span class="stat-label">总人数</span>
          </div>
        </div>
        <el-progress
          :percentage="report.total_students > 0 ? Math.round(report.completed_count / report.total_students * 100) : 0"
          :stroke-width="10"
          color="var(--color-primary)"
          style="margin-bottom: 0"
        />
      </div>

      <!-- 分班小计 -->
      <div v-if="report.per_class?.length" class="per-class-card">
        <h4 class="section-title">分班小计</h4>
        <el-table :data="report.per_class" stripe style="width: 100%">
          <el-table-column prop="class_name" label="班级" min-width="140" />
          <el-table-column prop="total" label="总人数" width="100" align="center" />
          <el-table-column prop="completed" label="已完成" width="100" align="center" />
          <el-table-column label="完成率" width="100" align="center">
            <template #default="{ row }">
              {{ row.total > 0 ? Math.round(row.completed / row.total * 100) : 0 }}%
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 学生名单（Tabs 切换） -->
      <div class="students-card">
        <el-tabs v-model="activeTab">
          <el-tab-pane :label="`已完成 (${report.completed_students.total})`" name="completed">
            <div class="tab-toolbar">
              <el-input
                v-model="searchCompleted"
                placeholder="搜索学号或姓名"
                size="default"
                style="width: 220px"
                clearable
              />
              <el-button size="small" @click="exportTab('completed')">导出已完成</el-button>
            </div>
            <el-table :data="filteredCompleted" stripe style="width: 100%">
              <el-table-column prop="id" label="学号" width="140" />
              <el-table-column prop="name" label="姓名" width="120" />
              <el-table-column prop="major" label="专业" min-width="160" />
              <el-table-column prop="class_name" label="班级" width="180" />
              <el-table-column label="成绩" width="100" align="center">
                <template #default="{ row }">
                  <span
                    :class="getScoreClass(row.score, row.total_questions)"
                    class="score-cell"
                  >
                    {{ getNormalizedScore(row.score, row.total_questions) }}分
                  </span>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="report.completed_students.total > pageSize" class="pagination-wrap">
              <el-pagination
                background
                layout="prev, pager, next"
                :total="report.completed_students.total"
                :page-size="pageSize"
                :current-page="completedPage"
                @current-change="handleCompletedPageChange"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`未完成 (${report.incomplete_students.total})`" name="incomplete">
            <div class="tab-toolbar">
              <el-input
                v-model="searchIncomplete"
                placeholder="搜索学号或姓名"
                size="default"
                style="width: 220px"
                clearable
              />
              <el-button size="small" @click="exportTab('incomplete')">导出未完成</el-button>
            </div>
            <el-table :data="filteredIncomplete" stripe style="width: 100%">
              <el-table-column prop="id" label="学号" width="140" />
              <el-table-column prop="name" label="姓名" width="120" />
              <el-table-column prop="major" label="专业" min-width="160" />
              <el-table-column prop="class_name" label="班级" width="180" />
            </el-table>
            <div v-if="report.incomplete_students.total > pageSize" class="pagination-wrap">
              <el-pagination
                background
                layout="prev, pager, next"
                :total="report.incomplete_students.total"
                :page-size="pageSize"
                :current-page="incompletePage"
                @current-change="handleIncompletePageChange"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-page {
  max-width: 960px;
  padding-bottom: var(--space-2xl);
}

/* ── 顶部导航 ── */
.detail-nav {
  margin-bottom: var(--space-lg);
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-md);
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.btn-back:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.back-arrow {
  font-size: 1.1rem;
}

/* ── 加载/空状态 ── */
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

/* ── 班级筛选 ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
}

.filter-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
}

/* ── 报告卡片 ── */
.report-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border-light);
}

.report-header h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
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

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--space-md);
  padding-left: var(--space-sm);
  border-left: 3px solid var(--color-primary);
}

/* ── 分班小计 ── */
.per-class-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

/* ── 学生名单 ── */
.students-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
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

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: var(--space-md) 0;
}

/* ── 响应式 ── */
@media (max-width: 760px) {
  .report-header,
  .report-stats {
    flex-direction: column;
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

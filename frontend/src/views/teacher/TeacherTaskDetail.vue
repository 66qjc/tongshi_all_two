<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getCompletionReport, type CompletionReport } from '@/api/announcement'

const props = defineProps<{
  modelValue: boolean
  announcementId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

// ── 状态 ──
const report = ref<CompletionReport | null>(null)
const loading = ref(false)
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
  return Math.round(score / totalQuestions * 100)
}

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
  if (!props.announcementId || loading.value) return
  loading.value = true
  try {
    report.value = await getCompletionReport(props.announcementId, {
      completed_page: completedPage.value,
      completed_page_size: pageSize.value,
      incomplete_page: incompletePage.value,
      incomplete_page_size: pageSize.value,
    })
  } catch {
    ElMessage.error('作业详情加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

watch([() => props.announcementId, visible], ([newId, isVisible]) => {
  if (newId != null && isVisible) {
    completedPage.value = 1
    incompletePage.value = 1
    searchCompleted.value = ''
    searchIncomplete.value = ''
    activeTab.value = 'completed'
    loadReport()
  } else if (!isVisible) {
    report.value = null
  }
})

// ── 分页 ──
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
  if (!props.announcementId) return
  try {
    // 拉取全量数据
    const full = await getCompletionReport(props.announcementId, {
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
    // 生成 CSV（BOM 头支持中文）
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
</script>

<template>
  <el-drawer
    v-model="visible"
    title="作业详情"
    size="780px"
    direction="rtl"
  >
    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">加载中...</div>

    <template v-else-if="report">
      <!-- 作业信息卡片 -->
      <div class="detail-card">
        <div class="detail-header">
          <h3>{{ report.announcement_title }}</h3>
          <el-tag
            :type="report.is_expired ? 'warning' : report.deadline ? 'success' : 'info'"
            size="small"
          >
            {{ report.is_expired ? '已截止' : report.deadline ? '进行中' : '无截止时间' }}
          </el-tag>
        </div>
        <div class="detail-meta">
          <div class="meta-item">
            <span class="meta-label">截止时间</span>
            <span class="meta-value" :class="{ 'text-expired': report.is_expired }">
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

        <!-- 完成进度 -->
        <div class="detail-stats">
          <div class="stat-row">
            <span class="stat-num">{{ report.completed_count }}</span>
            <span class="stat-sep">/</span>
            <span class="stat-total">{{ report.total_students }}</span>
            <span class="stat-label">已完成</span>
          </div>
          <el-progress
            :percentage="report.total_students > 0 ? Math.round(report.completed_count / report.total_students * 100) : 0"
            :stroke-width="8"
            color="var(--color-primary)"
          />
        </div>
      </div>

      <!-- 分班小计 -->
      <div v-if="report.per_class?.length" class="detail-card">
        <h4 class="section-title">分班小计</h4>
        <el-table :data="report.per_class" stripe size="small">
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

      <!-- Tabs: 已完成 / 未完成 -->
      <div class="detail-card students-section">
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
            <el-table :data="filteredCompleted" stripe size="small">
              <el-table-column prop="id" label="学号" width="120" />
              <el-table-column prop="name" label="姓名" width="100" />
              <el-table-column prop="major" label="专业" width="140" />
              <el-table-column prop="class_name" label="班级" width="120" />
              <el-table-column label="得分" width="100" align="center">
                <template #default="{ row }">
                  <span :class="getScoreClass(row.score, row.total_questions)" class="score-cell">
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
                size="small"
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
            <el-table :data="filteredIncomplete" stripe size="small">
              <el-table-column prop="id" label="学号" width="120" />
              <el-table-column prop="name" label="姓名" width="100" />
              <el-table-column prop="major" label="专业" width="140" />
              <el-table-column prop="class_name" label="班级" width="120" />
            </el-table>
            <div v-if="report.incomplete_students.total > pageSize" class="pagination-wrap">
              <el-pagination
                background
                layout="prev, pager, next"
                :total="report.incomplete_students.total"
                :page-size="pageSize"
                :current-page="incompletePage"
                @current-change="handleIncompletePageChange"
                size="small"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>

    <!-- 无数据 -->
    <div v-else class="loading-state">暂无数据</div>
  </el-drawer>
</template>

<style scoped>
.loading-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
}

.detail-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border-light);
}

.detail-header h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-lg);
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-lg);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
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

.text-expired {
  color: #ef4444;
  font-weight: 600;
}

.detail-stats {
  padding: var(--space-md);
  background: var(--color-bg-alt);
  border-radius: var(--radius-sm);
}

.stat-row {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-bottom: var(--space-sm);
}

.stat-num {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--color-primary);
}

.stat-sep {
  font-size: 1.2rem;
  color: var(--color-text-muted);
}

.stat-total {
  font-size: 1.2rem;
  color: var(--color-text-secondary);
  margin-right: var(--space-sm);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  padding-left: var(--space-sm);
  border-left: 3px solid var(--color-primary);
}

.students-section {
  padding-bottom: var(--space-sm);
}

.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.score-cell {
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 6px;
  display: inline-block;
}

.score-excellent {
  color: #10b981;
  background: rgba(16, 185, 129, 0.12);
}

.score-good {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.12);
}

.score-pass {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
}

.score-fail {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.12);
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: var(--space-md) 0 var(--space-sm);
}
</style>

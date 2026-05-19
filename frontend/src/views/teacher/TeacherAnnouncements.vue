<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAnnouncements, createAnnouncement, deleteAnnouncement as apiDeleteAnnouncement,
  getCompletionReport,
  type Announcement, type CompletionReport,
} from '@/api/announcement'
import { getClasses, type ClassInfo } from '@/api/class'
import { getQuestions, type Question } from '@/api/question'

const announcements = ref<Announcement[]>([])
const classes = ref<ClassInfo[]>([])
const loading = ref(true)

const dialogVisible = ref(false)
const form = reactive({
  class_id: 0,
  type: 'announcement' as 'announcement' | 'quiz',
  title: '',
  content: '',
  question_ids: [] as number[],
  start_time: '',
  end_time: '',
})

const questions = ref<Question[]>([])
const questionLoading = ref(false)

const reportDialogVisible = ref(false)
const reportData = ref<CompletionReport | null>(null)
const reportLoading = ref(false)

onMounted(async () => {
  try {
    const [a, c] = await Promise.all([getAnnouncements(), getClasses()])
    announcements.value = a
    classes.value = c
  } finally {
    loading.value = false
  }
})

function openCreate() {
  Object.assign(form, {
    class_id: classes.value[0]?.id || 0,
    type: 'announcement',
    title: '',
    content: '',
    question_ids: [],
    start_time: '',
    end_time: '',
  })
  questions.value = []
  dialogVisible.value = true
}

async function loadQuestions() {
  if (questions.value.length > 0) return
  questionLoading.value = true
  try {
    questions.value = await getQuestions()
  } finally {
    questionLoading.value = false
  }
}

function handleTypeChange() {
  if (form.type === 'quiz') {
    loadQuestions()
  }
}

async function handleCreate() {
  if (!form.title.trim()) { ElMessage.warning('请填写标题'); return }
  if (!form.class_id) { ElMessage.warning('请选择班级'); return }

  try {
    await createAnnouncement({
      class_id: form.class_id,
      type: form.type,
      title: form.title.trim(),
      content: form.type === 'announcement' ? form.content.trim() : undefined,
      question_ids: form.type === 'quiz' ? form.question_ids : undefined,
      start_time: form.start_time || undefined,
      end_time: form.end_time || undefined,
    })
    ElMessage.success('发布成功')
    dialogVisible.value = false
    announcements.value = await getAnnouncements()
  } catch {
    ElMessage.error('发布失败')
  }
}

async function handleDelete(item: Announcement) {
  try {
    await ElMessageBox.confirm('确定删除该公告？', '提示', { type: 'warning' })
    await apiDeleteAnnouncement(item.id)
    announcements.value = announcements.value.filter(a => a.id !== item.id)
    ElMessage.success('已删除')
  } catch {}
}

async function openReport(item: Announcement) {
  reportDialogVisible.value = true
  reportLoading.value = true
  try {
    reportData.value = await getCompletionReport(item.id)
  } finally {
    reportLoading.value = false
  }
}

function getClassName(classId: number) {
  return classes.value.find(c => c.id === classId)?.name || '未知班级'
}
</script>

<template>
  <div class="announcements-page">
    <div class="page-header">
      <h1>任务发布</h1>
      <el-button type="primary" round @click="openCreate">发布公告</el-button>
    </div>

    <el-table :data="announcements" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column label="目标班级" width="140">
        <template #default="{ row }">{{ getClassName(row.class_id) }}</template>
      </el-table-column>
      <el-table-column label="类型" width="80">
        <template #default="{ row }">
          <el-tag :type="row.type === 'announcement' ? '' : 'success'" size="small" effect="plain">
            {{ row.type === 'announcement' ? '公告' : '题目' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="发布时间" width="140" />
      <el-table-column label="时间限制" width="180">
        <template #default="{ row }">
          <span v-if="row.end_time" class="time-limit">{{ row.start_time || '' }} ~ {{ row.end_time }}</span>
          <span v-else class="no-limit">不限时</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openReport(row)">完成情况</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && announcements.length === 0" class="empty-state">
      <p>暂无公告，点击「发布公告」开始发布</p>
    </div>

    <!-- Create dialog -->
    <el-dialog v-model="dialogVisible" title="发布公告 / 任务" width="600px">
      <div class="form-group">
        <label>目标班级</label>
        <el-select v-model="form.class_id" placeholder="选择班级" size="large" style="width: 100%">
          <el-option v-for="c in classes" :key="c.id" :label="`${c.major} · ${c.name}`" :value="c.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>类型</label>
        <el-radio-group v-model="form.type" size="large" @change="handleTypeChange">
          <el-radio-button value="announcement">普通公告</el-radio-button>
          <el-radio-button value="quiz">发布题目</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>标题</label>
        <el-input v-model="form.title" placeholder="公告标题" size="large" />
      </div>

      <template v-if="form.type === 'announcement'">
        <div class="form-group">
          <label>公告内容</label>
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="输入公告内容" />
        </div>
      </template>

      <template v-if="form.type === 'quiz'">
        <div class="form-group">
          <label>选择题目</label>
          <div v-loading="questionLoading" class="question-selector">
            <el-checkbox-group v-model="form.question_ids">
              <div v-for="q in questions" :key="q.id" class="question-item">
                <el-checkbox :value="q.id">
                  <span class="q-stem">{{ q.stem.length > 40 ? q.stem.slice(0, 40) + '...' : q.stem }}</span>
                  <el-tag size="small" effect="plain" style="margin-left: 8px;">
                    {{ q.type === 'choice' ? '选择' : '填空' }}
                  </el-tag>
                </el-checkbox>
              </div>
            </el-checkbox-group>
            <div v-if="!questionLoading && questions.length === 0" class="empty-mini">题库为空</div>
          </div>
          <span class="hint">已选 {{ form.question_ids.length }} 题</span>
        </div>
      </template>

      <div class="form-row">
        <div class="form-group" style="flex: 1">
          <label>开始时间（可选）</label>
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="不限" size="large" style="width: 100%" value-format="YYYY-MM-DD HH:mm:ss" />
        </div>
        <div class="form-group" style="flex: 1">
          <label>截止时间（可选）</label>
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="不限" size="large" style="width: 100%" value-format="YYYY-MM-DD HH:mm:ss" />
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">发布</el-button>
      </template>
    </el-dialog>

    <!-- Completion report dialog -->
    <el-dialog v-model="reportDialogVisible" title="任务完成情况" width="520px">
      <div v-loading="reportLoading">
        <template v-if="reportData">
          <div class="report-summary">
            <div class="report-stat">
              <span class="stat-value">{{ reportData.completed_students }}</span>
              <span class="stat-label">已完成</span>
            </div>
            <div class="report-stat">
              <span class="stat-value warn">{{ reportData.total_students - reportData.completed_students }}</span>
              <span class="stat-label">未完成</span>
            </div>
            <div class="report-stat">
              <span class="stat-value">{{ reportData.total_students }}</span>
              <span class="stat-label">总人数</span>
            </div>
          </div>
          <el-progress
            :percentage="reportData.total_students > 0 ? Math.round(reportData.completed_students / reportData.total_students * 100) : 0"
            :stroke-width="10"
            color="var(--color-primary)"
          />
          <div v-if="reportData.incomplete_students.length > 0" class="incomplete-list">
            <h4>未完成学生名单</h4>
            <div v-for="s in reportData.incomplete_students" :key="s.id" class="incomplete-item">
              <span>{{ s.id }}</span>
              <span>{{ s.name }}</span>
            </div>
          </div>
          <div v-else class="all-done">所有学生已完成</div>
          <div v-if="reportData.is_expired" class="expired-tag">
            <el-tag type="warning" size="small">已过截止时间</el-tag>
          </div>
        </template>
      </div>
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

.form-row {
  display: flex;
  gap: var(--space-lg);
}

.time-limit {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.no-limit {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.hint {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: var(--space-xs);
  display: block;
}

.question-selector {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-sm);
}

.question-item {
  padding: var(--space-xs) var(--space-sm);
  border-bottom: 1px solid var(--color-border-light);
}

.question-item:last-child {
  border-bottom: none;
}

.q-stem {
  font-size: 0.85rem;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.empty-mini {
  text-align: center;
  padding: var(--space-lg);
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.report-summary {
  display: flex;
  gap: var(--space-xl);
  margin-bottom: var(--space-lg);
}

.report-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary);
}

.stat-value.warn {
  color: #ef4444;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.incomplete-list {
  margin-top: var(--space-lg);
}

.incomplete-list h4 {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: var(--space-sm);
  color: var(--color-text);
}

.incomplete-item {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-xs) 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-light);
}

.all-done {
  text-align: center;
  padding: var(--space-lg);
  color: #10b981;
  font-weight: 600;
}

.expired-tag {
  margin-top: var(--space-md);
}
</style>

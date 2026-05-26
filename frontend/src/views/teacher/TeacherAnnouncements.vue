<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAnnouncements, createAnnouncement, deleteAnnouncement as apiDeleteAnnouncement,
  getCompletionReport,
  type Announcement, type CompletionReport,
} from '@/api/announcement'
import { getClasses, type ClassInfo } from '@/api/class'
import http from '@/api/http'

// 本地扩展题目类型（兼容后端返回的 course_name / chapter_name 字段）
interface PickerQuestion {
  id: number
  type: 'choice' | 'fill'
  stem: string
  chapter_id?: number
  chapter_name?: string
  course_id?: number
  course_name?: string
}

interface CourseOption {
  id: number
  name: string
}

interface ChapterOption {
  id: number
  name: string
}

// ---- 公告列表 ----
const announcements = ref<Announcement[]>([])
const classes = ref<ClassInfo[]>([])
const loading = ref(true)

// ---- 发布表单 ----
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

// ---- 选题对话框状态 ----
const pickerVisible = ref(false)
const pickerLoading = ref(false)
const pickerCourses = ref<CourseOption[]>([])
const pickerChapters = ref<ChapterOption[]>([])
const pickerQuestions = ref<PickerQuestion[]>([])
const pickerFilterCourse = ref<number | ''>('')
const pickerFilterChapter = ref<number | ''>('')
const pickerFilterType = ref<string>('')
// 跨筛选保留的已选题目 ID 列表
const pickerSelectedIds = ref<number[]>([])
const pickerTableRef = ref<any>(null)
// 防止 restorePickerSelection 时 selection-change 回写
const isRestoringSelection = ref(false)

// ---- 完成情况报告 ----
const reportDialogVisible = ref(false)
const reportData = ref<CompletionReport | null>(null)
const reportLoading = ref(false)

onMounted(async () => {
  try {
    const [a, c] = await Promise.all([getAnnouncements(), getClasses()])
    announcements.value = a
    classes.value = c
  } catch {
    ElMessage.error('任务数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})

// ---- 发布表单 ----
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
  dialogVisible.value = true
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
    await ElMessageBox.confirm('确定删除该任务？删除后学生将无法继续查看或完成该任务。', '提示', { type: 'warning' })
    await apiDeleteAnnouncement(item.id)
    announcements.value = announcements.value.filter(a => a.id !== item.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

// ---- 选题对话框逻辑 ----
async function loadPickerCourses() {
  try {
    const data = await http.get<any, CourseOption[]>('/questions/courses')
    pickerCourses.value = Array.isArray(data) ? data : []
  } catch {
    pickerCourses.value = []
  }
}

async function loadPickerQuestions() {
  pickerLoading.value = true
  try {
    const params: Record<string, any> = {}
    if (pickerFilterCourse.value !== '') params.course_id = pickerFilterCourse.value
    if (pickerFilterChapter.value !== '') params.chapter_id = pickerFilterChapter.value
    if (pickerFilterType.value) params.type = pickerFilterType.value
    const data = await http.get<any, PickerQuestion[]>('/questions', { params })
    pickerQuestions.value = Array.isArray(data) ? data : []
    // 数据加载完毕后恢复已选状态
    await nextTick()
    restorePickerSelection()
  } catch {
    ElMessage.error('题目加载失败，请稍后重试')
    pickerQuestions.value = []
  } finally {
    pickerLoading.value = false
  }
}

/** 将 pickerSelectedIds 中在当前视图里的行重新打勾 */
function restorePickerSelection() {
  if (!pickerTableRef.value) return
  isRestoringSelection.value = true
  pickerQuestions.value.forEach(row => {
    if (pickerSelectedIds.value.includes(row.id)) {
      pickerTableRef.value.toggleRowSelection(row, true)
    }
  })
  nextTick(() => {
    isRestoringSelection.value = false
  })
}

/** 打开选题对话框 */
async function openPicker() {
  // 重置筛选
  pickerFilterCourse.value = ''
  pickerFilterChapter.value = ''
  pickerFilterType.value = ''
  pickerChapters.value = []
  // 从表单中恢复初始已选
  pickerSelectedIds.value = [...form.question_ids]
  pickerVisible.value = true
  // 并行加载课程列表与题目列表
  await Promise.all([loadPickerCourses(), loadPickerQuestions()])
}

/** 课程切换：联动清空章节、重新加载题目并提取章节选项 */
async function handlePickerCourseChange() {
  pickerFilterChapter.value = ''
  pickerChapters.value = []
  await loadPickerQuestions()
  // 从已加载题目中提取章节（仅当选了具体课程时才有意义）
  if (pickerFilterCourse.value !== '') {
    const chapMap = new Map<number, string>()
    pickerQuestions.value.forEach(q => {
      if (q.chapter_id != null && q.chapter_name) {
        chapMap.set(q.chapter_id, q.chapter_name)
      }
    })
    pickerChapters.value = Array.from(chapMap.entries()).map(([id, name]) => ({ id, name }))
  }
}

/** 章节切换：重新加载题目 */
async function handlePickerChapterChange() {
  await loadPickerQuestions()
}

/** 题型切换：重新加载题目 */
async function handlePickerTypeChange() {
  await loadPickerQuestions()
}

/**
 * 表格勾选变化时，跨筛选保留已选状态：
 * 移除当前视图中所有 ID，再加回此次被选中的 ID
 */
function handlePickerSelectionChange(rows: PickerQuestion[]) {
  if (isRestoringSelection.value) return
  const currentIds = pickerQuestions.value.map(q => q.id)
  const selectedIds = rows.map(r => r.id)
  pickerSelectedIds.value = [
    ...pickerSelectedIds.value.filter(id => !currentIds.includes(id)),
    ...selectedIds,
  ]
}

/** 确定选题：写入表单并关闭对话框 */
function confirmPicker() {
  form.question_ids = [...pickerSelectedIds.value]
  pickerVisible.value = false
}

/** 取消选题：不保存，关闭对话框 */
function cancelPicker() {
  pickerVisible.value = false
}

// ---- 完成情况报告 ----
async function openReport(item: Announcement) {
  reportDialogVisible.value = true
  reportLoading.value = true
  try {
    reportData.value = await getCompletionReport(item.id)
  } catch {
    ElMessage.error('完成情况加载失败，请稍后重试')
  } finally {
    reportLoading.value = false
  }
}

// ---- 辅助函数 ----
function getClassName(classId: number) {
  return classes.value.find(c => c.id === classId)?.name || '未知班级'
}

function getTypeLabel(type: string) {
  const map: Record<string, string> = { choice: '选择题', fill: '填空题' }
  return map[type] || type
}
</script>

<template>
  <div class="announcements-page">
    <div class="page-header">
      <h1>任务发布</h1>
      <el-button type="primary" round @click="openCreate">发布任务</el-button>
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
      <p>暂无任务，点击「发布任务」创建课程通知或学习任务。</p>
    </div>

    <!-- 发布公告/任务 对话框 -->
    <el-dialog v-model="dialogVisible" title="发布公告 / 任务" width="600px">
      <div class="form-group">
        <label>目标班级</label>
        <el-select v-model="form.class_id" placeholder="选择班级" size="large" style="width: 100%">
          <el-option v-for="c in classes" :key="c.id" :label="`${c.major} · ${c.name}`" :value="c.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>类型</label>
        <el-radio-group v-model="form.type" size="large">
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

      <!-- 题目选择区：替换旧 checkbox 列表，改为按钮触发选题对话框 -->
      <template v-if="form.type === 'quiz'">
        <div class="form-group">
          <label>选择题目</label>
          <div class="question-picker-row">
            <span class="selected-count">已选 <strong>{{ form.question_ids.length }}</strong> 道题</span>
            <el-button type="primary" plain size="small" @click="openPicker">选择题目</el-button>
          </div>
          <div v-if="form.question_ids.length > 0" class="selected-hint">
            已选题目 ID：{{ form.question_ids.join('、') }}
          </div>
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

    <!-- 选题对话框 -->
    <el-dialog
      v-model="pickerVisible"
      title="从题库选题"
      width="860px"
      :close-on-click-modal="false"
      append-to-body
    >
      <!-- 筛选行 -->
      <div class="picker-filters">
        <div class="filter-item">
          <span class="filter-label">课程：</span>
          <el-select
            v-model="pickerFilterCourse"
            placeholder="全部课程"
            clearable
            style="width: 180px"
            @change="handlePickerCourseChange"
          >
            <el-option v-for="c in pickerCourses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">章节：</span>
          <el-select
            v-model="pickerFilterChapter"
            placeholder="全部章节"
            clearable
            :disabled="pickerFilterCourse === ''"
            style="width: 180px"
            @change="handlePickerChapterChange"
          >
            <el-option v-for="ch in pickerChapters" :key="ch.id" :label="ch.name" :value="ch.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">题型：</span>
          <el-select
            v-model="pickerFilterType"
            placeholder="全部题型"
            clearable
            style="width: 140px"
            @change="handlePickerTypeChange"
          >
            <el-option label="选择题" value="choice" />
            <el-option label="填空题" value="fill" />
          </el-select>
        </div>
      </div>

      <!-- 题目表格 -->
      <div class="picker-table-wrap" v-loading="pickerLoading">
        <el-table
          ref="pickerTableRef"
          :data="pickerQuestions"
          style="width: 100%"
          row-key="id"
          @selection-change="handlePickerSelectionChange"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column label="题型" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.type === 'choice' ? '' : 'warning'" effect="plain">
                {{ getTypeLabel(row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="题干" min-width="260">
            <template #default="{ row }">
              <span class="stem-text">{{ row.stem.length > 50 ? row.stem.slice(0, 50) + '…' : row.stem }}</span>
            </template>
          </el-table-column>
          <el-table-column label="所属课程" width="140">
            <template #default="{ row }">{{ row.course_name || '—' }}</template>
          </el-table-column>
          <el-table-column label="所属章节" width="140">
            <template #default="{ row }">{{ row.chapter_name || '—' }}</template>
          </el-table-column>
        </el-table>
        <div v-if="!pickerLoading && pickerQuestions.length === 0" class="picker-empty">
          暂无符合条件的题目，请调整筛选条件
        </div>
      </div>

      <template #footer>
        <div class="picker-footer">
          <span class="picker-count">已选 <strong>{{ pickerSelectedIds.length }}</strong> 道题</span>
          <div>
            <el-button @click="cancelPicker">取消</el-button>
            <el-button type="primary" @click="confirmPicker">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 完成情况对话框 -->
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

/* 选题触发行 */
.question-picker-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selected-count {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.selected-hint {
  margin-top: 6px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  word-break: break-all;
}

/* 选题对话框 */
.picker-filters {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light, #f0f0f0);
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.picker-table-wrap {
  height: 400px;
  overflow-y: auto;
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-sm, 6px);
}

.picker-empty {
  text-align: center;
  padding: 48px 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.stem-text {
  font-size: 0.85rem;
  line-height: 1.4;
}

.picker-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.picker-count {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

/* 完成情况报告 */
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

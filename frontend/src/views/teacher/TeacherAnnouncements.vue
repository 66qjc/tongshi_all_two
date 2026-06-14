<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TableInstance } from 'element-plus'
import { createAnnouncement, deleteAnnouncement, getAnnouncements, type Announcement } from '@/api/announcement'
import { getClasses, type ClassInfo } from '@/api/class'
import { getCourses, type Course } from '@/api/course'
import { getCourseQuestions, type Question } from '@/api/question'
import {
  appendSelectedQuestionIds,
  removeSelectedQuestionId,
  syncVisibleSelectedQuestionIds,
} from './questionSelection'

const router = useRouter()
const announcements = ref<Announcement[]>([])
const courses = ref<Course[]>([])
const ownedCourses = computed(() => courses.value.filter(course => course.is_owner))
const classes = ref<ClassInfo[]>([])
const questions = ref<Question[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const questionDialogVisible = ref(false)
const questionLoading = ref(false)
const questionKeyword = ref('')
const questionTypeFilter = ref<'' | 'choice' | 'fill' | 'multi_choice'>('')
const questionTagFilter = ref('')
const questionAddCount = ref<number | null>(null)
const draftSelectedQuestionIds = ref<number[]>([])
const questionTableRef = ref<TableInstance>()
let questionRequestSeq = 0
let syncingQuestionSelection = false

const form = reactive({
  course_id: '' as number | '',
  class_ids: [] as number[],
  title: '',
  question_ids: [] as number[],
  start_time: '',
  end_time: '',
})

/** 格式化当前时间为 YYYY-MM-DD HH:mm:ss */
function nowString() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const targetClasses = computed(() => {
  if (typeof form.course_id !== 'number') return []
  return classes.value.filter(item => item.course_id === form.course_id)
})

const filteredQuestions = computed(() => {
  const keyword = questionKeyword.value.trim().toLowerCase()
  return questions.value.filter(item => {
    const matchType = !questionTypeFilter.value || item.type === questionTypeFilter.value
    const matchTag = !questionTagFilter.value || (item.tags || []).includes(questionTagFilter.value)
    const searchable = `${item.stem || ''} ${item.answer || ''} ${item.explanation || ''}`.toLowerCase()
    const matchKeyword = !keyword || searchable.includes(keyword)
    return matchType && matchTag && matchKeyword
  })
})

const questionTags = computed(() => {
  const tags = new Set<string>()
  questions.value.forEach(item => {
    ;(item.tags || []).forEach(tag => {
      if (tag) tags.add(tag)
    })
  })
  return Array.from(tags)
})

const selectedQuestions = computed(() => {
  const questionMap = new Map(questions.value.map(item => [item.id, item]))
  return draftSelectedQuestionIds.value
    .map(id => questionMap.get(id))
    .filter((item): item is Question => Boolean(item))
})

async function syncQuestionTableSelection() {
  await nextTick()
  const table = questionTableRef.value
  if (!table) return

  syncingQuestionSelection = true
  const selectedIds = new Set(draftSelectedQuestionIds.value)
  filteredQuestions.value.forEach(row => {
    table.toggleRowSelection(row, selectedIds.has(row.id))
  })
  await nextTick()
  syncingQuestionSelection = false
}

function getQuestionTypeLabel(type: Question['type']) {
  if (type === 'choice') return '选择题'
  if (type === 'multi_choice') return '多选题'
  return '填空题'
}

function getQuestionPreview(stem: string, length = 52) {
  return stem.length > length ? `${stem.slice(0, length)}...` : stem
}

async function loadBase() {
  const [list, courseList, classList] = await Promise.all([getAnnouncements(), getCourses(), getClasses()])
  announcements.value = list
  courses.value = courseList
  classes.value = classList
}

async function loadQuestions() {
  const requestSeq = ++questionRequestSeq
  const courseId = form.course_id
  if (typeof courseId !== 'number') {
    questions.value = []
    questionLoading.value = false
    return
  }
  questionLoading.value = true
  try {
    const result = await getCourseQuestions(courseId)
    if (requestSeq === questionRequestSeq && form.course_id === courseId) {
      questions.value = result
      if (questionDialogVisible.value) {
        void syncQuestionTableSelection()
      }
    }
  } catch {
    if (requestSeq === questionRequestSeq && form.course_id === courseId) {
      ElMessage.error('题目加载失败')
    }
  } finally {
    if (requestSeq === questionRequestSeq && form.course_id === courseId) {
      questionLoading.value = false
    }
  }
}

function openCreate() {
  Object.assign(form, {
    course_id: ownedCourses.value[0]?.id || '',
    class_ids: [],
    title: '',
    question_ids: [],
    start_time: nowString(),
    end_time: '',
  })
  dialogVisible.value = true
  loadQuestions()
}

async function openQuestionPicker() {
  if (typeof form.course_id !== 'number') {
    ElMessage.warning('请先选择课程')
    return
  }
  questionKeyword.value = ''
  questionTypeFilter.value = ''
  questionTagFilter.value = ''
  questionAddCount.value = null
  draftSelectedQuestionIds.value = [...form.question_ids]
  questionDialogVisible.value = true
  await loadQuestions()
  await syncQuestionTableSelection()
}

function handleQuestionSelection(rows: Question[]) {
  if (syncingQuestionSelection) return
  draftSelectedQuestionIds.value = syncVisibleSelectedQuestionIds(draftSelectedQuestionIds.value, filteredQuestions.value, rows)
}

function addTopFilteredQuestions() {
  const count = Number(questionAddCount.value)
  if (!Number.isInteger(count) || count < 1) {
    ElMessage.warning('请输入加入数量')
    return
  }
  const existing = new Set(draftSelectedQuestionIds.value)
  const availableIds = filteredQuestions.value
    .map(item => item.id)
    .filter(id => !existing.has(id))
  if (availableIds.length === 0) {
    ElMessage.warning('当前筛选结果没有可加入的题目')
    return
  }
  const addedIds = availableIds.slice(0, count)
  draftSelectedQuestionIds.value = appendSelectedQuestionIds(draftSelectedQuestionIds.value, addedIds)
  void syncQuestionTableSelection()
  ElMessage.success(`已加入 ${addedIds.length} 道题`)
}

function removeDraftQuestion(id: number) {
  draftSelectedQuestionIds.value = removeSelectedQuestionId(draftSelectedQuestionIds.value, id)
  void syncQuestionTableSelection()
}

function clearDraftQuestions() {
  draftSelectedQuestionIds.value = []
  void syncQuestionTableSelection()
}

function resetQuestionFilters() {
  questionKeyword.value = ''
  questionTypeFilter.value = ''
  questionTagFilter.value = ''
  questionAddCount.value = null
}

function confirmQuestions() {
  form.question_ids = [...draftSelectedQuestionIds.value]
  questionDialogVisible.value = false
}

async function handleCreate() {
  if (typeof form.course_id !== 'number') {
    ElMessage.warning('请选择所属课程')
    return
  }
  if (form.class_ids.length === 0) {
    ElMessage.warning('请选择目标班级')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (form.question_ids.length === 0) {
    ElMessage.warning('请选择题目')
    return
  }
  if (form.start_time && form.end_time && form.start_time >= form.end_time) {
    ElMessage.warning('截止时间必须晚于开始时间')
    return
  }

  try {
    await createAnnouncement({
      course_id: form.course_id,
      class_ids: form.class_ids,
      title: form.title.trim(),
      question_ids: form.question_ids,
      start_time: form.start_time || undefined,
      end_time: form.end_time || undefined,
    })
    ElMessage.success('发布成功')
    dialogVisible.value = false
    announcements.value = await getAnnouncements()
  } catch {
    ElMessage.error('发布失败，请确认班级和题目属于同一课程')
  }
}

async function handleDelete(row: Announcement) {
  try {
    await ElMessageBox.confirm('确定删除该发布题目？删除后学生将无法继续查看或完成。', '删除确认', { type: 'warning' })
    await deleteAnnouncement(row.id)
    announcements.value = announcements.value.filter(item => item.id !== row.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('删除失败，请稍后重试')
  }
}

function isExpired(row: Announcement) {
  if (!row.end_time) return false
  return new Date(row.end_time) < new Date()
}

function openReport(row: Announcement) {
  router.push({ path: '/teacher/task-report', query: { task_id: row.id } })
}

watch(() => form.course_id, () => {
  form.class_ids = []
  form.question_ids = []
  draftSelectedQuestionIds.value = []
  resetQuestionFilters()
  loadQuestions()
})

watch(filteredQuestions, () => {
  if (questionDialogVisible.value) {
    void syncQuestionTableSelection()
  }
})

onMounted(async () => {
  try {
    await loadBase()
  } catch {
    ElMessage.error('发布题目数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="publish-page">
    <div class="page-header">
      <h1>发布作业</h1>
      <el-button type="primary" round @click="openCreate">发布作业</el-button>
    </div>

    <el-table :data="announcements" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column prop="course_name" label="所属课程" min-width="160" />
      <el-table-column label="目标班级" min-width="220">
        <template #default="{ row }">
          {{ row.class_names?.join('、') || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="题目数" width="90" align="center">
        <template #default="{ row }">{{ row.question_ids?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="开始时间" width="160">
        <template #default="{ row }">{{ row.start_time ? row.start_time.slice(0, 16).replace('T', ' ') : '-' }}</template>
      </el-table-column>
      <el-table-column label="截止时间" width="160">
        <template #default="{ row }">
          <span v-if="row.end_time" :style="{ color: isExpired(row) ? '#ef4444' : '' }">
            {{ row.end_time.slice(0, 16).replace('T', ' ') }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openReport(row)">查看情况</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && announcements.length === 0" class="empty-state">
      暂无发布记录
    </div>

    <el-dialog v-model="dialogVisible" title="发布作业" width="600px">
      <div class="form-group">
        <label>所属课程</label>
        <el-select v-model="form.course_id" placeholder="选择课程" size="large" style="width: 100%">
          <el-option v-for="course in ownedCourses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>目标班级</label>
        <el-select v-model="form.class_ids" multiple placeholder="选择班级" size="large" style="width: 100%">
          <el-option v-for="item in targetClasses" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>标题</label>
        <el-input v-model="form.title" placeholder="输入发布标题" size="large" />
      </div>
      <div class="form-group">
        <label>题目</label>
        <div class="question-row">
          <span>已选 {{ form.question_ids.length }} 道题</span>
          <el-button plain type="primary" @click="openQuestionPicker">选择题目</el-button>
        </div>
      </div>
      <div class="time-row">
        <div class="form-group">
          <label>开始时间</label>
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="不限" size="large" style="width: 100%" value-format="YYYY-MM-DD HH:mm:ss" clearable />
        </div>
        <div class="form-group">
          <label>截止时间</label>
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="不限" size="large" style="width: 100%" value-format="YYYY-MM-DD HH:mm:ss" clearable />
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">发布</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="questionDialogVisible" title="选择题目" width="min(980px, calc(100vw - 32px))" append-to-body class="question-picker-dialog">
      <div class="question-picker">
        <div class="question-library">
          <div class="question-filter-bar">
            <el-input
              v-model="questionKeyword"
              placeholder="搜索题干、答案或解析"
              clearable
              size="large"
            />
            <el-select v-model="questionTypeFilter" placeholder="全部题型" clearable size="large" style="width: 140px">
              <el-option label="选择题" value="choice" />
              <el-option label="多选题" value="multi_choice" />
              <el-option label="填空题" value="fill" />
            </el-select>
            <el-select v-model="questionTagFilter" placeholder="全部标签" clearable size="large" style="width: 150px">
              <el-option v-for="tag in questionTags" :key="tag" :label="tag" :value="tag" />
            </el-select>
            <el-button size="large" @click="resetQuestionFilters">重置</el-button>
          </div>

          <div class="question-batch-row">
            <el-input-number
              v-model="questionAddCount"
              :min="1"
              :max="Math.max(filteredQuestions.length, 1)"
              :controls="false"
              placeholder="数量"
              size="large"
              class="question-count-input"
            />
            <el-button plain type="primary" size="large" @click="addTopFilteredQuestions">加入前 N 题</el-button>
            <span class="question-result-count">筛选结果 {{ filteredQuestions.length }} 题</span>
          </div>
          <p class="question-picker-tip">加入或勾选题目后，请点击底部“确定”，题目才会带入本次发布。</p>

          <el-table
            ref="questionTableRef"
            :data="filteredQuestions"
            row-key="id"
            height="420"
            style="width: 100%"
            v-loading="questionLoading"
            :empty-text="questions.length === 0 ? '当前课程暂无题目，请先到题库管理中新增或导入题目。' : '没有符合条件的题目，请调整关键词或题型。'"
            @selection-change="handleQuestionSelection"
          >
            <el-table-column type="selection" width="50" reserve-selection />
            <el-table-column label="题干" min-width="280">
              <template #default="{ row }">{{ getQuestionPreview(row.stem) }}</template>
            </el-table-column>
            <el-table-column label="题型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.type === 'choice' ? '' : row.type === 'multi_choice' ? 'warning' : 'success'" size="small" effect="plain">
                  {{ getQuestionTypeLabel(row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="标签" min-width="130">
              <template #default="{ row }">
                <div class="question-tag-list">
                  <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                  <span v-if="!row.tags?.length" class="question-muted">-</span>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <aside class="selected-question-panel">
          <div class="selected-question-header">
            <strong>已选题目（{{ draftSelectedQuestionIds.length }}）</strong>
            <el-button text size="small" :disabled="draftSelectedQuestionIds.length === 0" @click="clearDraftQuestions">清空</el-button>
          </div>
          <div v-if="selectedQuestions.length === 0" class="selected-question-empty">
            尚未选择题目，可以从左侧题库加入。
          </div>
          <div v-else class="selected-question-list">
            <div v-for="item in selectedQuestions" :key="item.id" class="selected-question-item">
              <div class="selected-question-main">
                <el-tag :type="item.type === 'choice' ? '' : item.type === 'multi_choice' ? 'warning' : 'success'" size="small" effect="plain">
                  {{ getQuestionTypeLabel(item.type) }}
                </el-tag>
                <el-tag v-for="tag in item.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                <span>{{ getQuestionPreview(item.stem, 34) }}</span>
              </div>
              <el-button type="danger" text size="small" @click="removeDraftQuestion(item.id)">移除</el-button>
            </div>
          </div>
        </aside>
      </div>
      <template #footer>
        <el-button @click="questionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmQuestions">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header,
.question-row,
.time-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.page-header {
  justify-content: space-between;
  margin-bottom: var(--space-lg);
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
}

.empty-state {
  padding: var(--space-3xl) 0;
  text-align: center;
  color: var(--color-text-muted);
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

.question-row {
  justify-content: space-between;
  color: var(--color-text-muted);
}

.time-row > .form-group {
  flex: 1;
}

.question-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: var(--space-lg);
  align-items: stretch;
}

.question-library {
  min-width: 0;
}

.question-filter-bar,
.question-batch-row,
.selected-question-header,
.selected-question-main {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.question-filter-bar,
.question-batch-row {
  margin-bottom: var(--space-md);
}

.question-count-input {
  width: 96px;
}

.question-result-count {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: 0.85rem;
  white-space: nowrap;
}

.question-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.question-muted {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.question-picker-tip {
  margin: calc(var(--space-sm) * -1) 0 var(--space-md);
  color: var(--color-text-muted);
  font-size: 0.82rem;
  line-height: 1.5;
}

.selected-question-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  min-height: 520px;
  background: var(--color-bg-alt);
}

.selected-question-header {
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.selected-question-empty {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  line-height: 1.6;
  padding: var(--space-xl) var(--space-sm);
  text-align: center;
}

.selected-question-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  max-height: 460px;
  overflow-y: auto;
}

.selected-question-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: var(--space-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
}

.selected-question-main {
  align-items: flex-start;
  min-width: 0;
  color: var(--color-text);
  font-size: 0.86rem;
  line-height: 1.5;
}

.selected-question-main span:last-child {
  min-width: 0;
  word-break: break-word;
}

@media (max-width: 900px) {
  .question-picker {
    grid-template-columns: 1fr;
  }

  .selected-question-panel {
    min-height: auto;
  }

  .question-filter-bar,
  .question-batch-row {
    flex-wrap: wrap;
  }

  .question-result-count {
    margin-left: 0;
  }
}
</style>

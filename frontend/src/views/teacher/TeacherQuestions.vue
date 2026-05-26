<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getChapters, type Chapter } from '@/api/chapter'
import {
  getQuestions, getCourses, createQuestion, updateQuestion,
  deleteQuestion as apiDeleteQuestion, importQuestions,
  type Question, type Course,
} from '@/api/question'

// ────────────── 数据状态 ──────────────
const courses = ref<Course[]>([])
const chapters = ref<Chapter[]>([])
const questions = ref<Question[]>([])
const loading = ref(true)

// ────────────── 筛选条件 ──────────────
const filterCourse = ref<number | ''>('')
const filterChapter = ref<number | ''>('')
const filterType = ref<'' | 'choice' | 'fill'>('')

// 筛选栏：根据所选课程过滤章节下拉
const filterChapterOptions = computed(() => {
  if (!filterCourse.value) return chapters.value
  return chapters.value.filter(c => c.course_id === filterCourse.value)
})

// ────────────── 表单状态 ──────────────
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formCourse = ref<number | ''>('')

const newQuestion = reactive({
  chapter: '' as number | '',
  type: 'choice' as 'choice' | 'fill',
  stem: '',
  options: ['', '', '', ''],
  answer: '',
  explanation: '',
})

// 表单中：根据所选课程过滤章节下拉
const formChapterOptions = computed(() => {
  if (!formCourse.value) return []
  return chapters.value.filter(c => c.course_id === formCourse.value)
})

// ────────────── 数据加载 ──────────────
async function fetchCourses() {
  try {
    courses.value = await getCourses()
  } catch {
    ElMessage.error('课程列表加载失败')
  }
}

async function fetchChapters() {
  try {
    chapters.value = await getChapters()
  } catch {
    ElMessage.error('章节列表加载失败')
  }
}

async function fetchQuestions() {
  loading.value = true
  try {
    const params: { chapter_id?: number; type?: string; course_id?: number } = {}
    if (filterCourse.value) params.course_id = filterCourse.value as number
    if (filterChapter.value) params.chapter_id = filterChapter.value as number
    if (filterType.value) params.type = filterType.value
    questions.value = await getQuestions(params)
  } catch {
    ElMessage.error('题目加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchCourses(), fetchChapters()])
  await fetchQuestions()
})

// ────────────── 筛选处理 ──────────────
// 课程变化时，联动重置章节筛选
function handleFilterCourseChange() {
  filterChapter.value = ''
  fetchQuestions()
}

function handleFilterChange() {
  fetchQuestions()
}

function resetFilter() {
  filterCourse.value = ''
  filterChapter.value = ''
  filterType.value = ''
  fetchQuestions()
}

// ────────────── 表单处理 ──────────────
// 表单中课程变化时，联动重置章节选择
function handleFormCourseChange() {
  newQuestion.chapter = ''
}

function openNew() {
  editingId.value = null
  formCourse.value = ''
  Object.assign(newQuestion, {
    chapter: '',
    type: 'choice',
    stem: '',
    options: ['', '', '', ''],
    answer: '',
    explanation: '',
  })
  dialogVisible.value = true
}

function openEdit(q: Question) {
  editingId.value = q.id
  // 先设置课程（不触发 formCourse watch，直接赋值后再设章节）
  formCourse.value = q.course_id ?? ''
  Object.assign(newQuestion, {
    chapter: q.chapter_id,
    type: q.type,
    stem: q.stem,
    options: q.options ? [...q.options] : ['', '', '', ''],
    answer: q.answer,
    explanation: q.explanation,
  })
  dialogVisible.value = true
}

async function handleSave() {
  if (!formCourse.value) {
    ElMessage.warning('请选择所属课程')
    return
  }
  if (typeof newQuestion.chapter !== 'number') {
    ElMessage.warning('请选择所属章节')
    return
  }
  if (!newQuestion.stem.trim() || !newQuestion.answer.trim()) {
    ElMessage.warning('请填写题干和答案')
    return
  }

  const payload = {
    chapter_id: newQuestion.chapter,
    type: newQuestion.type,
    stem: newQuestion.stem.trim(),
    answer: newQuestion.answer.trim(),
    explanation: newQuestion.explanation.trim(),
    options: newQuestion.type === 'choice' ? newQuestion.options.filter(o => o.trim()) : [],
  }

  try {
    if (editingId.value) {
      await updateQuestion(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createQuestion(payload)
      ElMessage.success('已添加')
    }
    await fetchQuestions()
    dialogVisible.value = false
  } catch {
    ElMessage.error('保存失败，请稍后重试')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该题目？删除后不可恢复。', '确认删除', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    })
    await apiDeleteQuestion(id)
    questions.value = questions.value.filter(q => q.id !== id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

// ────────────── Excel 批量导入 ──────────────
const importDialogVisible = ref(false)
const importFile = ref<File | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

function openImport() {
  importFile.value = null
  importDialogVisible.value = true
}

function handleImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    importFile.value = input.files[0]
  }
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  importing.value = true
  try {
    const result = await importQuestions(importFile.value)
    ElMessage.success(`导入完成：成功 ${result.success_count} 题，失败 ${result.fail_count} 题`)
    importDialogVisible.value = false
    await fetchQuestions()
  } catch {
    ElMessage.error('导入失败，请检查文件格式后重试')
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="questions-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>题库管理</h1>
      <div class="header-actions">
        <el-button round @click="openImport">导入题目</el-button>
        <el-button type="primary" round @click="openNew">新增题目</el-button>
      </div>
    </div>

    <!-- 三级联动筛选栏 -->
    <div class="filter-bar">
      <!-- 课程筛选 -->
      <el-select
        v-model="filterCourse"
        placeholder="全部课程"
        clearable
        size="default"
        style="width: 160px"
        @change="handleFilterCourseChange"
      >
        <el-option
          v-for="course in courses"
          :key="course.id"
          :label="course.name"
          :value="course.id"
        />
      </el-select>
      <!-- 章节筛选（联动课程） -->
      <el-select
        v-model="filterChapter"
        placeholder="全部章节"
        clearable
        size="default"
        style="width: 180px"
        @change="handleFilterChange"
      >
        <el-option
          v-for="chapter in filterChapterOptions"
          :key="chapter.id"
          :label="`${chapter.num} ${chapter.title}`"
          :value="chapter.id"
        />
      </el-select>
      <!-- 题型筛选 -->
      <el-select
        v-model="filterType"
        placeholder="全部题型"
        clearable
        size="default"
        style="width: 130px"
        @change="handleFilterChange"
      >
        <el-option label="选择题" value="choice" />
        <el-option label="填空题" value="fill" />
      </el-select>
      <el-button @click="resetFilter">重置</el-button>
      <span class="filter-count">共 {{ questions.length }} 题</span>
    </div>

    <!-- 题目列表 -->
    <el-table :data="questions" stripe style="width: 100%" v-loading="loading">
      <el-table-column type="index" label="序号" width="60" />
      <el-table-column label="题干" min-width="240">
        <template #default="{ row }">
          {{ row.stem.length > 40 ? row.stem.slice(0, 40) + '…' : row.stem }}
        </template>
      </el-table-column>
      <el-table-column label="题型" width="90">
        <template #default="{ row }">
          <el-tag :type="row.type === 'choice' ? '' : 'success'" size="small" effect="plain">
            {{ row.type === 'choice' ? '选择题' : '填空题' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="所属课程" width="140">
        <template #default="{ row }">
          <span>{{ row.course_name || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="所属章节" width="160">
        <template #default="{ row }">
          <span>{{ row.chapter_name || `章节 ${row.chapter_id}` }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <div v-if="!loading && questions.length === 0" class="empty-state">
      <p>暂无题目，点击「新增题目」或「导入题目」开始维护题库。</p>
    </div>

    <!-- 新增/编辑题目弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑题目' : '新增题目'" width="560px">
      <!-- 1. 所属课程 -->
      <div class="form-group">
        <label>所属课程 <span class="required">*</span></label>
        <el-select
          v-model="formCourse"
          size="large"
          style="width: 100%"
          placeholder="请选择课程"
          @change="handleFormCourseChange"
        >
          <el-option
            v-for="course in courses"
            :key="course.id"
            :label="course.name"
            :value="course.id"
          />
        </el-select>
        <p v-if="courses.length === 0" class="form-hint warn">
          暂无课程，请先前往课程管理页面创建课程。
        </p>
      </div>
      <!-- 2. 所属章节（联动课程） -->
      <div class="form-group">
        <label>所属章节 <span class="required">*</span></label>
        <el-select
          v-model="newQuestion.chapter"
          size="large"
          style="width: 100%"
          placeholder="请先选择课程"
          :disabled="!formCourse"
        >
          <el-option
            v-for="chapter in formChapterOptions"
            :key="chapter.id"
            :label="`${chapter.num} ${chapter.title}`"
            :value="chapter.id"
          />
        </el-select>
        <p v-if="formCourse && formChapterOptions.length === 0" class="form-hint">
          该课程下暂无章节。
        </p>
      </div>
      <!-- 3. 题型 -->
      <div class="form-group">
        <label>题型</label>
        <el-radio-group v-model="newQuestion.type" size="large">
          <el-radio-button value="choice">选择题</el-radio-button>
          <el-radio-button value="fill">填空题</el-radio-button>
        </el-radio-group>
      </div>
      <!-- 4. 题干 -->
      <div class="form-group">
        <label>题干 <span class="required">*</span></label>
        <el-input v-model="newQuestion.stem" type="textarea" :rows="3" placeholder="请输入题目内容" />
      </div>
      <!-- 5. 选项（仅选择题） -->
      <div v-if="newQuestion.type === 'choice'" class="form-group">
        <label>选项</label>
        <div v-for="(_, i) in newQuestion.options" :key="i" class="option-row">
          <span class="option-label">{{ ['A', 'B', 'C', 'D'][i] }}</span>
          <el-input v-model="newQuestion.options[i]" :placeholder="`选项 ${['A', 'B', 'C', 'D'][i]}`" size="large" />
        </div>
      </div>
      <!-- 6. 答案 -->
      <div class="form-group">
        <label>答案 <span class="required">*</span></label>
        <el-input v-model="newQuestion.answer" placeholder="选择题填 A/B/C/D，填空题填关键词" size="large" />
      </div>
      <!-- 7. 解析 -->
      <div class="form-group">
        <label>解析</label>
        <el-input v-model="newQuestion.explanation" type="textarea" :rows="2" placeholder="答案解析（选填）" />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Excel 批量导入弹窗 -->
    <el-dialog v-model="importDialogVisible" title="Excel 批量导入题目" width="500px">
      <div class="import-info">
        <p>请上传 .xlsx 文件，表头格式：</p>
        <table class="format-table">
          <thead>
            <tr><th>type</th><th>chapter</th><th>stem</th><th>options</th><th>answer</th><th>explanation</th></tr>
          </thead>
          <tbody>
            <tr><td>choice</td><td>01</td><td>图灵测试由谁提出？</td><td>A. xxx|B. xxx|C. xxx|D. xxx</td><td>A</td><td>解析内容</td></tr>
          </tbody>
        </table>
        <p class="import-note">type 为 choice 或 fill，chapter 填章节编号或章节标题，填空题 options 留空。</p>
      </div>
      <div class="upload-zone-import" @click="importInput?.click()">
        <input ref="importInput" type="file" accept=".xlsx,.xls" hidden @change="handleImportFile" />
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span v-if="!importFile">点击选择 Excel 文件</span>
        <span v-else class="file-name">{{ importFile.name }}</span>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">开始导入</el-button>
      </template>
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

.header-actions {
  display: flex;
  gap: var(--space-sm);
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
  flex-wrap: wrap;
}

.filter-count {
  font-size: 0.85rem;
  color: var(--color-text-muted);
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

.required {
  color: #f56c6c;
  margin-left: 2px;
}

.form-hint {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 6px;
}

.form-hint.warn {
  color: #e6a23c;
}

.option-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.option-label {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  background: var(--color-bg-alt);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.import-info {
  margin-bottom: var(--space-lg);
}

.import-info p {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-sm);
}

.format-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
  margin: var(--space-sm) 0;
}

.format-table th,
.format-table td {
  border: 1px solid var(--color-border);
  padding: 0.3rem 0.5rem;
  text-align: center;
}

.format-table th {
  background: var(--color-bg-alt);
  font-weight: 600;
}

.import-note {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.upload-zone-import {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.upload-zone-import:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.file-name {
  color: var(--color-primary);
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}
</style>

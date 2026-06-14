<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createQuestion, deleteQuestion, downloadQuestionTemplate, getQuestions, importQuestions, updateQuestion, type Question } from '@/api/question'
import { getCourses, type Course } from '@/api/course'

const courses = ref<Course[]>([])
const writableCourses = ref<Course[]>([])
const questions = ref<Question[]>([])
const loading = ref(true)
const filterCourse = ref<number | ''>('')
const filterType = ref<'' | 'choice' | 'fill' | 'multi_choice'>('')
const filterKeyword = ref('')
const filterTag = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const selectedQuestions = ref<Question[]>([])
const batchDeleting = ref(false)
const importDialogVisible = ref(false)
const importFile = ref<File | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)
const importErrors = ref<{ row: number; reason: string }[]>([])
const importErrorDialogVisible = ref(false)
const importFailureReason = ref('')

const form = reactive({
  course_id: '' as number | '',
  type: 'choice' as 'choice' | 'fill' | 'multi_choice',
  stem: '',
  options: ['', '', '', ''],
  answer: '',
  explanation: '',
  tags: [] as string[],
})

function hasTag(row: Question, tag: string) {
  const keyword = tag.trim().toLowerCase()
  if (!keyword) return true
  return (row.tags || []).some(item => item.toLowerCase().includes(keyword))
}

async function loadCourses() {
  const all = await getCourses()
  courses.value = all
  writableCourses.value = all.filter(course => course.is_owner)
}

async function loadQuestions() {
  loading.value = true
  try {
    const result = await getQuestions({
      course_id: filterCourse.value || undefined,
      type: filterType.value || undefined,
      keyword: filterKeyword.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    questions.value = result.items.filter(item => hasTag(item, filterTag.value))
    total.value = filterTag.value ? questions.value.length : result.total
  } catch {
    ElMessage.error('题目加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filterCourse.value = ''
  filterType.value = ''
  filterKeyword.value = ''
  filterTag.value = ''
  page.value = 1
  loadQuestions()
}

function handlePageChange(newPage: number) {
  page.value = newPage
  loadQuestions()
}

function openNew() {
  editingId.value = null
  Object.assign(form, {
    course_id: filterCourse.value || '',
    type: 'choice',
    stem: '',
    options: ['', '', '', ''],
    answer: '',
    explanation: '',
    tags: [],
  })
  dialogVisible.value = true
}

function openEdit(row: Question) {
  editingId.value = row.id
  Object.assign(form, {
    course_id: row.course_id,
    type: row.type,
    stem: row.stem,
    options: row.options?.length ? [...row.options] : ['', '', '', ''],
    answer: row.answer,
    explanation: row.explanation,
    tags: [...(row.tags || [])],
  })
  dialogVisible.value = true
}

async function handleSave() {
  if (typeof form.course_id !== 'number') {
    ElMessage.warning('请选择所属课程')
    return
  }
  if (!form.stem.trim() || !form.answer.trim()) {
    ElMessage.warning('请填写题干和答案')
    return
  }

  const payload = {
    course_id: form.course_id,
    type: form.type,
    stem: form.stem.trim(),
    options: form.type === 'choice' || form.type === 'multi_choice' ? form.options.map(item => item.trim()).filter(Boolean) : [],
    answer: form.answer.trim(),
    explanation: form.explanation.trim(),
    tags: form.tags.map(item => item.trim()).filter(Boolean),
  }

  try {
    if (editingId.value) {
      await updateQuestion(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createQuestion(payload)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    await loadQuestions()
  } catch {
    ElMessage.error('保存失败，请检查课程和题目内容')
  }
}

async function handleDelete(row: Question) {
  try {
    await ElMessageBox.confirm('确定删除该题目？删除后不可恢复。', '确认删除', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    })
    await deleteQuestion(row.id)
    questions.value = questions.value.filter(item => item.id !== row.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('删除失败，请稍后重试')
  }
}

function handleSelectionChange(rows: Question[]) {
  selectedQuestions.value = rows
}

function selectableQuestion(row: Question) {
  return !row.is_synced
}

async function handleBatchDelete() {
  const deletableRows = selectedQuestions.value.filter(selectableQuestion)
  if (deletableRows.length === 0) {
    ElMessage.warning('请选择可删除的题目')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${deletableRows.length} 道题目？删除后不可恢复。`, '批量删除确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    })
    batchDeleting.value = true
    const results = await Promise.allSettled(deletableRows.map(item => deleteQuestion(item.id)))
    const successIds = results
      .map((result, index) => result.status === 'fulfilled' ? deletableRows[index]?.id : undefined)
      .filter((id): id is number => typeof id === 'number')
    const failedCount = results.length - successIds.length
    questions.value = questions.value.filter(item => !successIds.includes(item.id))
    selectedQuestions.value = []
    if (failedCount > 0) {
      ElMessage.warning(`已删除 ${successIds.length} 道题，${failedCount} 道删除失败`)
    } else {
      ElMessage.success(`已删除 ${successIds.length} 道题`)
    }
    await loadQuestions()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('批量删除失败，请稍后重试')
  } finally {
    batchDeleting.value = false
  }
}

const templateType = ref<'all' | 'choice' | 'fill' | 'multi_choice'>('all')

function openImport() {
  importFile.value = null
  templateType.value = 'all'
  importDialogVisible.value = true
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

async function handleDownloadTemplate() {
  try {
    const blob = await downloadQuestionTemplate(templateType.value)
    const filename = templateType.value === 'choice' ? 'choice-question-template.xlsx' : templateType.value === 'fill' ? 'fill-question-template.xlsx' : templateType.value === 'multi_choice' ? 'multi-choice-question-template.xlsx' : 'question-template.xlsx'
    triggerDownload(blob as Blob, filename)
  } catch {
    ElMessage.error('模板下载失败，请稍后重试')
  }
}

function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  importFile.value = input.files?.[0] || null
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  importing.value = true
  importFailureReason.value = ''
  importErrors.value = []
  try {
    const result = await importQuestions(importFile.value)
    ElMessage.success(`导入完成：成功 ${result.success_count} 题，失败 ${result.fail_count} 题`)
    if (result.errors && result.errors.length > 0) {
      importErrors.value = result.errors
      importErrorDialogVisible.value = true
    } else {
      importErrorDialogVisible.value = false
    }
    importDialogVisible.value = false
    page.value = 1
    await loadQuestions()
  } catch (error) {
    const message = error instanceof Error && error.message ? error.message : '导入失败，请检查文件格式和课程名称'
    importFailureReason.value = message
    importErrors.value = []
    importErrorDialogVisible.value = true
    ElMessage.error(message)
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadCourses(), loadQuestions()])
})
</script>

<template>
  <div class="questions-page">
    <div class="page-header">
      <h1>题库管理</h1>
      <div class="header-actions">
        <el-button round @click="openImport">导入题目</el-button>
        <el-button type="primary" round @click="openNew">新增题目</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="filterKeyword" placeholder="搜索题干" clearable style="width: 200px" @keyup.enter="loadQuestions" @clear="loadQuestions" />
      <el-select v-model="filterCourse" placeholder="全部课程" clearable style="width: 220px" @change="page = 1; loadQuestions()">
        <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
      </el-select>
      <el-select v-model="filterType" placeholder="全部题型" clearable style="width: 140px" @change="page = 1; loadQuestions()">
        <el-option label="选择题" value="choice" />
        <el-option label="多选题" value="multi_choice" />
        <el-option label="填空题" value="fill" />
      </el-select>
      <el-input v-model="filterTag" placeholder="搜索标签" clearable style="width: 160px" @keyup.enter="page = 1; loadQuestions()" @clear="page = 1; loadQuestions()" />
      <el-button @click="resetFilter">重置</el-button>
      <el-button
        type="danger"
        plain
        :disabled="selectedQuestions.length === 0"
        :loading="batchDeleting"
        @click="handleBatchDelete"
      >
        批量删除
      </el-button>
      <span class="filter-count">共 {{ total }} 题</span>
    </div>

    <el-table :data="questions" stripe style="width: 100%" v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="48" :selectable="selectableQuestion" />
      <el-table-column type="index" label="序号" width="70" />
      <el-table-column label="题干" min-width="260">
        <template #default="{ row }">
          <span>{{ row.stem.length > 48 ? row.stem.slice(0, 48) + '…' : row.stem }}</span>
          <span v-if="row.type === 'multi_choice'" class="multi-tag">（多选题）</span>
          <el-tag v-if="row.is_synced" class="synced-tag" size="small" type="info" effect="plain">
            公共同步
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="题型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.type === 'choice' ? '' : row.type === 'multi_choice' ? 'warning' : 'success'" size="small" effect="plain">
            {{ row.type === 'choice' ? '选择题' : row.type === 'multi_choice' ? '多选题' : '填空题' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="course_name" label="所属课程" min-width="160" />
      <el-table-column label="课程标签" min-width="150">
        <template #default="{ row }">
          <div class="tag-list">
            <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
            <span v-if="!row.tags?.length" class="readonly-text">-</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="!row.is_synced" text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="!row.is_synced" type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
          <span v-else class="readonly-text">只读</span>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && questions.length === 0" class="empty-state">
      暂无题目，点击"新增题目"或"导入题目"开始维护题库。
    </div>

    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑题目' : '新增题目'" width="560px">
      <div class="form-group">
        <label>所属课程</label>
        <el-select v-model="form.course_id" placeholder="请选择课程" size="large" style="width: 100%">
          <el-option v-for="course in writableCourses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>题型</label>
        <el-radio-group v-model="form.type" size="large">
          <el-radio-button value="choice">选择题</el-radio-button>
          <el-radio-button value="multi_choice">多选题</el-radio-button>
          <el-radio-button value="fill">填空题</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>课程标签</label>
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入标签后回车"
          size="large"
          style="width: 100%"
        />
      </div>
      <div class="form-group">
        <label>题干</label>
        <el-input v-model="form.stem" type="textarea" :rows="3" placeholder="请输入题目内容" />
      </div>
      <div v-if="form.type === 'choice' || form.type === 'multi_choice'" class="form-group">
        <label>选项</label>
        <div v-for="(_, index) in form.options" :key="index" class="option-row">
          <span class="option-label">{{ ['A', 'B', 'C', 'D'][index] }}</span>
          <el-input v-model="form.options[index]" :placeholder="`选项 ${['A', 'B', 'C', 'D'][index]}`" size="large" />
        </div>
      </div>
      <div class="form-group">
        <label>答案</label>
        <el-input v-model="form.answer" :placeholder="form.type === 'multi_choice' ? '多选题填 AB、ACD 等（排序的字母组合）' : '选择题填 A/B/C/D，填空题填关键词'" size="large" />
      </div>
      <div class="form-group">
        <label>解析</label>
        <el-input v-model="form.explanation" type="textarea" :rows="2" placeholder="答案解析（选填）" />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="Excel 批量导入题目" width="560px">
      <div class="import-info">
        <p>请先选择模板类型并下载，再按模板填写后上传。</p>
        <table class="format-table">
          <thead>
            <tr><th>题型</th><th>课程名称</th><th>标签</th><th>题干</th><th>选项（选择题用 | 分隔）</th><th>答案</th><th>解析</th></tr>
          </thead>
          <tbody>
            <tr><td>choice</td><td>示例课程</td><td>人工智能</td><td>图灵测试由谁提出？</td><td>A. 图灵|B. 冯·诺依曼|C. 乔布斯|D. 爱因斯坦</td><td>A</td><td>图灵提出了图灵测试。</td></tr>
            <tr><td>multi_choice</td><td>示例课程</td><td>编程基础|多选</td><td>以下哪些是编程语言？</td><td>A. Python|B. Java|C. HTML|D. C++</td><td>ABD</td><td>HTML 是标记语言，不是编程语言。</td></tr>
            <tr><td>fill</td><td>示例课程</td><td>通识常识</td><td>中国的首都是哪里？</td><td></td><td>北京</td><td>填空题直接填写答案关键词。</td></tr>
          </tbody>
        </table>
        <p class="import-note">请将"课程名称"填写为当前教师已有课程名称；"标签"支持用逗号、顿号或 | 分隔多个标签；"题型"支持 choice、multi_choice 和 fill。多选题答案列填写排序后的字母组合，如 ABD。</p>
      </div>
      <div class="import-actions">
        <div class="template-block">
          <el-select v-model="templateType" style="width: 160px">
            <el-option label="全部题型模板" value="all" />
            <el-option label="选择题模板" value="choice" />
            <el-option label="多选题模板" value="multi_choice" />
            <el-option label="填空题模板" value="fill" />
          </el-select>
          <el-button class="download-btn" @click="handleDownloadTemplate">下载模板</el-button>
        </div>
        <div class="upload-zone" @click="importInput?.click()">
          <input ref="importInput" type="file" accept=".xlsx,.xls" hidden @change="handleImportFile" />
          <span v-if="!importFile">点击选择 Excel 文件</span>
          <span v-else class="file-name">{{ importFile.name }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 导入失败详情弹窗 -->
    <el-dialog v-model="importErrorDialogVisible" title="导入失败详情" width="560px">
      <div v-if="importFailureReason" class="import-failure-reason">
        {{ importFailureReason }}
      </div>
      <el-table v-else :data="importErrors" stripe max-height="400">
        <el-table-column prop="row" label="行号" width="80" />
        <el-table-column prop="reason" label="失败原因" />
      </el-table>
      <template #footer>
        <el-button @click="importErrorDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header,
.filter-bar,
.header-actions {
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

.filter-bar {
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
}

.filter-count,
.empty-state,
.import-note {
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: var(--space-lg) 0;
}

.import-actions {
  display: flex;
  gap: var(--space-lg);
  align-items: stretch;
  margin-top: var(--space-md);
  flex-wrap: wrap;
}

.import-failure-reason {
  padding: var(--space-md);
  border: 1px solid #fecaca;
  border-radius: var(--radius-sm);
  background: #fef2f2;
  color: #b91c1c;
  line-height: 1.6;
}

.template-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.download-btn {
  align-self: flex-start;
}

.empty-state {
  padding: var(--space-3xl) 0;
  text-align: center;
}

.synced-tag,
.multi-tag {
  margin-left: var(--space-sm);
}

.multi-tag {
  font-size: 0.75rem;
  font-weight: 600;
  color: #d97706;
}

.readonly-text {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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
  font-weight: 700;
  background: var(--color-bg-alt);
  border-radius: var(--radius-sm);
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
  padding: 0.35rem 0.5rem;
  text-align: center;
}

.upload-zone {
  min-width: 280px;
  min-height: 120px;
  padding: var(--space-2xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.upload-zone:hover,
.file-name {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
</style>

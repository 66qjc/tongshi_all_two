<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createQuestion, downloadQuestionTemplate, getQuestionTags, getQuestions, importQuestions, updateQuestion, type Question } from '@/api/question'
import { useDebounce } from '@/composables/useDebounce'

const questions = ref<Question[]>([])
const loading = ref(true)
// 全站共享题库：不再按课程筛选题目（后端忽略 course_id 过滤）
const filterType = ref<'' | 'choice' | 'fill' | 'multi_choice'>('')
const filterKeyword = ref('')
const debouncedKeyword = useDebounce(filterKeyword, 300)
watch(debouncedKeyword, () => {
  page.value = 1
  loadQuestions()
})
const filterTag = ref('')
const tagOptions = ref<string[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const importDialogVisible = ref(false)
const importFile = ref<File | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)
const importErrors = ref<{ row: number; reason: string }[]>([])
const importSkips = ref<{ row: number; reason: string }[]>([])
const importErrorDialogVisible = ref(false)
const importFailureReason = ref('')

const form = reactive({
  type: 'choice' as 'choice' | 'fill' | 'multi_choice',
  stem: '',
  options: ['', '', '', ''],
  answer: '',
  explanation: '',
  tags: [] as string[],
  star_rating: 3,
})

function getQuestionTagType(type: Question['type']) {
  if (type === 'choice') return 'primary'
  if (type === 'multi_choice') return 'warning'
  return 'success'
}

async function loadQuestions() {
  loading.value = true
  try {
    const result = await getQuestions({
      type: filterType.value || undefined,
      keyword: debouncedKeyword.value || undefined,
      tag: filterTag.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    questions.value = result.items
    total.value = result.total
  } catch {
    ElMessage.error('题目加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function loadTagOptions() {
  try {
    tagOptions.value = await getQuestionTags()
  } catch {
    // 标签选项失败不阻断主列表与手输
    tagOptions.value = []
  }
}

function resetFilter() {
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
    type: 'choice',
    stem: '',
    options: ['', '', '', ''],
    answer: '',
    explanation: '',
    tags: [],
    star_rating: 3,
  })
  dialogVisible.value = true
}

function openEdit(row: Question) {
  editingId.value = row.id
  Object.assign(form, {
    type: row.type,
    stem: row.stem,
    options: row.options?.length ? [...row.options] : ['', '', '', ''],
    answer: row.answer,
    explanation: row.explanation,
    tags: [...(row.tags || [])],
    star_rating: row.star_rating || 3,
  })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.stem.trim() || !form.answer.trim()) {
    ElMessage.warning('请填写题干和答案')
    return
  }

  const payload = {
    type: form.type,
    stem: form.stem.trim(),
    options: form.type === 'choice' || form.type === 'multi_choice' ? form.options.map(item => item.trim()).filter(Boolean) : [],
    answer: form.answer.trim(),
    explanation: form.explanation.trim(),
    tags: form.tags.map(item => item.trim()).filter(Boolean),
    star_rating: form.star_rating || 3,
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
    await Promise.all([loadQuestions(), loadTagOptions()])
  } catch {
    ElMessage.error('保存失败，请检查题目内容')
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
  importSkips.value = []
  try {
    const result = await importQuestions(importFile.value)
    // 构建成功提示
    const parts = [`成功 ${result.success_count} 题`]
    if (result.skip_count > 0) parts.push(`跳过 ${result.skip_count} 题（已存在）`)
    if (result.fail_count > 0) parts.push(`失败 ${result.fail_count} 题`)
    ElMessage.success(`导入完成：${parts.join('，')}`)
    importErrors.value = result.errors || []
    importSkips.value = result.skips || []
    if (importErrors.value.length > 0 || importSkips.value.length > 0) {
      importErrorDialogVisible.value = true
    } else {
      importErrorDialogVisible.value = false
    }
    importDialogVisible.value = false
    page.value = 1
    await Promise.all([loadQuestions(), loadTagOptions()])
  } catch (error) {
    const message = error instanceof Error && error.message ? error.message : '导入失败，请检查文件格式'
    importFailureReason.value = message
    importErrors.value = []
    importErrorDialogVisible.value = true
    ElMessage.error(message)
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadQuestions(), loadTagOptions()])
})
</script>

<template>
  <div class="questions-page">
    <div class="page-header">
      <h1>共享题库</h1>
      <div class="header-actions">
        <el-button round @click="openImport">导入题目</el-button>
        <el-button type="primary" round @click="openNew">新增题目</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="filterKeyword" placeholder="搜索题干" clearable style="width: 200px" @keyup.enter="loadQuestions" @clear="loadQuestions" />
      <el-select v-model="filterType" placeholder="全部题型" clearable style="width: 140px" @change="page = 1; loadQuestions()">
        <el-option label="选择题" value="choice" />
        <el-option label="多选题" value="multi_choice" />
        <el-option label="填空题" value="fill" />
      </el-select>
      <el-select
        v-model="filterTag"
        clearable
        filterable
        allow-create
        default-first-option
        placeholder="选择或输入标签"
        style="width: 180px"
        @change="page = 1; loadQuestions()"
        @clear="page = 1; loadQuestions()"
      >
        <el-option v-for="tag in tagOptions" :key="tag" :label="tag" :value="tag" />
      </el-select>
      <el-button @click="resetFilter">重置</el-button>
      <span class="filter-count">共享题库 共 {{ total }} 题</span>
    </div>

    <el-table :data="questions" stripe style="width: 100%" v-loading="loading">
      <el-table-column label="序号" width="70">
        <template #default="{ $index }">
          {{ (page - 1) * pageSize + $index + 1 }}
        </template>
      </el-table-column>
      <el-table-column label="题干" min-width="260">
        <template #default="{ row }">
          <span>{{ row.stem.length > 48 ? row.stem.slice(0, 48) + '…' : row.stem }}</span>
          <span v-if="row.type === 'multi_choice'" class="multi-tag">（多选题）</span>
        </template>
      </el-table-column>
      <el-table-column label="题型" width="100">
        <template #default="{ row }">
          <el-tag :type="getQuestionTagType(row.type)" size="small" effect="plain">
            {{ row.type === 'choice' ? '选择题' : row.type === 'multi_choice' ? '多选题' : '填空题' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="添加人" min-width="120">
        <template #default="{ row }">
          {{ row.creator_name || row.created_by || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="星级" width="140">
        <template #default="{ row }">
          <el-rate :model-value="Number(row.star_rating) || 3" disabled :max="5" />
        </template>
      </el-table-column>
      <el-table-column label="标签" min-width="150">
        <template #default="{ row }">
          <div class="tag-list">
            <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
            <span v-if="!row.tags?.length" class="readonly-text">-</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button
            text
            size="small"
            :disabled="row.is_owner === false"
            :title="row.is_owner === false ? '该题由其他老师创建，请联系管理员修改' : ''"
            @click="openEdit(row)"
          >
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && questions.length === 0" class="empty-state">
      暂无题目，点击"新增题目"或"导入题目"开始维护共享题库。
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
        <label>题型</label>
        <el-radio-group v-model="form.type" size="large">
          <el-radio-button value="choice">选择题</el-radio-button>
          <el-radio-button value="multi_choice">多选题</el-radio-button>
          <el-radio-button value="fill">填空题</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>标签</label>
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="选择已有标签，或输入后回车创建"
          size="large"
          style="width: 100%"
        >
          <el-option v-for="tag in tagOptions" :key="tag" :label="tag" :value="tag" />
        </el-select>
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
        <label>题目星级</label>
        <el-rate v-model="form.star_rating" :max="5" show-score />
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
            <tr><th>题型（必填）</th><th>课程名称（可选）</th><th>标签（必填）</th><th>题干（必填）</th><th>选项（选择题用 | 分隔）</th><th>答案（必填）</th><th>解析</th></tr>
          </thead>
          <tbody>
            <tr><td>choice</td><td></td><td>人工智能</td><td>图灵测试由谁提出？</td><td>A. 图灵|B. 冯·诺依曼|C. 乔布斯|D. 爱因斯坦</td><td>A</td><td>图灵提出了图灵测试。</td></tr>
            <tr><td>multi_choice</td><td></td><td>编程基础|多选</td><td>以下哪些是编程语言？</td><td>A. Python|B. Java|C. HTML|D. C++</td><td>ABD</td><td>HTML 是标记语言，不是编程语言。</td></tr>
            <tr><td>fill</td><td></td><td>通识常识</td><td>中国的首都是哪里？</td><td></td><td>北京</td><td>填空题直接填写答案关键词。</td></tr>
          </tbody>
        </table>
        <p class="import-note">「题型、标签、题干、答案」均为必填；「标签」支持用逗号、顿号或 | 分隔多个标签；「课程名称」可选，不填则写入独立共享题；题型列填写 choice（选择题）、multi_choice（多选题）或 fill（填空题）。多选题答案列填写排序后的字母组合，如 ABD。</p>
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

    <!-- 导入结果详情弹窗 -->
    <el-dialog v-model="importErrorDialogVisible" title="导入结果详情" width="560px">
      <div v-if="importFailureReason" class="import-failure-reason">
        {{ importFailureReason }}
      </div>
      <template v-else>
        <!-- 跳过的题目 -->
        <template v-if="importSkips.length > 0">
          <h4 style="margin: 0 0 8px; color: #e6a23c;">以下题目已存在，已跳过（{{ importSkips.length }} 题）</h4>
          <el-table :data="importSkips" stripe max-height="200">
            <el-table-column prop="row" label="行号" width="80" />
            <el-table-column prop="reason" label="跳过原因" />
          </el-table>
        </template>
        <!-- 导入失败的题目 -->
        <template v-if="importErrors.length > 0">
          <h4 :style="{ margin: importSkips.length > 0 ? '16px 0 8px' : '0 0 8px', color: '#f56c6c' }">以下题目导入失败（{{ importErrors.length }} 题）</h4>
          <el-table :data="importErrors" stripe max-height="200">
            <el-table-column prop="row" label="行号" width="80" />
            <el-table-column prop="reason" label="失败原因" />
          </el-table>
        </template>
      </template>
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

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createQuestion, deleteQuestion, getQuestions, importQuestions, updateQuestion, type Question } from '@/api/question'
import { getCourses, type Course } from '@/api/course'

const courses = ref<Course[]>([])
const questions = ref<Question[]>([])
const loading = ref(true)
const filterCourse = ref<number | ''>('')
const filterType = ref<'' | 'choice' | 'fill'>('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const importDialogVisible = ref(false)
const importFile = ref<File | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

const form = reactive({
  course_id: '' as number | '',
  type: 'choice' as 'choice' | 'fill',
  stem: '',
  options: ['', '', '', ''],
  answer: '',
  explanation: '',
})

async function loadCourses() {
  courses.value = await getCourses()
}

async function loadQuestions() {
  loading.value = true
  try {
    questions.value = await getQuestions({
      course_id: filterCourse.value || undefined,
      type: filterType.value || undefined,
    })
  } catch {
    ElMessage.error('题目加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filterCourse.value = ''
  filterType.value = ''
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
    options: form.type === 'choice' ? form.options.map(item => item.trim()).filter(Boolean) : [],
    answer: form.answer.trim(),
    explanation: form.explanation.trim(),
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

function openImport() {
  importFile.value = null
  importDialogVisible.value = true
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
  try {
    const result = await importQuestions(importFile.value)
    ElMessage.success(`导入完成：成功 ${result.success_count} 题，失败 ${result.fail_count} 题`)
    importDialogVisible.value = false
    await loadQuestions()
  } catch {
    ElMessage.error('导入失败，请检查文件格式和课程名称')
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
      <el-select v-model="filterCourse" placeholder="全部课程" clearable style="width: 220px" @change="loadQuestions">
        <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
      </el-select>
      <el-select v-model="filterType" placeholder="全部题型" clearable style="width: 140px" @change="loadQuestions">
        <el-option label="选择题" value="choice" />
        <el-option label="填空题" value="fill" />
      </el-select>
      <el-button @click="resetFilter">重置</el-button>
      <span class="filter-count">共 {{ questions.length }} 题</span>
    </div>

    <el-table :data="questions" stripe style="width: 100%" v-loading="loading">
      <el-table-column type="index" label="序号" width="70" />
      <el-table-column label="题干" min-width="260">
        <template #default="{ row }">
          {{ row.stem.length > 48 ? row.stem.slice(0, 48) + '…' : row.stem }}
        </template>
      </el-table-column>
      <el-table-column label="题型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.type === 'choice' ? '' : 'success'" size="small" effect="plain">
            {{ row.type === 'choice' ? '选择题' : '填空题' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="course_name" label="所属课程" min-width="160" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && questions.length === 0" class="empty-state">
      暂无题目，点击“新增题目”或“导入题目”开始维护题库。
    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑题目' : '新增题目'" width="560px">
      <div class="form-group">
        <label>所属课程</label>
        <el-select v-model="form.course_id" placeholder="请选择课程" size="large" style="width: 100%">
          <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>题型</label>
        <el-radio-group v-model="form.type" size="large">
          <el-radio-button value="choice">选择题</el-radio-button>
          <el-radio-button value="fill">填空题</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>题干</label>
        <el-input v-model="form.stem" type="textarea" :rows="3" placeholder="请输入题目内容" />
      </div>
      <div v-if="form.type === 'choice'" class="form-group">
        <label>选项</label>
        <div v-for="(_, index) in form.options" :key="index" class="option-row">
          <span class="option-label">{{ ['A', 'B', 'C', 'D'][index] }}</span>
          <el-input v-model="form.options[index]" :placeholder="`选项 ${['A', 'B', 'C', 'D'][index]}`" size="large" />
        </div>
      </div>
      <div class="form-group">
        <label>答案</label>
        <el-input v-model="form.answer" placeholder="选择题填 A/B/C/D，填空题填关键词" size="large" />
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

    <el-dialog v-model="importDialogVisible" title="Excel 批量导入题目" width="500px">
      <div class="import-info">
        <p>请上传 .xlsx 文件，表头格式：</p>
        <table class="format-table">
          <thead>
            <tr><th>type</th><th>course</th><th>stem</th><th>options</th><th>answer</th><th>explanation</th></tr>
          </thead>
          <tbody>
            <tr><td>choice</td><td>测试课程</td><td>图灵测试由谁提出？</td><td>A. 图灵|B. 冯诺依曼</td><td>A</td><td>解析内容</td></tr>
          </tbody>
        </table>
        <p class="import-note">course 填当前教师已有课程名称；type 为 choice 或 fill。</p>
      </div>
      <div class="upload-zone" @click="importInput?.click()">
        <input ref="importInput" type="file" accept=".xlsx,.xls" hidden @change="handleImportFile" />
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

.empty-state {
  padding: var(--space-3xl) 0;
  text-align: center;
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
  padding: var(--space-xl);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--color-text-muted);
  cursor: pointer;
}

.upload-zone:hover,
.file-name {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
</style>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getQuestions, createQuestion, updateQuestion, deleteQuestion as apiDeleteQuestion, importQuestions, type Question } from '@/api/question'

const chapterNames: Record<number, string> = {
  1: '人工智能概述',
  2: '计算机基础知识',
  3: 'AI 理论基础',
  4: 'AI 工具使用',
  5: 'AI 前沿与应用',
  6: 'AI 伦理与未来',
}

const questions = ref<Question[]>([])
const loading = ref(true)

const filterChapter = ref<number | ''>('')
const filterType = ref<'' | 'choice' | 'fill'>('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const newQuestion = reactive({
  chapter: 1,
  type: 'choice' as 'choice' | 'fill',
  stem: '',
  options: ['', '', '', ''],
  answer: '',
  explanation: '',
})

onMounted(async () => {
  try {
    questions.value = await getQuestions()
  } finally {
    loading.value = false
  }
})

const filteredQuestions = computed(() => {
  return questions.value.filter(q => {
    if (filterChapter.value && q.chapter_id !== filterChapter.value) return false
    if (filterType.value && q.type !== filterType.value) return false
    return true
  })
})

function openNew() {
  editingId.value = null
  Object.assign(newQuestion, { chapter: 1, type: 'choice', stem: '', options: ['', '', '', ''], answer: '', explanation: '' })
  dialogVisible.value = true
}

function openEdit(q: Question) {
  editingId.value = q.id
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
    questions.value = await getQuestions()
    dialogVisible.value = false
  } catch {
    ElMessage.error('保存失败')
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该题目？', '提示', { type: 'warning' })
    await apiDeleteQuestion(id)
    questions.value = questions.value.filter(q => q.id !== id)
    ElMessage.success('已删除')
  } catch {}
}

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
    questions.value = await getQuestions()
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}
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
      <el-select v-model="filterChapter" placeholder="全部章节" clearable size="default" style="width: 180px">
        <el-option v-for="(name, id) in chapterNames" :key="id" :label="name" :value="Number(id)" />
      </el-select>
      <el-select v-model="filterType" placeholder="全部题型" clearable size="default" style="width: 140px">
        <el-option label="选择题" value="choice" />
        <el-option label="填空题" value="fill" />
      </el-select>
      <span class="filter-count">共 {{ filteredQuestions.length }} 题</span>
    </div>

    <el-table :data="filteredQuestions" stripe style="width: 100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="题干" min-width="250">
        <template #default="{ row }">
          {{ row.stem.length > 40 ? row.stem.slice(0, 40) + '...' : row.stem }}
        </template>
      </el-table-column>
      <el-table-column label="题型" width="80">
        <template #default="{ row }">
          <el-tag :type="row.type === 'choice' ? '' : 'success'" size="small" effect="plain">
            {{ row.type === 'choice' ? '选择' : '填空' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="章节" width="140">
        <template #default="{ row }">
          {{ chapterNames[row.chapter_id] }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Edit dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑题目' : '新增题目'" width="560px">
      <div class="form-group">
        <label>章节</label>
        <el-select v-model="newQuestion.chapter" size="large" style="width: 100%">
          <el-option v-for="(name, id) in chapterNames" :key="id" :label="name" :value="Number(id)" />
        </el-select>
      </div>
      <div class="form-group">
        <label>题型</label>
        <el-radio-group v-model="newQuestion.type" size="large">
          <el-radio-button value="choice">选择题</el-radio-button>
          <el-radio-button value="fill">填空题</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>题干</label>
        <el-input v-model="newQuestion.stem" type="textarea" :rows="3" placeholder="请输入题目内容" />
      </div>
      <div v-if="newQuestion.type === 'choice'" class="form-group">
        <label>选项</label>
        <div v-for="(_, i) in newQuestion.options" :key="i" class="option-row">
          <span class="option-label">{{ ['A', 'B', 'C', 'D'][i] }}</span>
          <el-input v-model="newQuestion.options[i]" :placeholder="`选项 ${['A', 'B', 'C', 'D'][i]}`" size="large" />
        </div>
      </div>
      <div class="form-group">
        <label>答案</label>
        <el-input v-model="newQuestion.answer" placeholder="选择题填 A/B/C/D，填空题填关键词" size="large" />
      </div>
      <div class="form-group">
        <label>解析</label>
        <el-input v-model="newQuestion.explanation" type="textarea" :rows="2" placeholder="答案解析" />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Import dialog -->
    <el-dialog v-model="importDialogVisible" title="Excel 批量导入题目" width="500px">
      <div class="import-info">
        <p>请上传 .xlsx 文件，表头格式：</p>
        <table class="format-table">
          <thead><tr><th>type</th><th>chapter</th><th>stem</th><th>options</th><th>answer</th><th>explanation</th></tr></thead>
          <tbody><tr><td>choice</td><td>01</td><td>图灵测试由谁提出？</td><td>A. xxx|B. xxx|C. xxx|D. xxx</td><td>A</td><td>解析内容</td></tr></tbody>
        </table>
        <p class="import-note">type 为 choice 或 fill，chapter 填章节编号（如 01），填空题 options 留空。</p>
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
</style>

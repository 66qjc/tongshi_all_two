<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteAdminQuestionBank,
  createAdminQuestionBankItem,
  deleteAdminQuestionBankItem,
  downloadAdminQuestionBankTemplate,
  getAdminQuestionBank,
  getAdminQuestionBankContributions,
  importAdminQuestionBank,
  updateAdminQuestionBankItem,
  type AdminQuestionBankContribution,
} from '@/api/adminQuestionBank'
import type { Question } from '@/api/question'

const loading = ref(false)
const questions = ref<Question[]>([])
const selectedQuestions = ref<Question[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterType = ref('')
const filterKeyword = ref('')
const filterTag = ref('')
const contributions = ref<AdminQuestionBankContribution[]>([])
const contributionTotal = ref(0)
const contributionPage = ref(1)
const activeTab = ref<'questions' | 'contributions'>('questions')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)
const importErrors = ref<{ row: number; reason: string }[]>([])
const importErrorDialogVisible = ref(false)

const form = reactive({
  type: 'choice' as 'choice' | 'fill' | 'multi_choice',
  stem: '',
  options: ['', '', '', ''],
  answer: '',
  explanation: '',
  tags: [] as string[],
  star_rating: 3,
})

async function loadQuestions() {
  loading.value = true
  try {
    const result = await getAdminQuestionBank({
      type: filterType.value || undefined,
      keyword: filterKeyword.value || undefined,
      tag: filterTag.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    questions.value = result.items
    total.value = result.total
  } catch {
    ElMessage.error('题库加载失败')
  } finally {
    loading.value = false
  }
}

async function loadContributions() {
  try {
    const result = await getAdminQuestionBankContributions(contributionPage.value, 20)
    contributions.value = result.items
    contributionTotal.value = result.total
  } catch {
    ElMessage.error('贡献记录加载失败')
  }
}

function openCreate() {
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
  saving.value = true
  const payload = {
    type: form.type,
    stem: form.stem.trim(),
    options: form.type === 'fill' ? [] : form.options.map(item => item.trim()).filter(Boolean),
    answer: form.answer.trim(),
    explanation: form.explanation.trim(),
    tags: form.tags.map(item => item.trim()).filter(Boolean),
    star_rating: form.star_rating || 3,
  }
  try {
    if (editingId.value) {
      await updateAdminQuestionBankItem(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      // 共享题库以标签为主，新增默认独立题（不挂课程）
      await createAdminQuestionBankItem(payload, null)
      ElMessage.success('已新增到共享题库')
    }
    dialogVisible.value = false
    await loadQuestions()
  } catch (error: any) {
    ElMessage.error(error?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeQuestion(row: Question) {
  try {
    await ElMessageBox.confirm(
      '确定将该题目移入回收站吗？该题目可能由教师贡献。被未删除作业引用的题目不能删除；历史答题记录会保留，可在回收站恢复。',
      '移入回收站',
      { type: 'warning', confirmButtonText: '移入回收站', cancelButtonText: '取消' },
    )
    await deleteAdminQuestionBankItem(row.id)
    ElMessage.success('已移入回收站')
    selectedQuestions.value = selectedQuestions.value.filter(item => item.id !== row.id)
    await loadQuestions()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

async function removeSelectedQuestions() {
  const ids = selectedQuestions.value.map(item => item.id)
  if (!ids.length) {
    ElMessage.warning('请先勾选要删除的题目')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定将已选中的 ${ids.length} 道题目移入回收站吗？其中可能包含教师贡献题目。被未删除作业引用的题目不能删除；历史答题记录会保留。`,
      '批量移入回收站',
      { type: 'warning', confirmButtonText: '移入回收站', cancelButtonText: '取消' },
    )
    const result = await batchDeleteAdminQuestionBank(ids)
    const missing = result.missing_ids?.length || 0
    ElMessage.success(
      missing > 0
        ? `已移入回收站 ${result.deleted_count} 道，${missing} 道未找到`
        : `已移入回收站 ${result.deleted_count} 道题目`,
    )
    selectedQuestions.value = []
    await loadQuestions()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('批量删除失败')
  }
}

async function removeAllQuestions() {
  const ids = questions.value.map(item => item.id)
  if (!ids.length) {
    ElMessage.warning('当前题库没有可删除的题目')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定将当前页全部 ${ids.length} 道题目移入回收站吗？其中可能包含教师贡献题目。被未删除作业引用的题目不能删除；历史答题记录会保留。`,
      '一键移入回收站',
      { type: 'warning', confirmButtonText: '全部移入回收站', cancelButtonText: '取消' },
    )
    const result = await batchDeleteAdminQuestionBank(ids)
    ElMessage.success(`已移入回收站 ${result.deleted_count} 道题目`)
    selectedQuestions.value = []
    await loadQuestions()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('一键删除题目失败')
  }
}

async function handleImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  importing.value = true
  try {
    const result = await importAdminQuestionBank(importFile.value, null)
    ElMessage.success(`导入完成：成功 ${result.success_count} 题，跳过 ${result.skip_count} 题，失败 ${result.fail_count} 题`)
    const importDetails = [...result.skips, ...result.errors]
    if (importDetails.length > 0) {
      importErrors.value = importDetails
      importErrorDialogVisible.value = true
    }
    importFile.value = null
    await loadQuestions()
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  } finally {
    importing.value = false
  }
}

async function handleDownloadTemplate() {
  try {
    const blob = await downloadAdminQuestionBankTemplate('all')
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'admin-question-bank-template.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('模板下载失败')
  }
}

onMounted(async () => {
  await Promise.all([loadQuestions(), loadContributions()])
})
</script>

<template>
  <section class="admin-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">全站共享</p>
        <h1>共享题库</h1>
        <p>全站共享题目维护；以标签、题型、星级组织，不按课程划分。</p>
      </div>
      <div class="header-actions">
        <el-button @click="handleDownloadTemplate">下载导入模板</el-button>
        <el-button type="primary" @click="openCreate">新增题目</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="题目维护" name="questions">
        <el-card shadow="never" class="filter-card">
          <el-form :inline="true">
            <el-form-item label="题型">
              <el-select v-model="filterType" clearable placeholder="全部" style="width: 140px" @change="page = 1; loadQuestions()">
                <el-option label="选择题" value="choice" />
                <el-option label="多选题" value="multi_choice" />
                <el-option label="填空题" value="fill" />
              </el-select>
            </el-form-item>
            <el-form-item label="题干">
              <el-input v-model="filterKeyword" clearable placeholder="搜索题干" @keyup.enter="page = 1; loadQuestions()" />
            </el-form-item>
            <el-form-item label="标签">
              <el-input v-model="filterTag" clearable placeholder="标签关键词" @keyup.enter="page = 1; loadQuestions()" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="page = 1; loadQuestions()">查询</el-button>
              <el-button :disabled="!selectedQuestions.length" type="danger" plain @click="removeSelectedQuestions">
                删除选中{{ selectedQuestions.length ? `（${selectedQuestions.length}）` : '' }}
              </el-button>
              <el-button :disabled="!questions.length" type="danger" plain @click="removeAllQuestions">
                一键删除全部
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-table
          v-loading="loading"
          :data="questions"
          border
          empty-text="暂无题目"
          @selection-change="(rows: Question[]) => selectedQuestions = rows"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column label="序号" width="70">
            <template #default="{ $index }">
              {{ (page - 1) * pageSize + $index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="stem" label="题干" min-width="260" show-overflow-tooltip />
          <el-table-column label="题型" width="100">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">
                {{ row.type === 'choice' ? '选择题' : row.type === 'multi_choice' ? '多选题' : row.type === 'fill' ? '填空题' : row.type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="星级" width="140">
            <template #default="{ row }">
              <el-rate :model-value="Number(row.star_rating) || 3" disabled :max="5" />
            </template>
          </el-table-column>
          <el-table-column prop="creator_name" label="添加人" width="120" />
          <el-table-column label="标签" min-width="150">
            <template #default="{ row }">
              <div class="tag-list">
                <el-tag v-for="tag in row.tags || []" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                <span v-if="!row.tags?.length" class="readonly-text">-</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" plain @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="removeQuestion(row)">移入回收站</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager-row">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next, total"
            @current-change="loadQuestions"
          />
        </div>

        <el-card shadow="never" class="import-card">
          <h3>Excel 导入</h3>
          <p>题型、标签、题干、答案必填，课程名称可选；课程名称留空时导入独立共享题。题型列填写 choice（选择题）、multi_choice（多选题）或 fill（填空题）。</p>
          <div class="import-row">
            <input type="file" accept=".xlsx,.xls" @change="(e: Event) => importFile = (e.target as HTMLInputElement).files?.[0] || null" />
            <el-button type="primary" :loading="importing" @click="handleImport">开始导入</el-button>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="贡献记录" name="contributions">
        <el-table :data="contributions" border empty-text="暂无贡献记录">
          <el-table-column prop="created_at" label="时间" width="180" />
          <el-table-column prop="operator_name" label="操作人" width="120" />
          <el-table-column prop="action" label="动作" width="100" />
          <el-table-column prop="question_count" label="题数" width="80" />
          <el-table-column prop="public_course_name" label="课程上下文" min-width="180" />
        </el-table>
        <div class="pager-row">
          <el-pagination
            v-model:current-page="contributionPage"
            :page-size="20"
            :total="contributionTotal"
            layout="prev, pager, next, total"
            @current-change="loadContributions"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑共享题' : '新增共享题'" width="640px">
      <div class="form-group">
        <label>题型</label>
        <el-radio-group v-model="form.type">
          <el-radio-button value="choice">选择题</el-radio-button>
          <el-radio-button value="multi_choice">多选题</el-radio-button>
          <el-radio-button value="fill">填空题</el-radio-button>
        </el-radio-group>
      </div>
      <div class="form-group">
        <label>题干</label>
        <el-input v-model="form.stem" type="textarea" :rows="3" />
      </div>
      <div v-if="form.type !== 'fill'" class="form-group">
        <label>选项</label>
        <div v-for="(_, index) in form.options" :key="index" class="option-row">
          <span>{{ ['A', 'B', 'C', 'D'][index] }}</span>
          <el-input v-model="form.options[index]" />
        </div>
      </div>
      <div class="form-group">
        <label>答案</label>
        <el-input v-model="form.answer" />
      </div>
      <div class="form-group">
        <label>解析</label>
        <el-input v-model="form.explanation" type="textarea" :rows="2" />
      </div>
      <div class="form-group">
        <label>标签</label>
        <el-select v-model="form.tags" multiple filterable allow-create default-first-option style="width: 100%" />
      </div>
      <div class="form-group">
        <label>星级</label>
        <el-rate v-model="form.star_rating" :max="5" />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importErrorDialogVisible" title="导入未写入详情" width="560px">
      <el-table :data="importErrors" stripe max-height="400">
        <el-table-column prop="row" label="行号" width="80" />
        <el-table-column prop="reason" label="未写入原因" />
      </el-table>
      <template #footer>
        <el-button @click="importErrorDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 18px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
.page-header h1 { margin: 0; font-size: 1.5rem; }
.page-header p { margin: 6px 0 0; color: var(--color-text-secondary); }
.eyebrow { margin: 0 0 4px !important; font-size: 0.78rem; font-weight: 800; color: var(--color-primary); }
.header-actions { display: flex; gap: 8px; }
.filter-card, .import-card { border-color: var(--color-border); }
.pager-row { display: flex; justify-content: flex-end; margin-top: 12px; }
.import-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; margin-bottom: 6px; font-weight: 600; }
.option-row { display: grid; grid-template-columns: 28px 1fr; gap: 8px; margin-bottom: 8px; align-items: center; }
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.readonly-text {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
</style>

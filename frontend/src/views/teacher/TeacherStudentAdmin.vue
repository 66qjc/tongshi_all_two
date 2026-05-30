<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { enrollStudent, getClasses, getClassStudents, importStudents, unenrollStudent, type ClassInfo, type ClassStudent } from '@/api/class'

const route = useRoute()
const classes = ref<ClassInfo[]>([])
const selectedClassId = ref<number | ''>('')
const students = ref<ClassStudent[]>([])
const loading = ref(false)
const enrollDialogVisible = ref(false)
const importDialogVisible = ref(false)
const studentId = ref('')
const studentName = ref('')
const importFile = ref<File | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

async function loadClasses() {
  classes.value = await getClasses()
}

async function loadStudents() {
  if (typeof selectedClassId.value !== 'number') {
    students.value = []
    return
  }
  loading.value = true
  try {
    students.value = await getClassStudents(selectedClassId.value)
  } catch {
    ElMessage.error('学生列表加载失败')
  } finally {
    loading.value = false
  }
}

function openEnroll() {
  studentId.value = ''
  studentName.value = ''
  enrollDialogVisible.value = true
}

async function handleEnroll() {
  if (typeof selectedClassId.value !== 'number') {
    ElMessage.warning('请先选择班级')
    return
  }
  if (!studentId.value.trim() || !studentName.value.trim()) {
    ElMessage.warning('请输入学号和姓名')
    return
  }
  try {
    await enrollStudent(selectedClassId.value, studentId.value.trim(), studentName.value.trim())
    ElMessage.success('添加成功')
    enrollDialogVisible.value = false
    await loadStudents()
    await loadClasses()
  } catch {
    ElMessage.error('添加失败，请检查学号')
  }
}

async function handleUnenroll(row: ClassStudent) {
  if (typeof selectedClassId.value !== 'number') return
  try {
    await ElMessageBox.confirm(`确定将「${row.name}」移出该班级？`, '移除确认', { type: 'warning' })
    await unenrollStudent(selectedClassId.value, row.id)
    students.value = students.value.filter(item => item.id !== row.id)
    ElMessage.success('已移除')
    await loadClasses()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('移除失败，请稍后重试')
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
  if (typeof selectedClassId.value !== 'number') {
    ElMessage.warning('请先选择班级')
    return
  }
  if (!importFile.value) {
    ElMessage.warning('请选择 Excel 文件')
    return
  }
  importing.value = true
  try {
    const result = await importStudents(importFile.value, selectedClassId.value)
    ElMessage.success(`导入完成：成功 ${result.success_count} 条，跳过 ${result.skip_count} 条，失败 ${result.fail_count} 条`)
    importDialogVisible.value = false
    await loadStudents()
    await loadClasses()
  } catch {
    ElMessage.error('导入失败，请检查文件格式')
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await loadClasses()
  const classId = Number(route.query.class_id)
  if (Number.isFinite(classId) && classes.value.some(item => item.id === classId)) {
    selectedClassId.value = classId
  } else if (classes.value.length > 0) {
    selectedClassId.value = classes.value[0]?.id ?? ''
  }
  await loadStudents()
})

watch(selectedClassId, () => {
  loadStudents()
})
</script>

<template>
  <div class="student-admin-page">
    <div class="page-header">
      <h1>学生管理</h1>
      <div class="actions">
        <el-button round @click="openImport">Excel 导入</el-button>
        <el-button type="primary" round @click="openEnroll">手动添加</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-select v-model="selectedClassId" placeholder="选择班级" style="width: 280px">
        <el-option
          v-for="item in classes"
          :key="item.id"
          :label="`${item.course_name} · ${item.name}`"
          :value="item.id"
        />
      </el-select>
      <span class="filter-count">共 {{ students.length }} 名学生</span>
    </div>

    <el-table :data="students" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="学号" width="160" />
      <el-table-column prop="name" label="姓名" width="160" />
      <el-table-column prop="major" label="专业" min-width="180" />
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button type="danger" text size="small" @click="handleUnenroll(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && students.length === 0" class="empty-state">该班级暂无学生</div>

    <el-dialog v-model="enrollDialogVisible" title="手动添加学生" width="380px">
      <div class="form-group">
        <label>学号</label>
        <el-input v-model="studentId" placeholder="输入学生学号" size="large" />
      </div>
      <div class="form-group">
        <label>姓名</label>
        <el-input v-model="studentName" placeholder="输入学生姓名" size="large" />
      </div>
      <p class="hint">若该学号不存在，系统将自动创建学生账号。</p>
      <template #footer>
        <el-button @click="enrollDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEnroll">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="Excel 批量导入学生" width="480px">
      <div class="import-info">
        <p>请上传包含「学号」「姓名」列的 .xlsx 文件，姓名右侧一列将作为专业信息。</p>
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
.actions {
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
}

.filter-count,
.hint,
.import-info,
.empty-state {
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

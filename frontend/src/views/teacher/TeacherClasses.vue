<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getClasses, createClass, deleteClass as apiDeleteClass,
  getClassStudents, enrollStudent, unenrollStudent, importStudents,
  type ClassInfo, type ClassStudent,
} from '@/api/class'

const classes = ref<ClassInfo[]>([])
const loading = ref(true)

const createDialogVisible = ref(false)
const newClass = reactive({ name: '', major: '' })

const studentDialogVisible = ref(false)
const selectedClass = ref<ClassInfo | null>(null)
const classStudents = ref<ClassStudent[]>([])
const studentLoading = ref(false)

const enrollDialogVisible = ref(false)
const enrollStudentId = ref('')
const enrollStudentName = ref('')

const importDialogVisible = ref(false)
const importFile = ref<File | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

onMounted(async () => {
  await loadClasses()
})

async function loadClasses() {
  loading.value = true
  try {
    classes.value = await getClasses()
  } catch {
    ElMessage.error('班级数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  newClass.name = ''
  newClass.major = ''
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!newClass.name.trim() || !newClass.major.trim()) {
    ElMessage.warning('请填写班级名称和专业')
    return
  }
  try {
    await createClass({ name: newClass.name.trim(), major: newClass.major.trim() })
    ElMessage.success('班级创建成功')
    createDialogVisible.value = false
    await loadClasses()
  } catch {
    ElMessage.error('创建失败')
  }
}

async function handleDelete(cls: ClassInfo) {
  try {
    await ElMessageBox.confirm(
      `确定删除班级「${cls.name}」？只属于该班级的学生账号和学习数据会一并删除；仍属于其它班级的学生只会移出当前班级。`,
      '提示',
      { type: 'warning' },
    )
    await apiDeleteClass(cls.id)
    classes.value = classes.value.filter(c => c.id !== cls.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

async function openStudents(cls: ClassInfo) {
  selectedClass.value = cls
  studentDialogVisible.value = true
  studentLoading.value = true
  try {
    classStudents.value = await getClassStudents(cls.id)
  } catch {
    ElMessage.error('学生列表加载失败，请稍后重试')
  } finally {
    studentLoading.value = false
  }
}

function openEnroll() {
  enrollStudentId.value = ''
  enrollStudentName.value = ''
  enrollDialogVisible.value = true
}

async function handleEnroll() {
  if (!selectedClass.value || !enrollStudentId.value.trim() || !enrollStudentName.value.trim()) {
    ElMessage.warning('请输入学号和姓名')
    return
  }
  try {
    await enrollStudent(selectedClass.value.id, enrollStudentId.value.trim(), enrollStudentName.value.trim())
    ElMessage.success('添加成功')
    enrollDialogVisible.value = false
    classStudents.value = await getClassStudents(selectedClass.value.id)
    await loadClasses()
  } catch {
    ElMessage.error('添加失败，请检查学号是否正确')
  }
}

async function handleUnenroll(student: ClassStudent) {
  if (!selectedClass.value) return
  try {
    await ElMessageBox.confirm(`确定将「${student.name}」移出该班级？`, '提示', { type: 'warning' })
    await unenrollStudent(selectedClass.value.id, student.id)
    classStudents.value = classStudents.value.filter(s => s.id !== student.id)
    ElMessage.success('已移除')
    await loadClasses()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('移除失败，请稍后重试')
    }
  }
}

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
    const result = await importStudents(importFile.value)
    ElMessage.success(`导入完成：成功 ${result.success_count} 条，跳过 ${result.skip_count} 条，失败 ${result.fail_count} 条`)
    importDialogVisible.value = false
    await loadClasses()
  } catch {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="classes-page">
    <div class="page-header">
      <h1>班级管理</h1>
      <div class="header-actions">
        <el-button round @click="openImport">导入学生</el-button>
        <el-button type="primary" round @click="openCreate">新增班级</el-button>
      </div>
    </div>

    <el-table :data="classes" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="name" label="班级名称" min-width="160" />
      <el-table-column prop="major" label="所属专业" min-width="160" />
      <el-table-column label="学生人数" width="100" align="center">
        <template #default="{ row }">
          <span class="count-badge">{{ row.student_count }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="140" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openStudents(row)">查看学生</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && classes.length === 0" class="empty-state">
      <p>暂无班级，点击「新增班级」开始创建</p>
    </div>

    <!-- Create class dialog -->
    <el-dialog v-model="createDialogVisible" title="新增班级" width="420px">
      <div class="form-group">
        <label>专业名称</label>
        <el-input v-model="newClass.major" placeholder="如：自动化专业" size="large" />
      </div>
      <div class="form-group">
        <label>班级名称</label>
        <el-input v-model="newClass.name" placeholder="如：2025级1班" size="large" />
      </div>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- Students dialog -->
    <el-dialog v-model="studentDialogVisible" :title="selectedClass ? `${selectedClass.major} · ${selectedClass.name} 学生列表` : '学生列表'" width="600px">
      <div class="student-toolbar">
        <span class="student-count">共 {{ classStudents.length }} 名学生</span>
        <el-button size="small" type="primary" plain round @click="openEnroll">手动添加</el-button>
      </div>
      <el-table :data="classStudents" stripe v-loading="studentLoading" style="width: 100%">
        <el-table-column prop="id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="major" label="专业" min-width="140" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" text size="small" @click="handleUnenroll(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!studentLoading && classStudents.length === 0" class="empty-mini">
        该班级暂无学生
      </div>
    </el-dialog>

    <!-- Enroll student dialog -->
    <el-dialog v-model="enrollDialogVisible" title="手动添加学生" width="380px">
      <div class="form-group">
        <label>学号</label>
        <el-input v-model="enrollStudentId" placeholder="输入学生学号" size="large" />
      </div>
      <div class="form-group">
        <label>姓名</label>
        <el-input v-model="enrollStudentName" placeholder="输入学生姓名" size="large" />
      </div>
      <p class="enroll-hint">若该学号不存在，系统将自动创建学生账号（默认密码 a123456）</p>
      <template #footer>
        <el-button @click="enrollDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEnroll">添加</el-button>
      </template>
    </el-dialog>

    <!-- Import dialog -->
    <el-dialog v-model="importDialogVisible" title="Excel 批量导入学生" width="480px">
      <div class="import-info">
        <p>请上传 .xlsx 文件，表头格式：</p>
        <table class="format-table">
          <thead><tr><th>student_id</th><th>name</th><th>major</th><th>class_name</th></tr></thead>
          <tbody><tr><td>2025006</td><td>赵同学</td><td>自动化专业</td><td>2025级1班</td></tr></tbody>
        </table>
        <p class="import-note">系统将自动创建不存在的用户（默认密码 123456）和班级。</p>
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

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
}

.count-badge {
  font-weight: 700;
  color: var(--color-primary);
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

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.empty-mini {
  text-align: center;
  padding: var(--space-xl) 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.student-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.student-count {
  font-size: 0.85rem;
  color: var(--color-text-muted);
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
  font-size: 0.8rem;
  margin: var(--space-sm) 0;
}

.format-table th,
.format-table td {
  border: 1px solid var(--color-border);
  padding: 0.3rem 0.6rem;
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

.enroll-hint {
  font-size: 0.8rem;
  color: #999;
  margin-top: 8px;
}
</style>

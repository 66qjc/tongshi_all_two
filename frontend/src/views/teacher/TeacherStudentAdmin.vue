<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { enrollStudent, getClasses, getClassStudents, importStudents, unenrollStudent, type ClassInfo, type ClassStudent } from '@/api/class'
import { batchDeleteStudents, getPasswordResetRequests, approvePasswordResetRequest, rejectPasswordResetRequest, type PasswordResetRequest } from '@/api/teacher'

const route = useRoute()
const classes = ref<ClassInfo[]>([])
const selectedClassId = ref<number | ''>('')
const students = ref<ClassStudent[]>([])
const searchStudentId = ref('')
const loading = ref(false)

const filteredStudents = computed(() => {
  const keyword = searchStudentId.value.trim().toLowerCase()
  if (!keyword) return students.value
  return students.value.filter(item => String(item.id).toLowerCase().includes(keyword))
})
const enrollDialogVisible = ref(false)
const importDialogVisible = ref(false)
const studentId = ref('')
const studentName = ref('')
const studentMajor = ref('')
const importFile = ref<File | null>(null)
const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)
const selectedStudentIds = ref<string[]>([])
const batchDeleting = ref(false)

async function loadClasses() {
  classes.value = await getClasses()
}

async function loadStudents() {
  if (typeof selectedClassId.value !== 'number') {
    students.value = []
    selectedStudentIds.value = []
    searchStudentId.value = ''
    return
  }
  loading.value = true
  try {
    students.value = await getClassStudents(selectedClassId.value)
    selectedStudentIds.value = []
  } catch {
    ElMessage.error('学生列表加载失败')
  } finally {
    loading.value = false
  }
}

function openEnroll() {
  studentId.value = ''
  studentName.value = ''
  studentMajor.value = ''
  enrollDialogVisible.value = true
}

async function handleEnroll() {
  if (typeof selectedClassId.value !== 'number') {
    ElMessage.warning('请先选择班级')
    return
  }
  const rawId = studentId.value.trim()
  const rawName = studentName.value.trim()
  if (!rawId || !rawName) {
    ElMessage.warning('请输入学号和姓名')
    return
  }
  // 学号应包含数字，不应包含中文；姓名反之
  const hasChinese = (s: string) => /[一-鿿]/.test(s)
  const hasDigit = (s: string) => /\d/.test(s)
  const isDigitsOnly = (s: string) => /^\d+$/.test(s)

  if (hasChinese(rawId)) {
    ElMessage.warning('学号不应包含中文，请检查是否将姓名填入了学号栏')
    return
  }
  if (!hasDigit(rawId)) {
    ElMessage.warning('学号应包含数字，请检查学号是否填写正确')
    return
  }
  if (isDigitsOnly(rawName)) {
    ElMessage.warning('姓名不能为纯数字，请检查是否将学号填入了姓名栏')
    return
  }
  try {
    await enrollStudent(selectedClassId.value, rawId, rawName, studentMajor.value.trim())
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

function handleSelectionChange(rows: ClassStudent[]) {
  selectedStudentIds.value = rows.map(row => row.id)
}

async function handleBatchDelete() {
  if (selectedStudentIds.value.length === 0) {
    ElMessage.warning('请先选择要移出的学生')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${selectedStudentIds.value.length} 名学生从你的班级中移出？该操作不会删除学生账号，也不会影响其他教师班级或课程数据。`,
      '确认批量移出',
      {
        type: 'warning',
        confirmButtonText: '确认移出',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  batchDeleting.value = true
  try {
    const result = await batchDeleteStudents(selectedStudentIds.value)
    ElMessage.success(`成功移出 ${result.deleted_count} 名学生`)
    if (result.failed_ids?.length > 0) {
      ElMessage.warning(`${result.failed_ids.length} 名学生移出失败`)
    }
    selectedStudentIds.value = []
    await loadStudents()
    await loadClasses()
  } catch {
    ElMessage.error('批量移出失败，请稍后重试')
  } finally {
    batchDeleting.value = false
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

watch(selectedClassId, () => {
  searchStudentId.value = ''
  loadStudents()
})

// 密码重置申请管理
const resetRequests = ref<PasswordResetRequest[]>([])
const resetRequestsLoading = ref(false)
const resetStatusFilter = ref('pending')

async function loadResetRequests() {
  resetRequestsLoading.value = true
  try {
    resetRequests.value = await getPasswordResetRequests(resetStatusFilter.value)
  } catch {
    resetRequests.value = []
  } finally {
    resetRequestsLoading.value = false
  }
}

function switchResetFilter(status: string) {
  resetStatusFilter.value = status
  loadResetRequests()
}

async function handleApproveReset(requestId: number) {
  try {
    const result = await approvePasswordResetRequest(requestId)
    ElMessageBox.alert(`临时密码：<b>${result.temp_password}</b><br/>请告知学生，首次登录后需修改密码。`, '密码已重置', {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '复制并关闭',
      type: 'success',
    }).then(() => {
      navigator.clipboard.writeText(result.temp_password)
    })
    await loadResetRequests()
  } catch {
    // 拦截器已显示错误或用户取消弹窗
  }
}

async function handleRejectReset(requestId: number) {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt('请输入驳回原因（可选）', '驳回申请', {
      inputType: 'textarea',
      confirmButtonText: '确认驳回',
    })
    reason = String(result.value || '').trim()
  } catch { return }
  try {
    await rejectPasswordResetRequest(requestId, reason)
    ElMessage.success('已驳回')
    await loadResetRequests()
  } catch {
    // 拦截器已显示错误
  }
}

function copyTempPassword(pwd: string) {
  navigator.clipboard.writeText(pwd)
  ElMessage.success('已复制临时密码')
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
  loadResetRequests()
})
</script>

<template>
  <div class="student-admin-page">
    <div class="page-header">
      <h1>学生管理</h1>
      <div class="actions">
        <el-button
          type="danger"
          round
          :disabled="selectedStudentIds.length === 0"
          :loading="batchDeleting"
          @click="handleBatchDelete"
        >
          批量移出{{ selectedStudentIds.length > 0 ? ` (${selectedStudentIds.length})` : '' }}
        </el-button>
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
      <span class="filter-count">
        共 {{ searchStudentId.trim() ? filteredStudents.length : students.length }} 名学生
        <template v-if="searchStudentId.trim() && filteredStudents.length !== students.length">
          （本班 {{ students.length }} 人）
        </template>
      </span>
      <el-input
        v-model="searchStudentId"
        class="student-search"
        placeholder="按学号搜索"
        clearable
        style="width: 220px; margin-left: auto"
      />
    </div>

    <el-table :data="filteredStudents" stripe style="width: 100%" v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="50" />
      <el-table-column prop="serial_no" label="序号" width="80" align="center" />
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
    <div v-else-if="!loading && filteredStudents.length === 0" class="empty-state">未找到匹配学号的学生</div>

    <el-dialog v-model="enrollDialogVisible" title="手动添加学生" width="420px">
      <div class="form-group">
        <label>学号</label>
        <el-input v-model="studentId" placeholder="输入学生学号" size="large" />
      </div>
      <div class="form-group">
        <label>姓名</label>
        <el-input v-model="studentName" placeholder="输入学生姓名" size="large" />
      </div>
      <div class="form-group">
        <label>专业</label>
        <el-input v-model="studentMajor" placeholder="输入学生专业（选填）" size="large" />
      </div>
      <p class="hint">若该学号不存在，系统将自动创建学生账号。</p>
      <template #footer>
        <el-button @click="enrollDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEnroll">添加</el-button>
      </template>
    </el-dialog>

    <!-- 密码重置管理 -->
    <el-card class="reset-card" style="margin-top:24px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-weight:700;font-size:1rem">🔑 密码重置管理</span>
          <el-radio-group v-model="resetStatusFilter" size="small" @change="(v: string) => switchResetFilter(v)">
            <el-radio-button value="pending">待处理</el-radio-button>
            <el-radio-button value="approved">已通过</el-radio-button>
            <el-radio-button value="rejected">已驳回</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <el-table :data="resetRequests" v-loading="resetRequestsLoading" empty-text="暂无相关记录" stripe>
        <el-table-column prop="user_name" label="学生" width="110" />
        <el-table-column prop="user_id" label="学号" width="110" />
        <el-table-column prop="message" label="留言" min-width="160" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="warning" size="small">待处理</el-tag>
            <el-tag v-else-if="row.status === 'approved'" type="success" size="small">已通过</el-tag>
            <el-tag v-else type="info" size="small">已驳回</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="临时密码" width="130">
          <template #default="{ row }">
            <template v-if="row.status === 'approved' && row.temp_password">
              <code style="font-size:0.82rem">{{ row.temp_password }}</code>
              <el-button link type="primary" size="small" @click="copyTempPassword(row.temp_password)">复制</el-button>
            </template>
            <span v-else style="color:#999">-</span>
          </template>
        </el-table-column>
        <el-table-column label="处理人" width="100">
          <template #default="{ row }">
            {{ row.resolved_by_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="170">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString() : '' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="handleApproveReset(row.id)">重置</el-button>
              <el-button type="danger" size="small" @click="handleRejectReset(row.id)">驳回</el-button>
            </template>
            <span v-else style="color:#999;font-size:0.8rem">{{ row.resolved_at ? new Date(row.resolved_at).toLocaleString().split(' ')[0] : '' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="importDialogVisible" title="Excel 批量导入学生" width="480px">
      <div class="import-info">
        <p>请上传包含「学号」「姓名」列的 .xlsx 文件；如包含「序号」列，系统会保留该序号。</p>
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
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
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

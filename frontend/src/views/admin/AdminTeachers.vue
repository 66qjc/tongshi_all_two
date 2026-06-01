<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  getTeachers,
  createTeacher,
  deleteTeacher,
  resetTeacherPassword,
  importTeachers,
} from '../../api/admin'
import type { TeacherItem, ImportResult } from '../../api/admin'

const teachers = ref<TeacherItem[]>([])
const loading = ref(false)

// 手动添加
const showAddDialog = ref(false)
const addForm = ref({ id: '', name: '', major: '' })
const addLoading = ref(false)

// Excel 导入
const showImportDialog = ref(false)
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const importResult = ref<ImportResult | null>(null)

const fetchTeachers = async () => {
  loading.value = true
  try {
    const data = await getTeachers()
    teachers.value = data || []
  } catch {
    ElMessage.error('获取教师列表失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = async () => {
  if (!addForm.value.id.trim() || !addForm.value.name.trim()) {
    ElMessage.warning('工号和姓名为必填项')
    return
  }
  addLoading.value = true
  try {
    await createTeacher({
      id: addForm.value.id.trim(),
      name: addForm.value.name.trim(),
      major: addForm.value.major.trim() || undefined,
    })
    ElMessage.success('教师账号创建成功，初始密码为 123456')
    showAddDialog.value = false
    addForm.value = { id: '', name: '', major: '' }
    await fetchTeachers()
  } catch (err: any) {
    ElMessage.error(err?.message || '创建失败')
  } finally {
    addLoading.value = false
  }
}

const handleDelete = async (teacherId: string) => {
  try {
    await deleteTeacher(teacherId)
    ElMessage.success('教师账号已删除')
    await fetchTeachers()
  } catch {
    ElMessage.error('删除失败')
  }
}

const handleResetPassword = async (teacherId: string) => {
  try {
    await resetTeacherPassword(teacherId)
    ElMessage.success('密码已重置为 123456')
    await fetchTeachers()
  } catch {
    ElMessage.error('重置密码失败')
  }
}

const handleFileChange = (uploadFile: UploadFile) => {
  importFile.value = uploadFile.raw || null
}

const handleImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请先选择 Excel 文件')
    return
  }
  importLoading.value = true
  importResult.value = null
  try {
    const data = await importTeachers(importFile.value)
    importResult.value = data || null
    ElMessage.success(importResult.value?.message || '导入完成')
    await fetchTeachers()
  } catch (err: any) {
    ElMessage.error(err?.message || '导入失败')
  } finally {
    importLoading.value = false
  }
}

const closeImportDialog = () => {
  showImportDialog.value = false
  importFile.value = null
  importResult.value = null
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

onMounted(fetchTeachers)
</script>

<template>
  <div class="teachers-page">
    <!-- 页面标题 + 操作按钮 -->
    <div class="page-header">
      <h1 class="page-title">教师账号管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showAddDialog = true">
          手动添加教师
        </el-button>
        <el-button @click="showImportDialog = true">
          Excel 批量导入
        </el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table
      :data="teachers"
      v-loading="loading"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="工号" width="140" />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="major" label="专业" min-width="150">
        <template #default="{ row }">
          {{ row.major || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="130">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag v-if="row.needs_password_change" type="warning" size="small">待改密</el-tag>
          <el-tag v-else type="success" size="small">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-popconfirm
            title="确定要将该教师密码重置为 123456 吗？"
            confirm-button-text="确定重置"
            cancel-button-text="取消"
            @confirm="handleResetPassword(row.id)"
          >
            <template #reference>
              <el-button size="small" type="warning" text>重置密码</el-button>
            </template>
          </el-popconfirm>
          <el-popconfirm
            title="确定要删除该教师账号吗？此操作不可恢复。"
            confirm-button-text="确定删除"
            cancel-button-text="取消"
            @confirm="handleDelete(row.id)"
          >
            <template #reference>
              <el-button size="small" type="danger" text>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>

      <!-- 空状态 -->
      <template #empty>
        <el-empty description="暂无教师账号，点击右上角按钮添加" />
      </template>
    </el-table>

    <!-- 手动添加弹窗 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加教师账号"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="工号" required>
          <el-input v-model="addForm.id" placeholder="请输入工号（唯一）" clearable />
        </el-form-item>
        <el-form-item label="姓名" required>
          <el-input v-model="addForm.name" placeholder="请输入姓名" clearable />
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="addForm.major" placeholder="选填" clearable />
        </el-form-item>
      </el-form>
      <el-alert
        title="初始密码为 123456，教师首次登录需修改密码"
        type="info"
        :closable="false"
        style="margin-top: 8px"
      />
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="addLoading" @click="handleAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- Excel 批量导入弹窗 -->
    <el-dialog
      v-model="showImportDialog"
      title="批量导入教师"
      width="520px"
      :close-on-click-modal="false"
      @close="closeImportDialog"
    >
      <div class="import-tips">
        <p class="tips-title">Excel 文件格式要求：</p>
        <ul>
          <li>第一行为表头（内容可自定义）</li>
          <li>第一列：姓名</li>
          <li>第二列：工号</li>
          <li>仅支持 .xlsx 格式</li>
        </ul>
        <p class="tips-note">初始密码均为 123456，教师首次登录需修改密码。</p>
      </div>

      <el-upload
        action="#"
        :auto-upload="false"
        accept=".xlsx"
        :limit="1"
        :on-change="handleFileChange"
        drag
        style="margin-top: 16px"
      >
        <el-icon style="font-size: 48px; color: var(--el-color-primary)">
          <svg viewBox="0 0 24 24" width="48" height="48"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" fill="none" stroke="currentColor" stroke-width="2"/><polyline points="14 2 14 8 20 8" fill="none" stroke="currentColor" stroke-width="2"/></svg>
        </el-icon>
        <div class="el-upload__text">将 .xlsx 文件拖到此处，或<em>点击上传</em></div>
      </el-upload>

      <!-- 导入结果 -->
      <el-alert
        v-if="importResult"
        :title="`导入完成：成功 ${importResult.created_count} 条，跳过 ${importResult.skipped_count} 条（工号已存在则跳过）`"
        type="success"
        :closable="false"
        style="margin-top: 12px"
      />

      <template #footer>
        <el-button @click="closeImportDialog">取消</el-button>
        <el-button type="primary" :loading="importLoading" @click="handleImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.teachers-page {
  max-width: 1100px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: var(--font-serif);
  color: var(--color-text);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.import-tips {
  background: var(--color-bg-alt, #f1ece2);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  font-size: 0.875rem;
  color: var(--color-text-secondary, #606266);
  line-height: 1.8;
}

.tips-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--color-text, #303133);
}

.import-tips ul {
  padding-left: 20px;
  margin: 0 0 8px 0;
}

.tips-note {
  margin-top: 6px;
  color: var(--el-color-warning-dark-2, #b88230);
}
</style>

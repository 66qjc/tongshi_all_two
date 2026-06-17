<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile, UploadInstance } from 'element-plus'
import {
  getTeachers,
  createTeacher,
  deleteTeacher,
  getTeacherDependencies,
  resetTeacherPassword,
  importTeachers,
  downloadTeacherImportTemplate,
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
const uploadRef = ref<UploadInstance>()
const selectedFileName = ref('')
const templateDownloading = ref(false)

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
    // 第一步：检查关联数据
    const deps = await getTeacherDependencies(teacherId)
    const hasDeps = deps.course_count > 0 || deps.class_count > 0 || deps.announcement_count > 0

    if (hasDeps) {
      // 有关联数据，弹二次确认
      const parts: string[] = []
      if (deps.course_count > 0) parts.push(`${deps.course_count} 个课程`)
      if (deps.class_count > 0) parts.push(`${deps.class_count} 个班级`)
      if (deps.announcement_count > 0) parts.push(`${deps.announcement_count} 条公告`)
      if (deps.project_count > 0) parts.push(`${deps.project_count} 个作品`)
      if (deps.showcase_count > 0) parts.push(`${deps.showcase_count} 条图文`)
      const detail = parts.join('、')

      await ElMessageBox.confirm(
        `该教师名下仍有 ${detail}，删除后将<strong>永久清除</strong>这些数据且不可恢复。<br/><br/>确定要继续删除吗？`,
        '确认删除教师',
        {
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
          type: 'warning',
          dangerouslyUseHTMLString: true,
        },
      )
      // 用户确认，强制删除
      await deleteTeacher(teacherId, true)
    } else {
      // 无关联数据，直接删除
      await deleteTeacher(teacherId)
    }

    ElMessage.success('教师账号已删除')
    await fetchTeachers()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(err?.message || '删除失败')
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
  selectedFileName.value = uploadFile.name || ''
  importResult.value = null
}

const handleFileExceed = () => {
  ElMessage.warning('一次只能上传一个 Excel 文件，请先移除已选文件')
}

const handleDownloadTemplate = async () => {
  templateDownloading.value = true
  try {
    const blob = await downloadTeacherImportTemplate()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '教师批量导入模板.xlsx'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (err: any) {
    ElMessage.error(err?.message || '模板下载失败')
  } finally {
    templateDownloading.value = false
  }
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
    uploadRef.value?.clearFiles()
    importFile.value = null
    selectedFileName.value = ''
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
  selectedFileName.value = ''
  uploadRef.value?.clearFiles()
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
      <el-table-column prop="major" label="学院" min-width="150">
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
          <el-button size="small" type="danger" text @click="handleDelete(row.id)">删除</el-button>
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
        <el-form-item label="学院">
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
        <div class="tips-header">
          <p class="tips-title">Excel 文件格式要求：</p>
          <el-button
            type="primary"
            link
            :loading="templateDownloading"
            @click="handleDownloadTemplate"
          >
            下载导入模板
          </el-button>
        </div>
        <ul>
          <li>第一行为表头（内容可自定义）</li>
          <li>第一列：姓名</li>
          <li>第二列：工号</li>
          <li>第三列：学院（可选）</li>
          <li>仅支持 .xlsx 格式</li>
        </ul>
        <p class="tips-note">初始密码均为 123456，教师首次登录需修改密码。</p>
      </div>

      <el-upload
        ref="uploadRef"
        action="#"
        :auto-upload="false"
        accept=".xlsx"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="handleFileExceed"
        drag
        style="margin-top: 16px"
      >
        <el-icon style="font-size: 48px; color: var(--el-color-primary)">
          <svg viewBox="0 0 24 24" width="48" height="48"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" fill="none" stroke="currentColor" stroke-width="2"/><polyline points="14 2 14 8 20 8" fill="none" stroke="currentColor" stroke-width="2"/></svg>
        </el-icon>
        <div class="el-upload__text">将 .xlsx 文件拖到此处，或<em>点击上传</em></div>
      </el-upload>

      <el-alert
        v-if="selectedFileName"
        :title="`已选择：${selectedFileName}`"
        type="info"
        :closable="false"
        style="margin-top: 12px"
      />

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

.tips-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.tips-title {
  font-weight: 600;
  margin: 0;
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

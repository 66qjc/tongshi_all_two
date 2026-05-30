<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getCourses,
  createCourse,
  updateCourse,
  deleteCourse,
  type Course,
} from '@/api/course'

// ── 列表状态 ──────────────────────────────────────────────
const courses = ref<Course[]>([])
const loading = ref(true)
const router = useRouter()

// ── 弹窗状态 ──────────────────────────────────────────────
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formData = reactive({ name: '' })
const saving = ref(false)

// ── 加载课程列表 ───────────────────────────────────────────
async function loadCourses() {
  loading.value = true
  try {
    courses.value = await getCourses()
  } catch {
    ElMessage.error('课程列表加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadCourses()
})

// ── 新建课程 ───────────────────────────────────────────────
function openCreate() {
  isEdit.value = false
  editingId.value = null
  formData.name = ''
  dialogVisible.value = true
}

// ── 编辑课程 ───────────────────────────────────────────────
function openEdit(course: Course) {
  isEdit.value = true
  editingId.value = course.id
  formData.name = course.name
  dialogVisible.value = true
}

// ── 保存（新建/编辑共用） ─────────────────────────────────
async function handleSave() {
  if (!formData.name.trim()) {
    ElMessage.warning('请输入课程名称')
    return
  }
  saving.value = true
  try {
    if (isEdit.value && editingId.value !== null) {
      await updateCourse(editingId.value, { name: formData.name.trim() })
      ElMessage.success('课程更新成功')
    } else {
      await createCourse({ name: formData.name.trim() })
      ElMessage.success('课程创建成功')
    }
    dialogVisible.value = false
    await loadCourses()
  } catch {
    ElMessage.error(isEdit.value ? '更新失败，请稍后重试' : '创建失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

// ── 删除课程 ───────────────────────────────────────────────
async function handleDelete(course: Course) {
  try {
    await ElMessageBox.confirm(
      `确定删除课程「${course.name}」？存在资料、题目、学习记录或班级时系统会拒绝删除。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
    await deleteCourse(course.id)
    courses.value = courses.value.filter(c => c.id !== course.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

function openMaterials(course: Course) {
  router.push({ path: '/teacher/materials', query: { course_id: course.id } })
}

// ── 格式化创建时间 ─────────────────────────────────────────
function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  return dateStr.slice(0, 10)
}
</script>

<template>
  <div class="courses-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <h1>课程管理</h1>
      <el-button type="primary" round @click="openCreate">新建课程</el-button>
    </div>

    <!-- 课程列表表格 -->
    <el-table :data="courses" stripe style="width: 100%" v-loading="loading">
      <el-table-column type="index" label="序号" width="70" align="center" />
      <el-table-column prop="name" label="课程名称" min-width="200" />
      <el-table-column label="资料数" width="100" align="center">
        <template #default="{ row }">
          <span class="count-badge">{{ row.material_count ?? 0 }}</span>
        </template>
      </el-table-column>
      <el-table-column label="题目数" width="100" align="center">
        <template #default="{ row }">
          <span class="count-badge">{{ row.question_count ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="140">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openMaterials(row)">查看资料</el-button>
          <el-button text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <div v-if="!loading && courses.length === 0" class="empty-state">
      <p>暂无课程，请点击「新建课程」添加</p>
    </div>

    <!-- 新建 / 编辑课程弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑课程' : '新建课程'"
      width="420px"
      :close-on-click-modal="false"
    >
      <div class="form-group">
        <label>课程名称<span class="required">*</span></label>
        <el-input
          v-model="formData.name"
          placeholder="请输入课程名称"
          size="large"
          maxlength="100"
          show-word-limit
          @keyup.enter="handleSave"
        />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEdit ? '保存修改' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.courses-page {
  max-width: 960px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
}

.page-header h1 {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.count-badge {
  display: inline-block;
  padding: 2px 10px;
  background: var(--color-primary-glow, #f0f4ff);
  color: var(--color-primary, #4a6fa5);
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.empty-state {
  margin-top: var(--space-xl);
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  padding: var(--space-xl) 0;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
}

.form-group {
  margin-bottom: var(--space-md);
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.required {
  color: #e74c3c;
  margin-left: 2px;
}
</style>

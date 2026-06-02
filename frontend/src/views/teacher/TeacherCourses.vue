<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCourse,
  deleteCourse,
  getCourses,
  updateCourse,
  type Course,
} from '@/api/course'

const courses = ref<Course[]>([])
const loading = ref(true)
const router = useRouter()
const publicSearchKeyword = ref('')
const publicCourseDefaultLimit = 6

const myCourses = computed(() => courses.value.filter(course => !course.is_public))
const publicCourses = computed(() => courses.value.filter(course => course.is_public))
const filteredPublicCourses = computed(() => {
  const keyword = publicSearchKeyword.value.trim().toLowerCase()
  if (!keyword) return publicCourses.value
  return publicCourses.value.filter(course => course.name.toLowerCase().includes(keyword))
})
const displayedPublicCourses = computed(() => {
  if (publicSearchKeyword.value.trim()) return filteredPublicCourses.value
  return publicCourses.value.slice(0, publicCourseDefaultLimit)
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formData = reactive({
  name: '',
  is_public: false,
})
const saving = ref(false)

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

function openCreate() {
  isEdit.value = false
  editingId.value = null
  formData.name = ''
  formData.is_public = false
  dialogVisible.value = true
}

function openEdit(course: Course) {
  if (course.is_public && !course.is_owner) {
    ElMessage.warning('公共课程只能由创建者编辑')
    return
  }
  isEdit.value = true
  editingId.value = course.id
  formData.name = course.name
  formData.is_public = Boolean(course.is_public)
  dialogVisible.value = true
}

async function handleSave() {
  const name = formData.name.trim()
  if (!name) {
    ElMessage.warning('请输入课程名称')
    return
  }
  saving.value = true
  try {
    if (isEdit.value && editingId.value !== null) {
      await updateCourse(editingId.value, { name, is_public: formData.is_public })
      ElMessage.success('课程更新成功')
    } else {
      await createCourse({ name, is_public: formData.is_public })
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

async function handleDelete(course: Course) {
  if (course.is_public && !course.is_owner) {
    ElMessage.warning('公共课程只能由创建者删除')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除课程「${course.name}」？存在资料、题目、学习记录或班级时系统会拒绝删除。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
    await deleteCourse(course.id)
    courses.value = courses.value.filter(item => item.id !== course.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

function openMaterials(course: Course) {
  router.push({ path: '/teacher/materials', query: { course_id: course.id } })
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  return dateStr.slice(0, 10)
}
</script>

<template>
  <div class="courses-page">
    <div class="page-header">
      <h1>课程管理</h1>
      <el-button type="primary" round @click="openCreate">新建课程</el-button>
    </div>

    <el-table :data="myCourses" stripe style="width: 100%" v-loading="loading">
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

    <div v-if="!loading && myCourses.length === 0" class="empty-state">
      <p>暂无课程，请点击「新建课程」添加</p>
    </div>

    <div class="section-header public-section-header">
      <h2>公共课程</h2>
      <span>默认展示 {{ displayedPublicCourses.length }} 门，共 {{ publicCourses.length }} 门</span>
    </div>

    <el-table :data="displayedPublicCourses" stripe style="width: 100%" v-loading="loading">
      <el-table-column type="index" label="序号" width="70" align="center" />
      <el-table-column prop="name" label="课程名称" min-width="200">
        <template #default="{ row }">
          <span>{{ row.name }}</span>
          <el-tag class="public-tag" size="small" type="success" effect="plain">公共</el-tag>
        </template>
      </el-table-column>
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
          <el-button v-if="row.is_owner" text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.is_owner" type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="public-course-search">
      <el-input
        v-model="publicSearchKeyword"
        placeholder="搜索公共课程"
        clearable
        size="large"
      />
    </div>

    <div v-if="!loading && publicCourses.length === 0" class="empty-state public-empty">
      <p>暂无公共课程</p>
    </div>
    <div v-else-if="!loading && displayedPublicCourses.length === 0" class="empty-state public-empty">
      <p>没有匹配的公共课程</p>
    </div>

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
      <div class="form-group">
        <el-checkbox v-model="formData.is_public">设为公共课程</el-checkbox>
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
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
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

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: var(--space-2xl) 0 var(--space-md);
}

.section-header h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
}

.section-header span {
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

.public-tag {
  margin-left: var(--space-sm);
}

.public-course-search {
  max-width: 360px;
  margin-top: var(--space-xl);
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

.public-empty {
  margin-top: var(--space-md);
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

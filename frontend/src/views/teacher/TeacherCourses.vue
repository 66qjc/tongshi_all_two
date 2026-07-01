<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addPublicCourse,
  createCourse,
  deleteCourse,
  getCoursesPage,
  updateCourse,
  type Course,
} from '@/api/course'

const courses = ref<Course[]>([])
const pagedMyCourses = ref<Course[]>([])
const loading = ref(true)
const router = useRouter()
const mySearchKeyword = ref('')
const publicSearchKeyword = ref('')
const myPage = ref(1)
const myPageSize = ref(10)
const myTotal = ref(0)
const publicCourses = ref<Course[]>([])
const publicPage = ref(1)
const publicPageSize = ref(10)
const publicTotal = ref(0)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formData = reactive({
  name: '',
  description: '',
})
const saving = ref(false)

// 添加公共课程
const addDialogVisible = ref(false)
const addSearchKeyword = ref('')
const addDialogCourses = ref<Course[]>([])
const addDialogLoading = ref(false)
const addedCourseIds = ref<Set<number>>(new Set())
const addingCourseIds = ref<Set<number>>(new Set())

function isAlreadyOwned(course: Course) {
  return addedCourseIds.value.has(course.id)
}

const searchablePublicCourses = computed(() => {
  const keyword = addSearchKeyword.value.trim().toLowerCase()
  let list = addDialogCourses.value
  if (keyword) list = list.filter(c => c.name.toLowerCase().includes(keyword))
  return [...list].sort((a, b) => {
    const aAdded = isAlreadyOwned(a) ? 0 : 1
    const bAdded = isAlreadyOwned(b) ? 0 : 1
    return aAdded - bAdded
  })
})

async function handleAddOneCourse(course: Course) {
  if (isAlreadyOwned(course) || addingCourseIds.value.has(course.id)) return
  addingCourseIds.value = new Set([...addingCourseIds.value, course.id])
  try {
    await addPublicCourse(course.id)
    addedCourseIds.value = new Set([...addedCourseIds.value, course.id])
    await loadCourses()
    ElMessage.success('课程添加成功')
  } catch {
    ElMessage.error('添加失败，请稍后重试')
  } finally {
    const next = new Set(addingCourseIds.value)
    next.delete(course.id)
    addingCourseIds.value = next
  }
}

function openAddDialog() {
  addSearchKeyword.value = ''
  addedCourseIds.value = new Set()
  addDialogVisible.value = true
  loadAddDialogCourses()
}

async function loadAddDialogCourses() {
  addDialogLoading.value = true
  try {
    const result = await getCoursesPage({
      scope: 'public',
      page: 1,
      page_size: 200,
    })
    addDialogCourses.value = result.items
  } catch {
    // silent fallback — allow local filter over existing data
  } finally {
    addDialogLoading.value = false
  }
}

async function loadMyCourses() {
  const result = await getCoursesPage({
    keyword: mySearchKeyword.value || undefined,
    scope: 'owned',
    page: myPage.value,
    page_size: myPageSize.value,
  })
  pagedMyCourses.value = result.items
  myTotal.value = result.total
}

async function loadPublicCourses() {
  const result = await getCoursesPage({
    keyword: publicSearchKeyword.value || undefined,
    scope: 'public',
    page: publicPage.value,
    page_size: publicPageSize.value,
  })
  publicCourses.value = result.items
  publicTotal.value = result.total
}

async function loadCourses() {
  loading.value = true
  try {
    await Promise.all([loadMyCourses(), loadPublicCourses()])
  } catch {
    ElMessage.error('课程列表加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function handleMyPageChange(page: number) {
  myPage.value = page
  loadMyCourses()
}

function handleMySearch() {
  myPage.value = 1
  loadMyCourses()
}

function handlePublicPageChange(page: number) {
  publicPage.value = page
  loadPublicCourses()
}

function handlePublicPageSizeChange(size: number) {
  publicPage.value = 1
  publicPageSize.value = size
  loadPublicCourses()
}

function handlePublicSearch() {
  publicPage.value = 1
  loadPublicCourses()
}

onMounted(async () => {
  await loadCourses()
})

function openCreate() {
  isEdit.value = false
  editingId.value = null
  formData.name = ''
  formData.description = ''
  dialogVisible.value = true
}

function openEdit(course: Course) {
  if (!course.is_owner) {
    ElMessage.warning('只能编辑自己的课程')
    return
  }
  isEdit.value = true
  editingId.value = course.id
  formData.name = course.name
  formData.description = course.description || ''
  dialogVisible.value = true
}

function openCourseDetail(course: Course) {
  router.push(`/teacher/courses/${course.id}`)
}

async function handleSave() {
  const name = formData.name.trim()
    const description = formData.description.trim()
  if (!name) {
    ElMessage.warning('请输入课程名称')
    return
  }
  saving.value = true
  try {
    if (isEdit.value && editingId.value !== null) {
      await updateCourse(editingId.value, { name, description })
      ElMessage.success('课程更新成功')
    } else {
      await createCourse({ name, description })
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
  if (!course.is_owner) {
    ElMessage.warning('只能删除自己的课程')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除课程「${course.name}」？这只会删除你自己的课程副本，不会影响公共课程源内容。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
    await deleteCourse(course.id)
    ElMessage.success('已删除')
    await loadCourses()
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
      <h1>已添加课程</h1>
      <div class="header-actions">
        <el-button type="primary" round @click="openAddDialog">添加课程</el-button>
        <el-button type="primary" round @click="openCreate">新建课程</el-button>
      </div>
    </div>

    <div class="course-search-row">
      <el-input
        v-model="mySearchKeyword"
        placeholder="搜索已添加课程"
        clearable
        size="default"
        @keyup.enter="handleMySearch"
        @clear="handleMySearch"
      />
    </div>

    <el-table :data="pagedMyCourses" stripe style="width: 100%" v-loading="loading">
      <el-table-column type="index" label="序号" width="70" align="center" />
      <el-table-column prop="name" label="课程名称" min-width="200" />
      <el-table-column label="来源" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_public ? 'info' : 'success'" size="small" effect="plain">
            {{ row.is_public ? '公共' : '私有' }}
          </el-tag>
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
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openCourseDetail(row)">管理课程</el-button>
          <el-button text size="small" @click="openMaterials(row)">查看资料</el-button>
          <el-button text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && pagedMyCourses.length === 0" class="empty-state">
      <p>暂无课程，请点击「新建课程」添加</p>
    </div>

    <div v-if="myTotal > myPageSize" class="pagination-wrap">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="myTotal"
        :page-size="myPageSize"
        :current-page="myPage"
        @current-change="handleMyPageChange"
      />
    </div>

    <div class="section-header public-section-header">
      <h2>公共课程 <span class="public-count">共 {{ publicTotal }} 门</span></h2>
      <div class="public-course-search">
        <el-input
          v-model="publicSearchKeyword"
          placeholder="搜索公共课程"
          clearable
          size="default"
          @keyup.enter="handlePublicSearch"
          @clear="handlePublicSearch"
        />
      </div>
    </div>

    <el-table :data="publicCourses" stripe style="width: 100%" max-height="240" v-loading="loading">
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
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openMaterials(row)">查看资料</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="publicTotal > publicPageSize" class="pagination-wrap">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next"
        :total="publicTotal"
        :page-size="publicPageSize"
        :current-page="publicPage"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePublicPageChange"
        @size-change="handlePublicPageSizeChange"
      />
    </div>

    <div v-if="!loading && publicTotal === 0" class="empty-state public-empty">
      <p>暂无公共课程</p>
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
        <label>课程简介</label>
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="请输入课程简介（可选）"
          size="large"
          maxlength="500"
          show-word-limit
        />
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEdit ? '保存修改' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加公共课程弹窗 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加公共课程"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="addSearchKeyword"
        placeholder="搜索课程名称"
        size="large"
        clearable
        style="margin-bottom: var(--space-md)"
      />
      <el-table :data="searchablePublicCourses" stripe style="width: 100%" max-height="360">
        <el-table-column prop="name" label="课程名称" min-width="200">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <el-tag class="public-tag" size="small" type="success" effect="plain">公共</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资料" width="70" align="center">
          <template #default="{ row }">
            {{ row.material_count ?? 0 }}
          </template>
        </el-table-column>
        <el-table-column label="题目" width="70" align="center">
          <template #default="{ row }">
            {{ row.question_count ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button
              v-if="!isAlreadyOwned(row)"
              type="primary"
              size="small"
              :loading="addingCourseIds.has(row.id)"
              @click="handleAddOneCourse(row)"
            >添加</el-button>
            <el-tag v-else size="small" type="info">已添加</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="searchablePublicCourses.length === 0" class="empty-state" style="margin-top: var(--space-md)">
        暂无可用公共课程
      </div>
      <template #footer>
        <el-button @click="addDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.courses-page {
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
}

.header-actions {
  display: flex;
  gap: var(--space-sm);
}

.course-search-row {
  max-width: 360px;
  margin-bottom: var(--space-md);
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
}

.count-badge {
  font-weight: 700;
  color: var(--color-primary);
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

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: var(--space-lg) 0;
}

.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.public-empty {
  margin-top: var(--space-md);
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

.required {
  color: #e74c3c;
  margin-left: 2px;
}
</style>

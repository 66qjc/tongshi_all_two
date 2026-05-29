<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createAnnouncement, deleteAnnouncement, getAnnouncements, type Announcement } from '@/api/announcement'
import { getClasses, type ClassInfo } from '@/api/class'
import { getCourses, type Course } from '@/api/course'
import { getQuestions, type Question } from '@/api/question'

const router = useRouter()
const announcements = ref<Announcement[]>([])
const courses = ref<Course[]>([])
const classes = ref<ClassInfo[]>([])
const questions = ref<Question[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const questionDialogVisible = ref(false)
const questionLoading = ref(false)
const selectedQuestionIds = ref<number[]>([])

const form = reactive({
  course_id: '' as number | '',
  class_ids: [] as number[],
  title: '',
  question_ids: [] as number[],
  start_time: '',
  end_time: '',
})

const targetClasses = computed(() => {
  if (typeof form.course_id !== 'number') return []
  return classes.value.filter(item => item.course_id === form.course_id)
})

async function loadBase() {
  const [list, courseList, classList] = await Promise.all([getAnnouncements(), getCourses(), getClasses()])
  announcements.value = list
  courses.value = courseList
  classes.value = classList
}

async function loadQuestions() {
  if (typeof form.course_id !== 'number') {
    questions.value = []
    return
  }
  questionLoading.value = true
  try {
    questions.value = await getQuestions({ course_id: form.course_id })
  } catch {
    ElMessage.error('题目加载失败')
  } finally {
    questionLoading.value = false
  }
}

function openCreate() {
  Object.assign(form, {
    course_id: courses.value[0]?.id || '',
    class_ids: [],
    title: '',
    question_ids: [],
    start_time: '',
    end_time: '',
  })
  dialogVisible.value = true
  loadQuestions()
}

function openQuestionPicker() {
  if (typeof form.course_id !== 'number') {
    ElMessage.warning('请先选择课程')
    return
  }
  selectedQuestionIds.value = [...form.question_ids]
  questionDialogVisible.value = true
  loadQuestions()
}

function handleQuestionSelection(rows: Question[]) {
  selectedQuestionIds.value = rows.map(item => item.id)
}

function confirmQuestions() {
  form.question_ids = [...selectedQuestionIds.value]
  questionDialogVisible.value = false
}

async function handleCreate() {
  if (typeof form.course_id !== 'number') {
    ElMessage.warning('请选择所属课程')
    return
  }
  if (form.class_ids.length === 0) {
    ElMessage.warning('请选择目标班级')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (form.question_ids.length === 0) {
    ElMessage.warning('请选择题目')
    return
  }

  try {
    await createAnnouncement({
      course_id: form.course_id,
      class_ids: form.class_ids,
      title: form.title.trim(),
      question_ids: form.question_ids,
      start_time: form.start_time || undefined,
      end_time: form.end_time || undefined,
    })
    ElMessage.success('发布成功')
    dialogVisible.value = false
    announcements.value = await getAnnouncements()
  } catch {
    ElMessage.error('发布失败，请确认班级和题目属于同一课程')
  }
}

async function handleDelete(row: Announcement) {
  try {
    await ElMessageBox.confirm('确定删除该发布题目？删除后学生将无法继续查看或完成。', '删除确认', { type: 'warning' })
    await deleteAnnouncement(row.id)
    announcements.value = announcements.value.filter(item => item.id !== row.id)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('删除失败，请稍后重试')
  }
}

function openReport(row: Announcement) {
  router.push({ path: '/teacher/grades', query: { tab: 'tasks', task_id: row.id } })
}

watch(() => form.course_id, () => {
  form.class_ids = []
  form.question_ids = []
  loadQuestions()
})

onMounted(async () => {
  try {
    await loadBase()
  } catch {
    ElMessage.error('发布题目数据加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="publish-page">
    <div class="page-header">
      <h1>发布题目</h1>
      <el-button type="primary" round @click="openCreate">发布题目</el-button>
    </div>

    <el-table :data="announcements" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column prop="course_name" label="所属课程" min-width="160" />
      <el-table-column label="目标班级" min-width="220">
        <template #default="{ row }">
          {{ row.class_names?.join('、') || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="题目数" width="90" align="center">
        <template #default="{ row }">{{ row.question_ids?.length || 0 }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="发布时间" width="160">
        <template #default="{ row }">{{ row.created_at ? row.created_at.slice(0, 16).replace('T', ' ') : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <el-button text size="small" @click="openReport(row)">查看情况</el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && announcements.length === 0" class="empty-state">
      暂无发布记录
    </div>

    <el-dialog v-model="dialogVisible" title="发布题目" width="600px">
      <div class="form-group">
        <label>所属课程</label>
        <el-select v-model="form.course_id" placeholder="选择课程" size="large" style="width: 100%">
          <el-option v-for="course in courses" :key="course.id" :label="course.name" :value="course.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>目标班级</label>
        <el-select v-model="form.class_ids" multiple placeholder="选择班级" size="large" style="width: 100%">
          <el-option v-for="item in targetClasses" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </div>
      <div class="form-group">
        <label>标题</label>
        <el-input v-model="form.title" placeholder="输入发布标题" size="large" />
      </div>
      <div class="form-group">
        <label>题目</label>
        <div class="question-row">
          <span>已选 {{ form.question_ids.length }} 道题</span>
          <el-button plain type="primary" @click="openQuestionPicker">选择题目</el-button>
        </div>
      </div>
      <div class="time-row">
        <div class="form-group">
          <label>开始时间</label>
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="不限" size="large" style="width: 100%" value-format="YYYY-MM-DD HH:mm:ss" />
        </div>
        <div class="form-group">
          <label>截止时间</label>
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="不限" size="large" style="width: 100%" value-format="YYYY-MM-DD HH:mm:ss" />
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">发布</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="questionDialogVisible" title="选择题目" width="760px" append-to-body>
      <el-table
        :data="questions"
        row-key="id"
        style="width: 100%"
        v-loading="questionLoading"
        @selection-change="handleQuestionSelection"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column label="题干" min-width="300">
          <template #default="{ row }">{{ row.stem.length > 52 ? row.stem.slice(0, 52) + '…' : row.stem }}</template>
        </el-table-column>
        <el-table-column label="题型" width="100">
          <template #default="{ row }">{{ row.type === 'choice' ? '选择题' : '填空题' }}</template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="questionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmQuestions">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-header,
.question-row,
.time-row {
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

.empty-state {
  padding: var(--space-3xl) 0;
  text-align: center;
  color: var(--color-text-muted);
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

.question-row {
  justify-content: space-between;
  color: var(--color-text-muted);
}

.time-row > .form-group {
  flex: 1;
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCourses, type Course } from '@/api/course'
import { getAnnouncements, type Announcement } from '@/api/announcement'

const route = useRoute()
const router = useRouter()
const courses = ref<Course[]>([])
const announcements = ref<Announcement[]>([])
const loading = ref(true)
const selectedCourseId = ref<number | ''>('')
const statusFilter = ref<'all' | 'completed' | 'pending'>('all')
const titleKeyword = ref('')

async function loadData() {
  loading.value = true
  try {
    const [c, a] = await Promise.all([getCourses(), getAnnouncements()])
    courses.value = c
    announcements.value = a
    const preSelect = Number(route.query.course_id)
    if (preSelect) selectedCourseId.value = preSelect
    const preStatus = route.query.status as string | undefined
    if (preStatus === 'completed' || preStatus === 'pending') statusFilter.value = preStatus
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const enrolledCourses = computed(() => courses.value.filter(c => !c.is_public))

// 课程名映射
const courseNameMap = computed(() => {
  const m = new Map<number, string>()
  for (const c of courses.value) m.set(c.id, c.name)
  return m
})

// 扁平化作业列表
const flatAssignments = computed(() => {
  let list = announcements.value
  if (selectedCourseId.value) {
    list = list.filter(a => a.course_id === selectedCourseId.value)
  }
  return list.map((a, i) => ({
    ...a,
    _idx: i + 1,
    _courseName: courseNameMap.value.get(a.course_id) ?? a.course_name,
    _status: getStatus(a),
  }))
})

// 作业名称 + 状态筛选 + 排序
const filteredAssignments = computed(() => {
  let list = flatAssignments.value
  // 作业名称筛选
  const kw = titleKeyword.value.trim().toLowerCase()
  if (kw) list = list.filter(a => a.title.toLowerCase().includes(kw))
  // 状态筛选
  if (statusFilter.value === 'completed') {
    list = list.filter(a => a.is_completed)
  } else if (statusFilter.value === 'pending') {
    list = list.filter(a => !a.is_completed)
  }
  // 未完成排序：有截止时间按截止时间（越近越前），无截止时间按发布时间（越新越前）
  const pending = list.filter(a => !a.is_completed).sort((a, b) => {
    const aHasDeadline = !!a.end_time
    const bHasDeadline = !!b.end_time
    if (aHasDeadline && bHasDeadline) {
      return new Date(a.end_time!).getTime() - new Date(b.end_time!).getTime()
    }
    if (aHasDeadline) return -1  // 有截止时间的优先
    if (bHasDeadline) return 1
    // 都没有截止时间，按发布时间排序（越新越靠前）
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
  const completed = list.filter(a => a.is_completed)
  return [...pending, ...completed].map((a, i) => ({ ...a, _idx: i + 1 }))
})

function getStatus(item: Announcement): { text: string; cls: string } {
  if (item.is_completed) return { text: '已完成', cls: 'done' }
  if (item.end_time && new Date(item.end_time) < new Date()) return { text: '已过期', cls: 'expired' }
  return { text: '未完成', cls: 'pending' }
}

function goToQuiz(item: Announcement) {
  if (item.question_ids.length === 0) return
  router.push(`/practice/quiz/${item.course_id}?question_ids=${item.question_ids.join(',')}&announcement_id=${item.id}`)
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-'
  return dateStr.slice(0, 16).replace('T', ' ')
}
</script>

<template>
  <div class="assignments-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <img
              src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png"
              alt="AI 通识课平台标识"
              width="40"
              height="40"
              class="hero-icon-image"
            />
          </div>
          <h1>选择作业</h1>
          <p>选择题库作业，即时作答查看解析。</p>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="container">
        <button class="back-btn" @click="router.push('/practice')">← 返回练习首页</button>

        <div class="filter-bar">
          <el-select v-model="selectedCourseId" placeholder="全部课程" clearable size="default" style="width: 200px">
            <el-option v-for="c in enrolledCourses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select v-model="statusFilter" size="default" style="width: 140px">
            <el-option label="全部状态" value="all" />
            <el-option label="未完成" value="pending" />
            <el-option label="已完成" value="completed" />
          </el-select>
          <el-input v-model="titleKeyword" placeholder="搜索作业名称" clearable size="default" style="width: 200px" />
        </div>

        <div v-if="loading" class="empty-state">加载中...</div>

        <template v-else>
          <el-table :data="filteredAssignments" stripe style="width: 100%" v-loading="false">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="_courseName" label="课程名称" min-width="140" />
            <el-table-column prop="title" label="作业名称" min-width="160" />
            <el-table-column label="开始时间" width="140">
              <template #default="{ row }">{{ formatDate(row.start_time) }}</template>
            </el-table-column>
            <el-table-column label="截止时间" width="140">
              <template #default="{ row }">{{ formatDate(row.end_time) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <span class="status-tag" :class="row._status.cls">{{ row._status.text }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <button
                  v-if="!row.is_completed && !(row.end_time && new Date(row.end_time) < new Date())"
                  class="go-btn"
                  @click="goToQuiz(row)"
                >去练习</button>
                <span v-else class="disabled-text">-</span>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="filteredAssignments.length === 0" class="empty-state">
            暂无作业，请等待教师发布。
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.assignments-page { padding-top: 60px; }

.page-hero {
  padding: var(--space-3xl) 0 var(--space-2xl);
  background: var(--color-practice-bg);
  border-bottom: 1px solid var(--color-border-light);
}
.hero-inner { text-align: center; }
.hero-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 56px; height: 56px;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
  box-shadow: 0 4px 14px rgba(0,0,0,0.15);
}
.hero-icon-image {
  display: block;
  width: 40px;
  height: 40px;
  object-fit: contain;
}
.hero-inner h1 {
  font-family: var(--font-serif); font-size: 1.8rem; font-weight: 900;
  color: var(--color-text); margin-bottom: var(--space-sm); letter-spacing: 0.05em;
}
.hero-inner p { font-size: 0.92rem; color: var(--color-text-secondary); }

.content-section { padding: var(--space-2xl) 0 var(--space-3xl); max-width: 1000px; margin: 0 auto; }

.back-btn {
  display: inline-block; font-size: 0.85rem;
  color: var(--color-practice); font-weight: 600; margin-bottom: var(--space-lg);
}

.filter-bar { display: flex; gap: var(--space-md); margin-bottom: var(--space-lg); }

.status-tag {
  font-size: 0.75rem; font-weight: 600;
  padding: 2px 10px; border-radius: var(--radius-full);
}
.status-tag.done { color: #10b981; background: rgba(16,185,129,0.1); }
.status-tag.pending { color: #f59e0b; background: rgba(245,158,11,0.1); }
.status-tag.expired { color: #ef4444; background: rgba(239,68,68,0.1); }

.go-btn {
  padding: 4px 16px; font-size: 0.8rem; font-weight: 600; color: white;
  background: var(--color-practice); border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}
.go-btn:hover { opacity: 0.9; }

.disabled-text { color: var(--color-text-muted); font-size: 0.8rem; }

.empty-state { text-align: center; padding: var(--space-4xl) 0; color: var(--color-text-muted); font-size: 0.9rem; }
</style>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTeacherStats } from '@/api/teacher'
import { getAllProjects } from '@/api/teacher'
import { getTaskOverview, type TaskOverview } from '@/api/announcement'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// ── 状态 ──
const loading = ref(true)
const statsLoading = ref(true)
const tasksLoading = ref(true)
const reviewsLoading = ref(true)

const teacherName = authStore.user?.name || '教师'

const stats = ref([
  { label: '总学生数', value: 0, icon: 'students', tone: 'learn' },
  { label: '我的课程', value: 0, icon: 'courses', tone: 'primary' },
  { label: '待审作品', value: 0, icon: 'reviews', tone: 'create' },
  { label: '累计练习', value: 0, icon: 'practice', tone: 'act' },
])

const recentTasks = ref<TaskOverview['tasks']>([])
const pendingProjects = ref<{ id: number; title: string; author_name: string; date: string }[]>([])

// ── 数据加载 ──
onMounted(async () => {
  // 统计数据
  try {
    const data = await getTeacherStats()
    stats.value = [
      { label: '总学生数', value: data.total_students, icon: 'students', tone: 'learn' },
      { label: '我的课程', value: data.my_courses, icon: 'courses', tone: 'primary' },
      { label: '待审作品', value: data.pending_reviews, icon: 'reviews', tone: 'create' },
      { label: '累计练习', value: data.weekly_exercises, icon: 'practice', tone: 'act' },
    ]
  } catch {
    ElMessage.error('统计数据加载失败')
  } finally {
    statsLoading.value = false
  }

  // 近期作业
  try {
    const overview = await getTaskOverview()
    // 按创建时间倒序取前 5 条
    recentTasks.value = overview.tasks
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5)
  } catch {
    // 静默处理，不影响页面其他功能
  } finally {
    tasksLoading.value = false
  }

  // 待审作品
  try {
    const result = await getAllProjects('pending', undefined, 1, 5)
    pendingProjects.value = result.items.map(p => ({
      id: p.id,
      title: p.title,
      author_name: p.author_name,
      date: p.date,
    }))
  } catch {
    // 静默处理
  } finally {
    reviewsLoading.value = false
  }

  loading.value = false
})

// ── 快捷操作 ──
const quickActions = [
  { label: '发布作业', desc: '选题、设时间、发到班级', path: '/teacher/publish', icon: 'publish' },
  { label: '上传资料', desc: '视频课件或 PDF 讲义', path: '/teacher/materials', icon: 'upload' },
  { label: '管理题库', desc: '新增、编辑或导入题目', path: '/teacher/questions', icon: 'questions' },
  { label: '审核作品', desc: '查看并审核学生提交的作品', path: '/teacher/reviews', icon: 'reviews' },
  { label: '学生成绩', desc: '查看完成率、导出成绩单', path: '/teacher/grades', icon: 'grades' },
]

// ── 工具函数 ──
function formatProgress(completed: number, total: number): number {
  if (total === 0) return 0
  return Math.round((completed / total) * 100)
}

function formatDateShort(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<template>
  <div class="dashboard">
    <!-- 欢迎区域 -->
    <div class="welcome-row">
      <div>
        <h1 class="page-title">欢迎回来，{{ teacherName }}</h1>
        <p class="page-subtitle">这里是你的教学概览，快速了解当前状态。</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div v-for="stat in stats" :key="stat.label" class="stat-card" :class="`tone-${stat.tone}`">
        <div class="stat-icon-wrap">
          <!-- 内联 SVG 图标 -->
          <svg v-if="stat.icon === 'students'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          <svg v-else-if="stat.icon === 'courses'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          <svg v-else-if="stat.icon === 'reviews'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="stat-body">
          <div v-if="statsLoading" class="stat-skeleton">
            <span class="skel-value"></span>
          </div>
          <div v-else class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- 双栏面板：近期作业 + 待审作品 -->
    <div class="panels-row">
      <!-- 近期作业 -->
      <div class="panel">
        <div class="panel-header">
          <h2 class="panel-title">近期作业</h2>
          <button class="panel-link" @click="router.push('/teacher/task-report')">查看全部</button>
        </div>
        <div v-if="tasksLoading" class="panel-loading">
          <div v-for="i in 4" :key="i" class="skel-row"></div>
        </div>
        <div v-else-if="recentTasks.length === 0" class="panel-empty">
          <p>暂无已发布的作业</p>
        </div>
        <div v-else class="task-list">
          <div
            v-for="task in recentTasks"
            :key="task.id"
            class="task-item"
            @click="router.push(`/teacher/task-report/${task.id}`)"
          >
            <div class="task-top">
              <span class="task-title">{{ task.title }}</span>
              <span class="task-date">{{ formatDateShort(task.created_at) }}</span>
            </div>
            <div class="task-meta">
              <span class="task-course">{{ task.course_name }}</span>
              <span v-if="task.is_expired" class="task-expired">已截止</span>
            </div>
            <div class="task-progress-row">
              <div class="task-progress-bar">
                <div
                  class="task-progress-fill"
                  :style="{ width: formatProgress(task.completed_count, task.total_students) + '%' }"
                  :class="{ 'is-full': task.completed_count === task.total_students && task.total_students > 0 }"
                ></div>
              </div>
              <span class="task-progress-text">
                {{ task.completed_count }}/{{ task.total_students }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 待审作品 -->
      <div class="panel">
        <div class="panel-header">
          <h2 class="panel-title">待审作品</h2>
          <button class="panel-link" @click="router.push('/teacher/reviews')">全部作品</button>
        </div>
        <div v-if="reviewsLoading" class="panel-loading">
          <div v-for="i in 4" :key="i" class="skel-row"></div>
        </div>
        <div v-else-if="pendingProjects.length === 0" class="panel-empty">
          <p>暂无待审核作品</p>
        </div>
        <div v-else class="review-list">
          <div
            v-for="project in pendingProjects"
            :key="project.id"
            class="review-item"
            @click="router.push('/teacher/reviews')"
          >
            <div class="review-top">
              <span class="review-title">{{ project.title }}</span>
              <span class="review-date">{{ formatDateShort(project.date) }}</span>
            </div>
            <div class="review-meta">
              <span class="review-author">{{ project.author_name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <h2 class="section-title">快捷操作</h2>
    <div class="actions-grid">
      <button
        v-for="action in quickActions"
        :key="action.label"
        class="action-card"
        @click="router.push(action.path)"
      >
        <div class="action-icon-wrap">
          <svg v-if="action.icon === 'publish'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          <svg v-else-if="action.icon === 'upload'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <svg v-else-if="action.icon === 'questions'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          <svg v-else-if="action.icon === 'reviews'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        </div>
        <div class="action-body">
          <h3>{{ action.label }}</h3>
          <p>{{ action.desc }}</p>
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* ── 欢迎区域 ── */
.welcome-row {
  margin-bottom: var(--space-xl);
}

.page-title {
  font-size: 1.5rem;
  font-weight: 800;
  font-family: var(--font-serif);
  color: var(--color-text);
  margin-bottom: 2px;
}

.page-subtitle {
  font-size: 0.88rem;
  color: var(--color-text-muted);
}

/* ── 统计卡片 ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-2xl);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
  transition: all var(--duration-fast) var(--ease-out);
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.stat-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.stat-icon-wrap svg {
  width: 20px;
  height: 20px;
}

.tone-learn .stat-icon-wrap {
  background: var(--color-learn-bg);
  color: var(--color-learn);
}
.tone-primary .stat-icon-wrap {
  background: var(--color-primary-glow);
  color: var(--color-primary);
}
.tone-create .stat-icon-wrap {
  background: var(--color-create-bg);
  color: var(--color-create);
}
.tone-act .stat-icon-wrap {
  background: var(--color-act-bg);
  color: var(--color-act);
}

.stat-body {
  min-width: 0;
}

.stat-value {
  font-size: 1.6rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--color-text);
  line-height: 1.2;
}

.stat-label {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin-top: 1px;
}

/* 骨架屏 */
.stat-skeleton {
  height: 1.6rem;
  display: flex;
  align-items: center;
}

.skel-value {
  display: block;
  width: 40px;
  height: 1.2rem;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, var(--color-border-light) 25%, var(--color-bg-alt) 50%, var(--color-border-light) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── 双栏面板 ── */
.panels-row {
  display: grid;
  grid-template-columns: 1.4fr 0.6fr;
  gap: var(--space-lg);
  margin-bottom: var(--space-2xl);
}

.panel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  min-height: 260px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
}

.panel-title {
  font-size: 1rem;
  font-weight: 700;
  font-family: var(--font-serif);
  color: var(--color-text);
}

.panel-link {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  transition: color var(--duration-fast);
  padding: 2px 0;
}

.panel-link:hover {
  color: var(--color-primary-light);
}

.panel-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  color: var(--color-text-muted);
  font-size: 0.88rem;
}

.panel-loading {
  display: grid;
  gap: var(--space-md);
}

.skel-row {
  height: 56px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, var(--color-border-light) 25%, var(--color-bg-alt) 50%, var(--color-border-light) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

/* ── 近期作业列表 ── */
.task-list {
  display: grid;
  gap: var(--space-sm);
}

.task-item {
  padding: var(--space-md);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.task-item:hover {
  border-color: var(--color-primary-light);
  background: var(--color-primary-glow);
}

.task-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: 2px;
}

.task-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.task-date {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.task-course {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.task-expired {
  font-size: 0.68rem;
  font-weight: 600;
  color: #dc2626;
  background: rgba(220, 38, 38, 0.08);
  padding: 0 6px;
  border-radius: var(--radius-full);
}

.task-progress-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.task-progress-bar {
  flex: 1;
  height: 6px;
  background: var(--color-border-light);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.task-progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width 0.6s var(--ease-out);
}

.task-progress-fill.is-full {
  background: var(--color-act);
}

.task-progress-text {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  white-space: nowrap;
  min-width: 36px;
  text-align: right;
}

/* ── 待审作品列表 ── */
.review-list {
  display: grid;
  gap: var(--space-sm);
}

.review-item {
  padding: var(--space-md);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.review-item:hover {
  border-color: var(--color-create-light);
  background: var(--color-create-bg);
}

.review-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-bottom: 2px;
}

.review-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.review-date {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.review-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.review-author {
  font-size: 0.78rem;
  color: var(--color-text-secondary);
}

/* ── 快捷操作 ── */
.section-title {
  font-size: 1.05rem;
  font-weight: 700;
  font-family: var(--font-serif);
  color: var(--color-text);
  margin-bottom: var(--space-lg);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-md);
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  text-align: left;
  transition: all var(--duration-normal) var(--ease-out);
}

.action-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--color-primary-light);
}

.action-card:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

.action-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-primary-glow);
  color: var(--color-primary);
}

.action-icon-wrap svg {
  width: 18px;
  height: 18px;
}

.action-body h3 {
  font-size: 0.92rem;
  font-weight: 700;
  font-family: var(--font-serif);
  color: var(--color-text);
  margin-bottom: 2px;
}

.action-body p {
  font-size: 0.78rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

/* ── 响应式 ── */
@media (max-width: 1024px) {
  .actions-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .panels-row {
    grid-template-columns: 1fr;
  }

  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .actions-grid {
    grid-template-columns: 1fr;
  }
}
</style>

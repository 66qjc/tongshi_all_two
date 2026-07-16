<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getAnnouncements,
  markAsRead,
  recordCompletion,
  type Announcement,
} from '@/api/announcement'
import {
  getNotificationPreferences,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  updateNotificationPreferences,
  type NotificationPreferences,
  type StudentNotification,
} from '@/api/notification'
import { emitMessageRefresh, onMessageRefresh } from '@/utils/messageRefresh'

const router = useRouter()
const route = useRoute()
const announcements = ref<Announcement[]>([])
const notifications = ref<StudentNotification[]>([])
const loading = ref(true)
const notificationLoading = ref(false)
const activeCategory = ref('all')
const unreadOnly = ref(false)
const preferenceVisible = ref(false)
let messageTimer: number | undefined
let stopMessageRefresh: (() => void) | undefined
const preferences = reactive({
  enable_assignment_due: true,
  enable_grade_published: true,
  enable_course_update: true,
  enable_project_review: true,
})

const categoryOptions = [
  { label: '全部通知', value: 'all' },
  { label: '作业提醒', value: 'assignment' },
  { label: '成绩通知', value: 'grade' },
  { label: '课程更新', value: 'course' },
  { label: '作品审核', value: 'project' },
  { label: '系统通知', value: 'system' },
]

const categoryLabelMap: Record<string, string> = {
  assignment: '作业',
  grade: '成绩',
  course: '课程',
  project: '作品',
  system: '系统',
}

interface InboxItem {
  key: string
  source: 'announcement' | 'notification'
  id: number
  title: string
  content: string
  category: string
  categoryLabel: string
  isRead: boolean
  createdAt: string
  teacherName?: string
  courseName?: string
  classNames?: string[]
  questionCount?: number
  startTime?: string | null
  endTime?: string | null
  actionUrl?: string
  priority?: string
  rawAnnouncement?: Announcement
  rawNotification?: StudentNotification
}

const allItems = computed<InboxItem[]>(() => {
  const announcementItems = announcements.value.map(item => ({
    key: `announcement-${item.id}`,
    source: 'announcement' as const,
    id: item.id,
    title: item.title,
    content: item.content || '',
    category: 'assignment',
    categoryLabel: '作业',
    isRead: item.is_read,
    createdAt: item.created_at,
    teacherName: item.teacher_name,
    courseName: item.course_name,
    classNames: item.class_names,
    questionCount: item.question_ids.length,
    startTime: item.start_time,
    endTime: item.end_time,
    rawAnnouncement: item,
  }))

  const notificationItems = notifications.value.map(item => ({
    key: `notification-${item.id}`,
    source: 'notification' as const,
    id: item.id,
    title: item.title,
    content: item.content || '',
    category: item.category || 'system',
    categoryLabel: categoryLabelMap[item.category || 'system'] || '通知',
    isRead: item.is_read,
    createdAt: item.created_at,
    actionUrl: item.action_url,
    priority: item.priority,
    rawNotification: item,
  }))

  return [...announcementItems, ...notificationItems]
    .filter(item => activeCategory.value === 'all' || item.category === activeCategory.value)
    .filter(item => !unreadOnly.value || !item.isRead)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
})

onMounted(async () => {
  await Promise.all([loadMessages(true), loadPreferences()])
  preferenceVisible.value = route.path === '/student/settings/notifications'
  messageTimer = window.setInterval(loadMessages, 15_000)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  stopMessageRefresh = onMessageRefresh(loadMessages)
})

onBeforeUnmount(() => {
  if (messageTimer !== undefined) window.clearInterval(messageTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  stopMessageRefresh?.()
})

async function loadMessages(showInitialLoading = false) {
  if (showInitialLoading) loading.value = true
  try {
    await Promise.all([loadAnnouncements(), loadNotifications()])
  } finally {
    if (showInitialLoading) loading.value = false
  }
}

function handleVisibilityChange() {
  if (!document.hidden) void loadMessages()
}

async function loadAnnouncements() {
  announcements.value = await getAnnouncements()
}

async function loadNotifications(showLoading = false) {
  if (showLoading) notificationLoading.value = true
  try {
    notifications.value = await getNotifications({
      category: activeCategory.value !== 'all' && activeCategory.value !== 'assignment' ? activeCategory.value : undefined,
      unread_only: unreadOnly.value || undefined,
    })
  } catch {
    ElMessage.error('通知列表加载失败')
  } finally {
    if (showLoading) notificationLoading.value = false
  }
}

async function loadPreferences() {
  try {
    const result = await getNotificationPreferences()
    applyPreferences(result)
  } catch {
    // 偏好加载失败不影响消息列表阅读。
  }
}

function applyPreferences(result: NotificationPreferences) {
  preferences.enable_assignment_due = result.enable_assignment_due
  preferences.enable_grade_published = result.enable_grade_published
  preferences.enable_course_update = result.enable_course_update
  preferences.enable_project_review = result.enable_project_review
}

async function handleFilterChange() {
  await loadNotifications(true)
}

async function handleRead(item: InboxItem) {
  if (item.source === 'announcement' && item.rawAnnouncement) {
    if (item.rawAnnouncement.is_read) return
    try {
      await markAsRead(item.rawAnnouncement.id)
      item.rawAnnouncement.is_read = true
      emitMessageRefresh()
    } catch {
      ElMessage.error('通知标记已读失败，请稍后重试')
    }
    return
  }

  if (item.source === 'notification' && item.rawNotification) {
    if (!item.rawNotification.is_read) {
      try {
        await markNotificationRead(item.rawNotification.id)
        item.rawNotification.is_read = true
        emitMessageRefresh()
      } catch {
        ElMessage.error('通知标记已读失败，请稍后重试')
        return
      }
    }
    if (item.actionUrl) {
      await router.push(item.actionUrl)
    }
  }
}

async function handleMarkAllRead() {
  try {
    const unreadAnnouncements = announcements.value.filter(item => !item.is_read)
    await Promise.all(unreadAnnouncements.map(item => markAsRead(item.id)))
    await markAllNotificationsRead()
    unreadAnnouncements.forEach(item => { item.is_read = true })
    notifications.value.forEach(item => { item.is_read = true })
    emitMessageRefresh()
    ElMessage.success('已全部标记为已读')
  } catch {
    ElMessage.error('全部已读操作失败，请稍后重试')
  }
}

async function savePreferences() {
  try {
    const result = await updateNotificationPreferences({ ...preferences })
    applyPreferences(result)
    ElMessage.success('通知偏好已保存')
    preferenceVisible.value = false
  } catch {
    ElMessage.error('通知偏好保存失败')
  }
}

async function handleComplete(item: InboxItem) {
  const announcement = item.rawAnnouncement
  if (!announcement) return
  if (isExpired(item)) {
    ElMessage.warning('该作业已截止，无法标记完成')
    return
  }
  try {
    await recordCompletion(announcement.id)
    ElMessage.success('已标记完成')
    await loadAnnouncements()
    emitMessageRefresh()
  } catch {
    ElMessage.error('操作失败')
  }
}

function isExpired(item: InboxItem) {
  if (!item.endTime) return false
  return new Date(item.endTime) < new Date()
}

/** 判断任务是否尚未开始 */
function isNotStarted(item: InboxItem) {
  if (!item.startTime) return false
  return new Date(item.startTime) > new Date()
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <div class="inbox-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
              <path d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1>通知中心</h1>
          <p>集中查看老师发布的作业，以及课程更新、成绩发布和作品审核通知。</p>
        </div>
      </div>
    </section>

    <section class="inbox-section">
      <div class="container">
        <div class="toolbar-card">
          <div class="filter-row">
            <el-segmented
              v-model="activeCategory"
              class="category-segmented"
              :options="categoryOptions"
              @change="handleFilterChange"
            />
            <div class="toolbar-actions">
              <el-checkbox v-model="unreadOnly" @change="handleFilterChange">只看未读</el-checkbox>
              <el-button plain @click="preferenceVisible = true">通知偏好</el-button>
              <el-button type="primary" plain @click="handleMarkAllRead">全部已读</el-button>
            </div>
          </div>
        </div>

        <div v-if="loading" class="loading-state">加载中...</div>

        <div v-else-if="allItems.length === 0" class="empty-state">
          <p>暂无消息通知</p>
        </div>

        <div v-else v-loading="notificationLoading" class="inbox-list">
          <div
            v-for="item in allItems"
            :key="item.key"
            class="inbox-item"
            :class="{
              unread: !item.isRead,
              'expired-card': isExpired(item),
              'not-started-card': isNotStarted(item),
            }"
            @click="handleRead(item)"
          >
            <div class="item-dot" v-if="!item.isRead"></div>
            <div class="item-content">
              <div class="item-header">
                <span class="item-title">{{ item.title }}</span>
                <el-tag
                  :type="item.priority === 'high' ? 'danger' : item.source === 'announcement' ? 'success' : 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ item.categoryLabel }}
                </el-tag>
              </div>
              <div class="item-meta">
                <template v-if="item.source === 'announcement'">
                  <span>{{ item.teacherName }}</span>
                  <span class="meta-sep">·</span>
                  <span>{{ item.classNames?.join('、') || item.courseName }}</span>
                  <span class="meta-sep">·</span>
                </template>
                <span>{{ formatDate(item.createdAt) }}</span>
              </div>
              <p v-if="item.content" class="item-content-text">{{ item.content }}</p>
              <div v-if="item.questionCount && item.questionCount > 0" class="item-quiz">
                <span>包含 {{ item.questionCount }} 道题目</span>
                <router-link
                  v-if="!isExpired(item) && !isNotStarted(item)"
                  :to="`/practice/announcement/${item.id}`"
                  class="quiz-link"
                >去练习</router-link>
                <span v-else class="quiz-link-disabled">{{ isExpired(item) ? '已截止' : '未开始' }}</span>
              </div>
              <div class="item-time">
                <span v-if="item.startTime && isNotStarted(item)" class="not-started">
                  未开始: {{ formatDate(item.startTime) }}
                </span>
                <span v-if="item.endTime" :class="{ expired: isExpired(item) }">
                  {{ isExpired(item) ? '已截止' : '截止' }}: {{ formatDate(item.endTime) }}
                </span>
              </div>
              <div v-if="item.source === 'announcement' && item.isRead" class="item-actions">
                <el-button
                  v-if="!isExpired(item)"
                  size="small"
                  type="primary"
                  plain
                  round
                  @click.stop="handleComplete(item)"
                >标记完成</el-button>
                <el-button v-else size="small" disabled round>已截止</el-button>
              </div>
              <div v-if="item.source === 'notification' && item.actionUrl" class="item-actions">
                <el-button size="small" type="primary" plain round @click.stop="handleRead(item)">查看详情</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <el-dialog v-model="preferenceVisible" title="通知偏好" width="min(420px, calc(100vw - 32px))">
      <div class="preference-list">
        <div class="preference-item">
          <div>
            <strong>作业提醒</strong>
            <p>作业发布、即将截止和批改结果。</p>
          </div>
          <el-switch v-model="preferences.enable_assignment_due" />
        </div>
        <div class="preference-item">
          <div>
            <strong>成绩通知</strong>
            <p>成绩发布或成绩调整提醒。</p>
          </div>
          <el-switch v-model="preferences.enable_grade_published" />
        </div>
        <div class="preference-item">
          <div>
            <strong>课程更新</strong>
            <p>新增资料和课程公告。</p>
          </div>
          <el-switch v-model="preferences.enable_course_update" />
        </div>
        <div class="preference-item">
          <div>
            <strong>作品审核</strong>
            <p>作品审核通过或驳回提醒。</p>
          </div>
          <el-switch v-model="preferences.enable_project_review" />
        </div>
      </div>
      <template #footer>
        <el-button @click="preferenceVisible = false">取消</el-button>
        <el-button type="primary" @click="savePreferences">保存偏好</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.inbox-page {
  padding-top: 60px;
}

.page-hero {
  padding: var(--space-3xl) 0;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.06), rgba(6, 182, 212, 0.06));
  border-bottom: 1px solid var(--color-border-light);
}

.hero-inner {
  text-align: center;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-learn));
  border-radius: var(--radius-md);
  color: white;
  margin-bottom: var(--space-md);
}

.hero-inner h1 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  text-wrap: balance;
}

.hero-inner p {
  max-width: 72ch;
  margin: 0 auto;
  font-size: var(--text-body);
  line-height: var(--leading-body);
  color: var(--color-text-secondary);
  text-wrap: pretty;
}

.inbox-section {
  padding: var(--space-2xl) 0 var(--space-3xl);
}

.loading-state,
.empty-state {
  text-align: center;
  padding: var(--space-3xl) 0;
  color: var(--color-text-muted);
}

.toolbar-card {
  max-width: 920px;
  margin: 0 auto var(--space-lg);
  padding: var(--space-md);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
}

.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.category-segmented {
  max-width: 100%;
  overflow-x: auto;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.item-content-text {
  margin: var(--space-sm) 0 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
}

.preference-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.preference-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-md);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-bg-soft);
}

.preference-item strong {
  color: var(--color-text);
}

.preference-item p {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.inbox-list {
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.inbox-item {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
  position: relative;
}

.inbox-item:hover {
  box-shadow: var(--shadow-sm);
}

.inbox-item.unread {
  border-color: rgba(79, 70, 229, 0.22);
  background: rgba(79, 70, 229, 0.035);
  box-shadow: inset 0 0 0 1px rgba(79, 70, 229, 0.08);
}

.item-dot {
  width: 8px;
  height: 8px;
  background: var(--color-primary);
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6px;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-xs);
}

.item-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
}

.item-meta {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-sm);
}

.meta-sep {
  margin: 0 var(--space-xs);
}

.item-body {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-sm);
}

.item-quiz {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-sm);
}

.quiz-link {
  font-weight: 600;
  color: var(--color-primary);
}

.item-time {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-sm);
}

.item-time .expired {
  color: #ef4444;
  font-weight: 600;
}

.item-time .not-started {
  color: #f59e0b;
  font-weight: 600;
  margin-right: var(--space-md);
}

.expired-card {
  opacity: 0.55;
  background: var(--color-bg-muted, #f5f5f5) !important;
  border-color: var(--color-border-light) !important;
}

.expired-card:hover {
  box-shadow: none !important;
}

.not-started-card {
  opacity: 0.7;
  background: rgba(245, 158, 11, 0.03) !important;
}

.quiz-link-disabled {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.item-actions {
  padding-top: var(--space-sm);
}
</style>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getAnnouncements, markAsRead, recordCompletion,
  type Announcement,
} from '@/api/announcement'
import {
  getNotifications,
  markNotificationRead,
  type StudentNotification,
} from '@/api/notification'
import { emitMessageRefresh, onMessageRefresh } from '@/utils/messageRefresh'

const router = useRouter()
const announcements = ref<Announcement[]>([])
const notifications = ref<StudentNotification[]>([])
const loading = ref(true)
let refreshTimer: number | undefined
let stopMessageRefresh: (() => void) | undefined
let loadingMessages = false

async function loadMessages(showLoading = false) {
  if (loadingMessages) return
  loadingMessages = true
  if (showLoading) loading.value = true
  try {
    const [announcementList, notificationList] = await Promise.all([
      getAnnouncements(),
      getNotifications(),
    ])
    announcements.value = announcementList
    notifications.value = notificationList
  } finally {
    loadingMessages = false
    loading.value = false
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    loadMessages()
  }
}

onMounted(() => {
  loadMessages(true)
  refreshTimer = window.setInterval(loadMessages, 15_000)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  stopMessageRefresh = onMessageRefresh(loadMessages)
})

onUnmounted(() => {
  if (refreshTimer !== undefined) window.clearInterval(refreshTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  stopMessageRefresh?.()
})

async function handleRead(item: Announcement) {
  if (item.is_read) return
  try {
    await markAsRead(item.id)
    item.is_read = true
    emitMessageRefresh()
  } catch {}
}

async function handleNotificationRead(item: StudentNotification) {
  if (item.is_read) return
  try {
    await markNotificationRead(item.id)
    item.is_read = true
    emitMessageRefresh()
  } catch {}
}

async function openProjectNotification(item: StudentNotification) {
  await handleNotificationRead(item)
  if (item.project_id) {
    router.push(`/create/project/${item.project_id}`)
  }
}

async function handleComplete(item: Announcement) {
  if (isExpired(item)) {
    ElMessage.warning('该任务已截止，无法标记完成')
    return
  }
  try {
    await recordCompletion(item.id)
    ElMessage.success('已标记完成')
    await loadMessages()
    emitMessageRefresh()
  } catch {
    ElMessage.error('操作失败')
  }
}

function isExpired(item: Announcement) {
  if (!item.end_time) return false
  return new Date(item.end_time) < new Date()
}

function canPractice(item: Announcement) {
  return item.question_ids.length > 0 && !item.is_completed && !isExpired(item) && !isNotStarted(item)
}

function canManualComplete(item: Announcement) {
  return item.question_ids.length === 0 && !item.is_completed && !isExpired(item) && !isNotStarted(item)
}

function actionDisabledText(item: Announcement) {
  if (item.is_completed) return '已完成'
  if (isNotStarted(item)) return '未开始'
  if (isExpired(item)) return '已截止'
  if (item.question_ids.length > 0) return '请先练习'
  return '不可完成'
}

/** 判断任务是否尚未开始 */
function isNotStarted(item: Announcement) {
  if (!item.start_time) return false
  return new Date(item.start_time) > new Date()
}

function formatDate(dateStr: string) {
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
          <h1>消息通知</h1>
          <p>查看老师发布的题目任务</p>
        </div>
      </div>
    </section>

    <section class="inbox-section">
      <div class="container">
        <div v-if="loading" class="loading-state">加载中...</div>

        <div v-else-if="announcements.length === 0 && notifications.length === 0" class="empty-state">
          <p>暂无消息通知</p>
        </div>

        <div v-else class="inbox-list">
          <div
            v-for="item in notifications"
            :key="`notification-${item.id}`"
            class="inbox-item review-item"
            :class="{ unread: !item.is_read }"
            @click="handleNotificationRead(item)"
          >
            <div class="item-dot" v-if="!item.is_read"></div>
            <div class="item-content">
              <div class="item-header">
                <span class="item-title">{{ item.title }}</span>
                <el-tag
                  :type="item.content.includes('驳回') ? 'danger' : 'success'"
                  size="small"
                  effect="plain"
                >
                  作品审核
                </el-tag>
              </div>
              <div class="item-meta">
                <span>{{ formatDate(item.created_at) }}</span>
              </div>
              <div class="item-body">{{ item.content }}</div>
              <div v-if="item.project_id" class="item-actions">
                <el-button
                  size="small"
                  type="primary"
                  plain
                  round
                  @click.stop="openProjectNotification(item)"
                >查看作品</el-button>
              </div>
            </div>
          </div>

          <div
            v-for="item in announcements"
            :key="item.id"
            class="inbox-item"
            :class="{
              unread: !item.is_read,
              'expired-card': isExpired(item),
              'not-started-card': isNotStarted(item),
            }"
            @click="handleRead(item)"
          >
            <div class="item-dot" v-if="!item.is_read"></div>
            <div class="item-content">
              <div class="item-header">
                <span class="item-title">{{ item.title }}</span>
                <el-tag
                  type="success"
                  size="small"
                  effect="plain"
                >
                  题目
                </el-tag>
              </div>
              <div class="item-meta">
                <span>{{ item.teacher_name }}</span>
                <span class="meta-sep">·</span>
                <span>{{ item.class_names?.join('、') || item.course_name }}</span>
                <span class="meta-sep">·</span>
                <span>{{ formatDate(item.created_at) }}</span>
              </div>
              <div v-if="item.question_ids.length > 0" class="item-quiz">
                <span>包含 {{ item.question_ids.length }} 道题目</span>
                <router-link
                  v-if="canPractice(item)"
                  :to="`/practice/announcement/${item.id}`"
                  class="quiz-link"
                >去练习</router-link>
                <span v-else class="quiz-link-disabled">{{ item.is_completed ? '已完成' : isExpired(item) ? '已截止' : '未开始' }}</span>
              </div>
              <div class="item-time">
                <span v-if="item.start_time && isNotStarted(item)" class="not-started">
                  未开始: {{ formatDate(item.start_time) }}
                </span>
                <span v-if="item.end_time" :class="{ expired: isExpired(item) }">
                  {{ isExpired(item) ? '已截止' : '截止' }}: {{ formatDate(item.end_time) }}
                </span>
              </div>
              <div v-if="item.is_read" class="item-actions">
                <el-button
                  v-if="canManualComplete(item)"
                  size="small"
                  type="primary"
                  plain
                  round
                  @click.stop="handleComplete(item)"
                >标记完成</el-button>
                <el-button v-else-if="item.question_ids.length > 0 && canPractice(item)" size="small" type="primary" plain round @click.stop="router.push(`/practice/announcement/${item.id}`)">去练习</el-button>
                <el-button v-else size="small" disabled round>{{ actionDisabledText(item) }}</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
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
  font-size: 1.8rem;
  font-weight: 800;
  font-family: var(--font-serif);
  letter-spacing: 0.05em;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.hero-inner p {
  font-size: 1rem;
  color: var(--color-text-secondary);
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
  border-left: 3px solid var(--color-primary);
  background: rgba(79, 70, 229, 0.02);
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

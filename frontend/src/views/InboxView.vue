<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getAnnouncements, markAsRead, recordCompletion,
  type Announcement,
} from '@/api/announcement'

const router = useRouter()
const announcements = ref<Announcement[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    announcements.value = await getAnnouncements()
  } finally {
    loading.value = false
  }
})

async function handleRead(item: Announcement) {
  if (item.is_read) return
  try {
    await markAsRead(item.id)
    item.is_read = true
  } catch {}
}

async function handleComplete(item: Announcement) {
  try {
    await recordCompletion(item.id)
    ElMessage.success('已标记完成')
    // refresh
    announcements.value = await getAnnouncements()
  } catch {
    ElMessage.error('操作失败')
  }
}

function isExpired(item: Announcement) {
  if (!item.end_time) return false
  return new Date(item.end_time) < new Date()
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

        <div v-else-if="announcements.length === 0" class="empty-state">
          <p>暂无消息通知</p>
        </div>

        <div v-else class="inbox-list">
          <div
            v-for="item in announcements"
            :key="item.id"
            class="inbox-item"
            :class="{ unread: !item.is_read }"
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
                <router-link :to="`/practice`" class="quiz-link">去练习</router-link>
              </div>
              <div v-if="item.end_time" class="item-time">
                <span :class="{ expired: isExpired(item) }">
                  {{ isExpired(item) ? '已截止' : '截止' }}: {{ formatDate(item.end_time) }}
                </span>
              </div>
              <div v-if="item.is_read" class="item-actions">
                <el-button size="small" type="primary" plain round @click.stop="handleComplete(item)">标记完成</el-button>
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
  padding-top: 64px;
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
  border-radius: var(--radius-lg);
  color: white;
  margin-bottom: var(--space-md);
}

.hero-inner h1 {
  font-size: 1.8rem;
  font-weight: 800;
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

.item-actions {
  padding-top: var(--space-sm);
}
</style>

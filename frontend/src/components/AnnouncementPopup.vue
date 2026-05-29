<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getUnreadCount, getAnnouncements, markAsRead, type Announcement } from '@/api/announcement'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const visible = ref(false)
const latestAnnouncement = ref<Announcement | null>(null)

onMounted(async () => {
  if (!authStore.isLoggedIn || authStore.user?.role !== 'student') return
  // Only show once per session
  if (sessionStorage.getItem('announcement_popup_shown')) return

  try {
    const { count } = await getUnreadCount()
    if (count > 0) {
      const list = await getAnnouncements()
      const unread = list.filter(a => !a.is_read)
      if (unread.length > 0) {
        latestAnnouncement.value = unread[0] ?? null
        visible.value = true
        sessionStorage.setItem('announcement_popup_shown', '1')
      }
    }
  } catch {}
})

function goToInbox() {
  visible.value = false
  router.push('/inbox')
}

async function dismiss() {
  if (latestAnnouncement.value) {
    try {
      await markAsRead(latestAnnouncement.value.id)
    } catch {}
  }
  visible.value = false
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="新消息通知"
    width="420px"
    :close-on-click-modal="false"
  >
    <template v-if="latestAnnouncement">
      <div class="popup-content">
        <div class="popup-type">
          <el-tag type="success" size="small" effect="plain">题目</el-tag>
        </div>
        <h3 class="popup-title">{{ latestAnnouncement.title }}</h3>
        <div class="popup-meta">
          <span>{{ latestAnnouncement.teacher_name }}</span>
          <span class="sep">·</span>
          <span>{{ latestAnnouncement.class_names?.join('、') || latestAnnouncement.course_name }}</span>
          <span class="sep">·</span>
          <span>{{ formatDate(latestAnnouncement.created_at) }}</span>
        </div>
        <p class="popup-quiz">
          包含 {{ latestAnnouncement.question_ids.length }} 道题目
        </p>
      </div>
    </template>
    <template #footer>
      <el-button @click="dismiss">我知道了</el-button>
      <el-button type="primary" @click="goToInbox">查看详情</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.popup-content {
  padding: var(--space-sm) 0;
}

.popup-type {
  margin-bottom: var(--space-sm);
}

.popup-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.popup-meta {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-md);
}

.sep {
  margin: 0 var(--space-xs);
}

.popup-body {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-sm);
}

.popup-quiz {
  font-size: 0.85rem;
  color: var(--color-primary);
  font-weight: 600;
}
</style>

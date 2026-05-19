<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTeacherStats } from '@/api/teacher'

const router = useRouter()

const stats = ref([
  { label: '总学生数', value: '0', color: 'var(--color-learn)' },
  { label: '已发布章节', value: '0 / 0', color: 'var(--color-primary)' },
  { label: '待审作品', value: '0', color: 'var(--color-create)' },
  { label: '本周练习量', value: '0', color: 'var(--color-act)' },
])

const quickActions = [
  { label: '上传资料', desc: '上传视频课件或 PDF 讲义', path: '/teacher/materials', color: 'var(--color-learn)' },
  { label: '管理题库', desc: '新增、编辑或删除练习题', path: '/teacher/questions', color: 'var(--color-practice)' },
  { label: '审核作品', desc: '查看并审核学生提交的作品', path: '/teacher/reviews', color: 'var(--color-create)' },
]

onMounted(async () => {
  try {
    const data = await getTeacherStats()
    stats.value = [
      { label: '总学生数', value: String(data.total_students), color: 'var(--color-learn)' },
      { label: '已发布章节', value: `${data.published_chapters} / 6`, color: 'var(--color-primary)' },
      { label: '待审作品', value: String(data.pending_reviews), color: 'var(--color-create)' },
      { label: '本周练习量', value: String(data.weekly_exercises), color: 'var(--color-act)' },
    ]
  } catch {}
})
</script>

<template>
  <div class="dashboard">
    <h1 class="page-title">欢迎回来，教师</h1>

    <!-- Stats -->
    <div class="stats-grid">
      <div v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
    </div>

    <!-- Quick actions -->
    <h2 class="section-title">快捷操作</h2>
    <div class="actions-grid">
      <div
        v-for="action in quickActions"
        :key="action.label"
        class="action-card"
        @click="router.push(action.path)"
      >
        <div class="action-dot" :style="{ background: action.color }"></div>
        <div>
          <h3>{{ action.label }}</h3>
          <p>{{ action.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xl);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-2xl);
}

.stat-card {
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  text-align: center;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 900;
  font-family: var(--font-mono);
  margin-bottom: var(--space-xs);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.section-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
}

.action-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.action-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
}

.action-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.action-card h3 {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 2px;
}

.action-card p {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .actions-grid {
    grid-template-columns: 1fr;
  }
}
</style>

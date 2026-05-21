<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCourseDetail, type CourseDetail } from '@/api/course'

const route = useRoute()
const router = useRouter()
const courseId = computed(() => Number(route.params.courseId))
const course = ref<CourseDetail | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    course.value = await getCourseDetail(courseId.value)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="course-detail-page">
    <section class="course-hero">
      <div class="container">
        <button class="back-btn" @click="router.push('/learn')">返回课程列表</button>
        <div v-if="course" class="course-heading">
          <h1>{{ course.name }}</h1>
          <p>{{ course.chapter_count }} 个章节，{{ course.material_count }} 份学习资料</p>
        </div>
      </div>
    </section>

    <section class="chapters-section">
      <div class="container">
        <div v-if="loading" class="empty-state">课程加载中...</div>
        <div v-else-if="course && course.chapters.length > 0" class="chapters-grid">
          <div v-for="ch in course.chapters" :key="ch.num" class="chapter-card" :class="{ locked: ch.status === '即将发布' }">
            <div class="chapter-header">
              <span class="chapter-num">{{ ch.num }}</span>
              <el-tag :type="ch.status === '已发布' ? 'success' : 'info'" size="small" effect="plain">
                {{ ch.status }}
              </el-tag>
            </div>
            <h3 class="chapter-title">{{ ch.title }}</h3>
            <p class="chapter-desc">{{ ch.desc }}</p>

            <div class="chapter-topics">
              <span v-for="topic in ch.topics" :key="topic" class="topic-tag">{{ topic }}</span>
            </div>

            <div v-if="ch.day_of_week" class="chapter-schedule">
              <span>{{ ch.day_of_week }} 第 {{ ch.class_periods || '未设置' }} 节</span>
              <span v-if="ch.schedule_note" class="schedule-note">（{{ ch.schedule_note }}）</span>
            </div>

            <div class="content-count">
              <span>{{ ch.videos }} 个视频</span>
              <span class="count-sep">·</span>
              <span>{{ ch.docs }} 份文档</span>
            </div>

            <div v-if="ch.progress > 0" class="chapter-progress">
              <el-progress :percentage="ch.progress" :stroke-width="6" :show-text="false" color="var(--color-learn)" />
              <span class="progress-text">已学习 {{ ch.progress }}%</span>
            </div>

            <button class="chapter-btn" :disabled="ch.status === '即将发布'" @click="router.push(`/learn/${ch.num}`)">
              {{ ch.status === '已发布' ? '开始学习' : '敬请期待' }}
            </button>
          </div>
        </div>
        <div v-else class="empty-state">该课程暂无章节。</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.course-detail-page {
  padding-top: 64px;
}

.course-hero {
  padding: var(--space-3xl) 0;
  background: var(--color-learn-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.back-btn {
  margin-bottom: var(--space-lg);
  color: var(--color-text-secondary);
  font-weight: 600;
}

.back-btn:hover {
  color: var(--color-learn);
}

.course-heading h1 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text);
}

.course-heading p {
  margin-top: var(--space-sm);
  color: var(--color-text-secondary);
}

.chapters-section {
  padding: var(--space-3xl) 0;
}

.chapters-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-xl);
}

.chapter-card {
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--duration-normal) var(--ease-out);
}

.chapter-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.chapter-card.locked {
  opacity: 0.6;
}

.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.chapter-num {
  font-size: 2rem;
  font-weight: 900;
  color: var(--color-border);
  font-family: var(--font-mono);
  line-height: 1;
}

.chapter-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.chapter-desc {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
  line-height: 1.6;
}

.chapter-topics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
}

.topic-tag {
  padding: 0.25rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-learn);
  background: var(--color-learn-bg);
  border-radius: var(--radius-full);
  border: 1px solid rgba(6, 182, 212, 0.15);
}

.content-count,
.chapter-schedule {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-lg);
}

.chapter-schedule {
  color: var(--color-learn);
  font-weight: 500;
}

.schedule-note {
  color: var(--color-text-muted);
  font-weight: 400;
}

.count-sep {
  margin: 0 var(--space-xs);
}

.chapter-progress {
  margin-bottom: var(--space-lg);
}

.progress-text {
  display: block;
  margin-top: var(--space-xs);
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.chapter-btn {
  width: 100%;
  padding: 0.65rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: var(--color-learn);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.chapter-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.chapter-btn:disabled {
  background: var(--color-border);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
  font-size: 1rem;
}

@media (max-width: 768px) {
  .chapters-grid {
    grid-template-columns: 1fr;
  }
}
</style>

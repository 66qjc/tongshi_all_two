<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getChapters, type Chapter } from '@/api/chapter'
import { getCourses, type Course } from '@/api/course'

const router = useRouter()
const chapters = ref<Chapter[]>([])
const courses = ref<Course[]>([])
const loading = ref(true)

const unassignedChapters = computed(() => chapters.value.filter(chapter => !chapter.course_id))

onMounted(async () => {
  try {
    const [chapterList, courseList] = await Promise.all([getChapters(), getCourses()])
    chapters.value = chapterList
    courses.value = courseList
  } finally {
    loading.value = false
  }
})

function openChapter(chapter: Chapter) {
  if (chapter.status === '已发布') {
    router.push(`/learn/${chapter.num}`)
  }
}
</script>

<template>
  <div class="learn-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 6.25278V19.2528M12 6.25278C10.8321 5.47686 9.24649 5 7.5 5C5.75351 5 4.16789 5.47686 3 6.25278V19.2528C4.16789 18.4769 5.75351 18 7.5 18C9.24649 18 10.8321 18.4769 12 19.2528M12 6.25278C13.1679 5.47686 14.7535 5 16.5 5C18.2465 5 19.8321 5.47686 21 6.25278V19.2528C19.8321 18.4769 18.2465 18 16.5 18C14.7535 18 13.1679 18.4769 12 19.2528"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
          <h1>探 · 学无止境</h1>
          <p>按课程进入章节学习，查看资料、课表与学习进度。</p>
        </div>
      </div>
    </section>

    <section class="chapters-section">
      <div class="container">
        <div v-if="loading" class="empty-state">课程加载中...</div>

        <template v-else>
          <div v-if="courses.length > 0" class="course-grid">
            <div v-for="course in courses" :key="course.id" class="course-card" @click="router.push(`/learn/course/${course.id}`)">
              <div class="course-card-header">
                <h3>{{ course.name }}</h3>
                <span>{{ course.chapter_count }} 章</span>
              </div>
              <p>共 {{ course.material_count }} 份学习资料</p>
              <el-button type="primary" plain>查看课程</el-button>
            </div>
          </div>

          <div v-if="unassignedChapters.length > 0" class="unassigned-section">
            <h2>未分配课程</h2>
            <div class="chapters-grid">
              <div
                v-for="ch in unassignedChapters"
                :key="ch.num"
                class="chapter-card"
                :class="{ locked: ch.status === '即将发布' }"
              >
                <div class="chapter-header">
                  <span class="chapter-num">{{ ch.num }}</span>
                  <el-tag :type="ch.status === '已发布' ? 'success' : 'info'" size="small" effect="plain">
                    {{ ch.status }}
                  </el-tag>
                </div>

                <h3 class="chapter-title">{{ ch.title }}</h3>
                <p class="chapter-desc">{{ ch.desc }}</p>

                <div class="chapter-topics">
                  <span v-for="topic in ch.topics" :key="topic" class="topic-tag">
                    {{ topic }}
                  </span>
                </div>

                <div v-if="ch.videos > 0 || ch.docs > 0" class="content-count">
                  <span v-if="ch.videos > 0">{{ ch.videos }} 个视频</span>
                  <span v-if="ch.videos > 0 && ch.docs > 0" class="count-sep">·</span>
                  <span v-if="ch.docs > 0">{{ ch.docs }} 份文档</span>
                </div>

                <div v-if="ch.day_of_week" class="chapter-schedule">
                  <span>{{ ch.day_of_week }} 第 {{ ch.class_periods || '未设置' }} 节</span>
                  <span v-if="ch.schedule_note" class="schedule-note">（{{ ch.schedule_note }}）</span>
                </div>

                <div v-if="ch.progress > 0" class="chapter-progress">
                  <el-progress :percentage="ch.progress" :stroke-width="6" :show-text="false" color="var(--color-learn)" />
                  <span class="progress-text">已学习 {{ ch.progress }}%</span>
                </div>

                <button class="chapter-btn" :disabled="ch.status === '即将发布'" @click="openChapter(ch)">
                  {{ ch.status === '已发布' ? '开始学习' : '敬请期待' }}
                </button>
              </div>
            </div>
          </div>

          <div v-if="courses.length === 0 && unassignedChapters.length === 0" class="empty-state">
            暂无课程内容。
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.learn-page {
  padding-top: 64px;
}

.page-hero {
  padding: var(--space-3xl) 0;
  background: var(--color-learn-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.hero-inner {
  text-align: center;
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, var(--color-learn-light), var(--color-learn));
  border-radius: var(--radius-lg);
  color: white;
  margin-bottom: var(--space-lg);
}

.hero-inner h1 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.hero-inner p {
  font-size: 1.05rem;
  color: var(--color-text-secondary);
}

.chapters-section {
  padding: var(--space-3xl) 0;
}

.course-grid,
.chapters-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-xl);
}

.course-grid {
  margin-bottom: var(--space-3xl);
}

.course-card,
.chapter-card {
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--duration-normal) var(--ease-out);
}

.course-card {
  cursor: pointer;
}

.course-card:hover,
.chapter-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.course-card-header,
.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.course-card h3 {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-text);
}

.course-card p {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
}

.chapter-card.locked {
  opacity: 0.6;
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

.unassigned-section h2 {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
}

.empty-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
  font-size: 1rem;
}

@media (max-width: 768px) {
  .course-grid,
  .chapters-grid {
    grid-template-columns: 1fr;
  }
}
</style>

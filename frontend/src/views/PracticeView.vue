<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCourses, type Course } from '@/api/course'
import { getQuestions } from '@/api/question'
import { getQuizHistory, getQuizStats } from '@/api/quiz'

const router = useRouter()
const courses = ref<Course[]>([])
const loading = ref(true)
const stats = ref([
  { label: '总题数', value: '0' },
  { label: '已练习', value: '0' },
  { label: '正确率', value: '0%' },
  { label: '今日练习', value: '0' },
])
const recentExercises = ref<any[]>([])

onMounted(async () => {
  try {
    const [quizStats, courseList, history] = await Promise.all([
      getQuizStats(),
      getCourses(),
      getQuizHistory(5),
      getQuestions(),
    ])
    stats.value = [
      { label: '总题数', value: String(quizStats.total_questions) },
      { label: '已练习', value: String(quizStats.questions_done) },
      { label: '正确率', value: `${quizStats.accuracy}%` },
      { label: '今日练习', value: String(quizStats.today_count) },
    ]
    courses.value = courseList
    recentExercises.value = history.map((item: any) => ({
      title: item.stem || '练习题目',
      result: item.is_correct ? 'correct' : 'wrong',
    }))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="practice-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">练</div>
          <h1>练 · 学以致用</h1>
          <p>按课程进入练习，提交后即时查看答案与解析。</p>
        </div>
      </div>
    </section>

    <section class="stats-section">
      <div class="container">
        <div class="stats-grid">
          <div v-for="stat in stats" :key="stat.label" class="stat-card">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="courses-section">
      <div class="container">
        <div v-if="loading" class="empty-state">练习加载中...</div>
        <div v-else-if="courses.length > 0" class="course-grid">
          <button v-for="course in courses" :key="course.id" class="course-card" @click="router.push(`/practice/quiz/${course.id}`)">
            <h3>{{ course.name }}</h3>
            <p>{{ course.question_count }} 道题目</p>
            <span>开始练习</span>
          </button>
        </div>
        <div v-else class="empty-state">暂无可练习课程。</div>
      </div>
    </section>

    <section v-if="recentExercises.length > 0" class="recent-section">
      <div class="container">
        <h2>最近练习</h2>
        <div class="recent-list">
          <div v-for="item in recentExercises" :key="item.title" class="recent-item">
            <span>{{ item.title }}</span>
            <strong :class="item.result">{{ item.result === 'correct' ? '正确' : '错误' }}</strong>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.practice-page {
  padding-top: 64px;
}

.page-hero {
  padding: var(--space-3xl) 0;
  background: var(--color-practice-bg);
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
  background: var(--color-practice);
  border-radius: var(--radius-lg);
  color: white;
  font-size: 1.4rem;
  font-weight: 800;
  margin-bottom: var(--space-lg);
}

.hero-inner h1 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.stats-section,
.courses-section,
.recent-section {
  padding: var(--space-2xl) 0;
}

.stats-grid,
.course-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-md);
}

.course-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.stat-card,
.course-card,
.recent-item {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.stat-card {
  padding: var(--space-lg);
  text-align: center;
}

.stat-value {
  font-size: 1.6rem;
  font-weight: 900;
  color: var(--color-practice);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.course-card {
  text-align: left;
  padding: var(--space-xl);
}

.course-card:hover {
  border-color: var(--color-practice);
  box-shadow: var(--shadow-md);
}

.course-card h3 {
  font-size: 1.15rem;
  font-weight: 800;
  margin-bottom: var(--space-sm);
}

.course-card p {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
}

.course-card span {
  color: var(--color-practice);
  font-weight: 800;
}

.recent-section h2 {
  font-size: 1.2rem;
  font-weight: 800;
  margin-bottom: var(--space-lg);
}

.recent-list {
  display: grid;
  gap: var(--space-sm);
}

.recent-item {
  display: flex;
  justify-content: space-between;
  padding: var(--space-md);
}

.recent-item strong.correct {
  color: #10b981;
}

.recent-item strong.wrong {
  color: #ef4444;
}

.empty-state {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-3xl) 0;
}

@media (max-width: 768px) {
  .stats-grid,
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>

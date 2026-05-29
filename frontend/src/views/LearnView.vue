<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCourses, type Course } from '@/api/course'

const router = useRouter()
const courses = ref<Course[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    courses.value = await getCourses()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="learn-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">学</div>
          <h1>探 · 学无止境</h1>
          <p>按课程查看视频课件、PDF 讲义和学习进度。</p>
        </div>
      </div>
    </section>

    <section class="courses-section">
      <div class="container">
        <div v-if="loading" class="empty-state">课程加载中...</div>
        <div v-else-if="courses.length > 0" class="course-grid">
          <button v-for="course in courses" :key="course.id" class="course-card" @click="router.push(`/learn/course/${course.id}`)">
            <h3>{{ course.name }}</h3>
            <p>{{ course.material_count }} 份学习资料 · {{ course.question_count }} 道练习题</p>
            <span>查看课程</span>
          </button>
        </div>
        <div v-else class="empty-state">暂无课程内容。</div>
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

.hero-inner p {
  font-size: 1.05rem;
  color: var(--color-text-secondary);
}

.courses-section {
  padding: var(--space-3xl) 0;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-xl);
}

.course-card {
  text-align: left;
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-learn);
}

.course-card h3 {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.course-card p {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
}

.course-card span {
  color: var(--color-learn);
  font-weight: 700;
}

.empty-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
}

@media (max-width: 768px) {
  .course-grid {
    grid-template-columns: 1fr;
  }
}
</style>

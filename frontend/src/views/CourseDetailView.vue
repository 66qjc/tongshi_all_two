<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getCourseDetail, type CourseDetail } from '@/api/course'
import { getCourseContents, type Material } from '@/api/material'
import { resolveFileUrl } from '@/utils/url'

const route = useRoute()
const router = useRouter()
const courseId = computed(() => Number(route.params.courseId))
const course = ref<CourseDetail | null>(null)
const materials = ref<Material[]>([])
const loading = ref(true)

function materialUrl(item: Material) {
  return resolveFileUrl(item.file_id ? `/api/files/${item.file_id}` : item.url)
}

onMounted(async () => {
  try {
    const [detail, contents] = await Promise.all([
      getCourseDetail(courseId.value),
      getCourseContents(courseId.value),
    ])
    course.value = detail
    materials.value = contents
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
          <p>{{ course.material_count }} 份学习资料，{{ course.question_count }} 道练习题</p>
        </div>
      </div>
    </section>

    <section class="materials-section">
      <div class="container">
        <div v-if="loading" class="empty-state">课程加载中...</div>
        <div v-else-if="materials.length > 0" class="materials-grid">
          <a
            v-for="item in materials"
            :key="item.id"
            class="material-card"
            :href="materialUrl(item)"
            target="_blank"
            rel="noopener"
          >
            <span class="material-type">{{ item.type === 'video' ? '视频' : 'PDF' }}</span>
            <h3>{{ item.title }}</h3>
            <p>{{ item.size || '未记录大小' }} · {{ item.date || '未记录日期' }}</p>
          </a>
        </div>
        <div v-else class="empty-state">该课程暂无学习资料。</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.course-detail-page {
  padding-top: 64px;
}

.course-hero {
  padding: var(--space-2xl) 0;
  background: var(--color-learn-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.back-btn {
  margin-bottom: var(--space-lg);
  color: var(--color-learn);
  font-weight: 700;
}

.course-heading h1 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.course-heading p {
  color: var(--color-text-secondary);
}

.materials-section {
  padding: var(--space-3xl) 0;
}

.materials-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-xl);
}

.material-card {
  display: block;
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
}

.material-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-learn);
}

.material-type {
  display: inline-flex;
  margin-bottom: var(--space-sm);
  color: var(--color-learn);
  font-weight: 800;
}

.material-card h3 {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.material-card p,
.empty-state {
  color: var(--color-text-muted);
}

.empty-state {
  text-align: center;
  padding: var(--space-4xl) 0;
}

@media (max-width: 768px) {
  .materials-grid {
    grid-template-columns: 1fr;
  }
}
</style>

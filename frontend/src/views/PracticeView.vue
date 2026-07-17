<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCourseList, type Course } from '@/api/course'
import { getAnnouncements, type Announcement } from '@/api/announcement'
import { getQuizStats } from '@/api/quiz'

const router = useRouter()
const courses = ref<Course[]>([])
const announcements = ref<Announcement[]>([])
const globalStats = ref({ total_questions: 0, questions_done: 0, accuracy: 0, today_count: 0 })
const loading = ref(true)
const courseHint = ref<string | null>(null)

async function loadData() {
  loading.value = true
  try {
    const [courseResult, a, stats] = await Promise.all([
      getCourseList(),
      getAnnouncements(),
      getQuizStats().catch(() => ({ total_questions: 0, questions_done: 0, accuracy: 0, today_count: 0 })),
    ])
    courses.value = courseResult.courses
    courseHint.value = courseResult.hint
    announcements.value = a
    globalStats.value = stats
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const emptyText = computed(() => courseHint.value || '暂无已加入的课程')
const noEnrollment = computed(() => !loading.value && courses.value.length === 0)

const courseAssignmentStats = computed(() => {
  const map = new Map<number, { completed: number; pending: number; expired: number }>()
  for (const c of courses.value) {
    const items = announcements.value.filter(a => a.course_id === c.id)
    map.set(c.id, {
      completed: items.filter(a => a.is_completed).length,
      pending: items.filter(a => !a.is_completed && (!a.end_time || new Date(a.end_time) > new Date())).length,
      expired: items.filter(a => !a.is_completed && a.end_time && new Date(a.end_time) <= new Date()).length,
    })
  }
  return map
})

function goToAssignments(courseId: number, status: string) {
  router.push(`/practice/assignments?course_id=${courseId}&status=${status}`)
}

function goToFreePractice() {
  router.push('/practice/quiz?random=10')
}
</script>

<template>
  <div class="practice-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <img
              src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png"
              alt="AI 通识课平台标识"
              width="40"
              height="40"
              class="hero-icon-image"
            />
          </div>
          <h1>思 · 深化理解</h1>
          <p>完成老师发布的作业练习，也可以进入全站共享题池自由练习。</p>
        </div>
      </div>
    </section>

    <div v-if="loading" class="empty-state">加载中...</div>

    <template v-else>
      <section class="section-block free-section">
        <div class="container">
          <h2 class="section-title">自由练习</h2>
          <div v-if="noEnrollment" class="empty-hint">你尚未加入课程</div>
          <div v-else class="global-practice-card">
            <div class="global-stats">
              <div class="stat-item">
                <span class="stat-num">{{ globalStats.total_questions }}</span>
                <span class="stat-label">可见题数</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ globalStats.questions_done }}</span>
                <span class="stat-label">已完成</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ globalStats.accuracy }}%</span>
                <span class="stat-label">正确率</span>
              </div>
              <div class="stat-item">
                <span class="stat-num">{{ globalStats.today_count }}</span>
                <span class="stat-label">今日作答</span>
              </div>
            </div>
            <button class="go-btn" @click="goToFreePractice">进入全局练习</button>
          </div>
        </div>
      </section>

      <section class="section-block">
        <div class="container">
          <h2 class="section-title">作业</h2>
          <div v-if="courses.length === 0" class="empty-hint">{{ emptyText }}</div>
          <div v-else class="card-grid">
            <div v-for="c in courses" :key="c.id" class="hw-card">
              <h3>{{ c.name }}</h3>
              <div class="hw-stats">
                <div class="hw-stat done" @click="goToAssignments(c.id, 'completed')">
                  <span class="hw-num">{{ courseAssignmentStats.get(c.id)?.completed ?? 0 }}</span>
                  <span class="hw-label">已完成</span>
                </div>
                <div class="hw-stat pending" @click="goToAssignments(c.id, 'pending')">
                  <span class="hw-num">{{ courseAssignmentStats.get(c.id)?.pending ?? 0 }}</span>
                  <span class="hw-label">未完成</span>
                  <span v-if="(courseAssignmentStats.get(c.id)?.expired ?? 0) > 0" class="hw-expired-tip">
                    含 {{ courseAssignmentStats.get(c.id)?.expired }} 个已过期
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.practice-page { padding-top: 60px; }

.page-hero {
  padding: var(--space-3xl) 0 var(--space-2xl);
  background: var(--color-practice-bg);
  border-bottom: 1px solid var(--color-border-light);
}
.hero-inner { text-align: center; }
.hero-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 56px; height: 56px;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
  box-shadow: 0 4px 14px rgba(0,0,0,0.15);
}
.hero-icon-image {
  display: block;
  width: 40px;
  height: 40px;
  object-fit: contain;
}
.hero-inner h1 {
  font-family: var(--font-sans); font-size: var(--text-page-title); font-weight: 900;
  line-height: var(--leading-title); color: var(--color-text); margin-bottom: var(--space-sm); letter-spacing: 0;
  text-wrap: balance;
}
.hero-inner p { font-size: var(--text-body); color: var(--color-text-secondary); line-height: var(--leading-body); }

.section-block { padding: var(--space-2xl) 0; }
.section-block + .section-block { border-top: 1px solid var(--color-border-light); }
.free-section { background: var(--color-bg-alt); }

.section-title {
  font-family: var(--font-sans); font-size: var(--text-section-title); font-weight: 900;
  line-height: var(--leading-title); color: var(--color-text); margin-bottom: var(--space-lg); letter-spacing: 0;
}

.card-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-md); }

.hw-card {
  padding: var(--space-lg); background: var(--color-bg-card);
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
}
.hw-card h3 {
  font-family: var(--font-sans); font-size: var(--text-card-title); font-weight: 800;
  line-height: var(--leading-compact); color: var(--color-text); margin-bottom: var(--space-md); letter-spacing: 0;
}

.hw-stats { display: flex; gap: var(--space-sm); }
.hw-stat {
  flex: 1; text-align: center; padding: var(--space-sm) 0;
  border-radius: var(--radius-sm); cursor: pointer; transition: all var(--duration-fast);
}
.hw-stat.done { background: rgba(16,185,129,0.08); }
.hw-stat.done:hover { background: rgba(16,185,129,0.15); }
.hw-stat.pending { background: rgba(245,158,11,0.08); }
.hw-stat.pending:hover { background: rgba(245,158,11,0.15); }
.hw-num { display: block; font-size: 1.4rem; font-weight: 800; }
.hw-label { font-size: 0.85rem; color: var(--color-text-secondary); }
.hw-expired-tip { display: block; font-size: 0.75rem; color: var(--color-danger, #dc2626); margin-top: 2px; }

.global-practice-card {
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  flex-wrap: wrap;
}
.global-stats { display: flex; gap: var(--space-xl); flex-wrap: wrap; }
.stat-item { text-align: center; min-width: 72px; }
.stat-num { display: block; font-size: 1.5rem; font-weight: 800; color: var(--color-text); }
.stat-label { font-size: 0.85rem; color: var(--color-text-secondary); }
.go-btn {
  border: none;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  padding: 0.7rem 1.2rem;
  font-weight: 700;
  cursor: pointer;
}
.empty-hint, .empty-state {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--space-xl) 0;
}

@media (max-width: 768px) {
  .card-grid { grid-template-columns: 1fr; }
  .global-practice-card { flex-direction: column; align-items: stretch; }
}
</style>

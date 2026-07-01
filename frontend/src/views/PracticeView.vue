<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCourseList, type Course } from '@/api/course'
import { getAnnouncements, type Announcement } from '@/api/announcement'
import { getCourseQuizStats } from '@/api/quiz'

const router = useRouter()
const courses = ref<Course[]>([])
const announcements = ref<Announcement[]>([])
const courseStats = ref<Map<number, { done: number; accuracy: number }>>(new Map())
const loading = ref(true)
const courseHint = ref<string | null>(null)

async function loadData() {
  loading.value = true
  try {
    const [courseResult, a] = await Promise.all([getCourseList(), getAnnouncements()])
    courses.value = courseResult.courses
    courseHint.value = courseResult.hint
    announcements.value = a
    const statsMap = new Map<number, { done: number; accuracy: number }>()
    await Promise.all(
      courses.value.map(async (co) => {
        try {
          const s = await getCourseQuizStats(co.id)
          statsMap.set(co.id, { done: s.questions_done, accuracy: s.accuracy })
        } catch {
          // 单个课程统计失败不影响课程入口展示。
        }
      }),
    )
    courseStats.value = statsMap
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const emptyText = computed(() => courseHint.value || '暂无已加入的课程')

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

function goToFreePractice(courseId: number) {
  router.push(`/practice/quiz/${courseId}?random=10`)
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
          <p>完成老师发布的作业练习，也可以围绕已加入课程自由练习。</p>
        </div>
      </div>
    </section>

    <div v-if="loading" class="empty-state">加载中...</div>

    <template v-else>
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

      <section class="section-block free-section">
        <div class="container">
          <h2 class="section-title">自由练习</h2>
          <div v-if="courses.length === 0" class="empty-hint">{{ emptyText }}</div>
          <div v-else class="card-grid">
            <div v-for="c in courses" :key="c.id" class="free-card">
              <h3>{{ c.name }}</h3>
              <div class="free-row">
                <span class="free-stat">已完成 {{ courseStats.get(c.id)?.done ?? 0 }} 次</span>
                <span class="free-stat">题目 {{ c.question_count }} 题</span>
                <button class="go-btn" @click="goToFreePractice(c.id)">去练习</button>
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
  font-family: var(--font-serif); font-size: 1.8rem; font-weight: 900;
  color: var(--color-text); margin-bottom: var(--space-sm); letter-spacing: 0.05em;
}
.hero-inner p { font-size: 0.92rem; color: var(--color-text-secondary); }

.section-block { padding: var(--space-2xl) 0; }
.section-block + .section-block { border-top: 1px solid var(--color-border-light); }
.free-section { background: var(--color-bg-alt); }

.section-title {
  font-family: var(--font-serif); font-size: 1.15rem; font-weight: 700;
  color: var(--color-text); margin-bottom: var(--space-lg); letter-spacing: 0.03em;
}

.card-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-md); }

.hw-card, .free-card {
  padding: var(--space-lg); background: var(--color-bg-card);
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
}
.hw-card h3, .free-card h3 {
  font-family: var(--font-serif); font-size: 1rem; font-weight: 700;
  color: var(--color-text); margin-bottom: var(--space-md); letter-spacing: 0.03em;
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
.hw-num { display: block; font-size: 1.5rem; font-weight: 800; }
.hw-stat.done .hw-num { color: #10b981; }
.hw-stat.pending .hw-num { color: #f59e0b; }
.hw-label { font-size: 0.75rem; color: var(--color-text-muted); }

.hw-expired-tip {
  display: block;
  font-size: 0.65rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.free-row { display: flex; align-items: center; gap: var(--space-md); }
.free-stat { font-size: 0.8rem; color: var(--color-text-secondary); }

.go-btn {
  padding: 6px 20px; font-size: 0.85rem; font-weight: 600; color: white;
  background: var(--color-practice); border-radius: var(--radius-full);
  transition: all var(--duration-fast); margin-left: auto;
}
.go-btn:hover { opacity: 0.9; transform: translateY(-1px); }

.empty-state { text-align: center; padding: var(--space-4xl) 0; color: var(--color-text-muted); font-size: 0.9rem; }
.empty-hint { text-align: center; padding: var(--space-2xl) 0; color: var(--color-text-muted); font-size: 0.9rem; }

@media (max-width: 768px) { .card-grid { grid-template-columns: 1fr; } }
</style>

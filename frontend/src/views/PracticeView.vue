<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getChapters, type Chapter } from '@/api/chapter'
import { getQuizStats, getQuizHistory } from '@/api/quiz'

const router = useRouter()
const activeChapter = ref<number | null>(null)
const loading = ref(true)

const stats = ref([
  { label: '总题数', value: '0', icon: '&#9632;' },
  { label: '已练习', value: '0', icon: '&#9733;' },
  { label: '正确率', value: '0%', icon: '&#9670;' },
  { label: '今日练习', value: '0', icon: '&#9679;' },
])

const chapters = ref<Chapter[]>([])
const recentExercises = ref<any[]>([])

onMounted(async () => {
  try {
    const [quizStats, chs, history] = await Promise.all([
      getQuizStats(),
      getChapters(),
      getQuizHistory(5),
    ])
    stats.value = [
      { label: '总题数', value: String(quizStats.total_questions), icon: '&#9632;' },
      { label: '已练习', value: String(quizStats.questions_done), icon: '&#9733;' },
      { label: '正确率', value: `${quizStats.accuracy}%`, icon: '&#9670;' },
      { label: '今日练习', value: String(quizStats.today_count), icon: '&#9679;' },
    ]
    chapters.value = chs
    recentExercises.value = history.map((h: any) => ({
      chapter: '',
      title: h.stem || '练习题目',
      type: h.user_answer ? '选择题' : '填空题',
      result: h.is_correct ? 'correct' : 'wrong',
    }))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="practice-page">
    <!-- Page hero -->
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1>练 · 学以致用</h1>
          <p>在线练习，以题促学，巩固 AI 知识</p>
        </div>
      </div>
    </section>

    <!-- Quick stats -->
    <section class="stats-section">
      <div class="container">
        <div class="stats-grid">
          <div v-for="stat in stats" :key="stat.label" class="stat-card">
            <div class="stat-value" v-html="stat.value"></div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Question type intro -->
    <section class="types-section">
      <div class="container">
        <div class="section-header">
          <h2>题型说明</h2>
          <p>练习以选择题和填空（计算）题为主，方便即时批改反馈</p>
        </div>
        <div class="types-grid">
          <div class="type-card">
            <div class="type-icon choice-icon">A</div>
            <h3>选择题</h3>
            <p>四选一单选题，考查概念理解与知识记忆。提交即刻显示答案与解析。</p>
            <div class="type-count">共 205 题</div>
          </div>
          <div class="type-card">
            <div class="type-icon fill-icon">—</div>
            <h3>填空题</h3>
            <p>关键词填空与简单计算，考查知识点掌握与计算能力。支持数值精确匹配。</p>
            <div class="type-count">共 115 题</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Chapter exercises -->
    <section class="chapters-section">
      <div class="container">
        <div class="section-header">
          <h2>按章节练习</h2>
          <p>选择章节开始针对性练习，系统自动记录答题进度</p>
        </div>
        <div class="chapters-grid">
          <div
            v-for="ch in chapters"
            :key="ch.num"
            class="chapter-card"
            :class="{ locked: ch.status === '即将发布' }"
            @mouseenter="activeChapter = Number(ch.num)"
            @mouseleave="activeChapter = null"
          >
            <div class="chapter-header">
              <span class="chapter-num">{{ ch.num }}</span>
              <el-tag
                :type="ch.status === '已发布' ? 'success' : 'info'"
                size="small"
                effect="plain"
              >
                {{ ch.status }}
              </el-tag>
            </div>

            <h3 class="chapter-title">{{ ch.title }}</h3>

            <div class="chapter-types">
              <span v-for="t in ch.types" :key="t.name" class="type-tag">
                <span class="type-letter">{{ t.icon }}</span>
                {{ t.name }} {{ t.count }}题
              </span>
            </div>

            <div class="chapter-progress">
              <div class="progress-bar-wrapper">
                <el-progress
                  :percentage="ch.total > 0 ? Math.round(ch.done / ch.total * 100) : 0"
                  :stroke-width="6"
                  :show-text="false"
                  color="var(--color-practice)"
                />
              </div>
              <div class="progress-info">
                <span>已完成 {{ ch.done }}/{{ ch.total }}</span>
                <span v-if="ch.accuracy > 0">正确率 {{ ch.accuracy }}%</span>
              </div>
            </div>

            <button
              class="chapter-btn"
              :disabled="ch.status === '即将发布'"
              @click="ch.status === '已发布' && router.push(`/practice/quiz/${ch.num}`)"
            >
              {{ ch.status === '已发布' ? '开始练习' : '敬请期待' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Recent exercises -->
    <section class="recent-section">
      <div class="container">
        <div class="section-header">
          <h2>最近练习</h2>
          <p>回顾最近的答题记录，巩固薄弱知识点</p>
        </div>
        <div class="recent-list">
          <div
            v-for="(item, index) in recentExercises"
            :key="index"
            class="recent-item"
          >
            <div class="recent-result" :class="item.result">
              <svg v-if="item.result === 'correct'" width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="recent-content">
              <div class="recent-title">{{ item.title }}</div>
              <div class="recent-meta">
                <span>{{ item.chapter }}</span>
                <span class="meta-divider">·</span>
                <span>{{ item.type }}</span>
              </div>
            </div>
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

/* Page hero */
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
  background: linear-gradient(135deg, var(--color-practice-light), var(--color-practice));
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

/* Stats */
.stats-section {
  padding: var(--space-xl) 0;
  margin-top: calc(-1 * var(--space-xl));
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}

.stat-card {
  text-align: center;
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--color-practice);
  margin-bottom: var(--space-xs);
}

.stat-label {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

/* Section header */
.section-header {
  margin-bottom: var(--space-xl);
}

.section-header h2 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.section-header p {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
}

/* Question types */
.types-section {
  padding: var(--space-3xl) 0;
  background: var(--color-bg-alt);
}

.types-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-xl);
}

.type-card {
  padding: var(--space-2xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--duration-normal) var(--ease-out);
}

.type-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.type-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: 900;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-md);
}

.choice-icon {
  color: var(--color-practice);
  background: var(--color-practice-bg);
  border: 1px solid rgba(139, 92, 246, 0.15);
}

.fill-icon {
  color: var(--color-create);
  background: var(--color-create-bg);
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.type-card h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.type-card p {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-md);
}

.type-count {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-practice);
}

/* Chapters */
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
  margin-bottom: var(--space-md);
}

.chapter-types {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
}

.type-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 0.25rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-practice);
  background: var(--color-practice-bg);
  border-radius: var(--radius-full);
  border: 1px solid rgba(139, 92, 246, 0.15);
}

.type-letter {
  font-weight: 800;
  font-size: 0.7rem;
}

.chapter-progress {
  margin-bottom: var(--space-lg);
}

.progress-info {
  display: flex;
  justify-content: space-between;
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
  background: var(--color-practice);
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

/* Recent exercises */
.recent-section {
  padding: var(--space-3xl) 0;
  background: var(--color-bg-alt);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.recent-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) var(--ease-out);
}

.recent-item:hover {
  border-color: var(--color-practice);
  box-shadow: var(--shadow-sm);
}

.recent-result {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.recent-result.correct {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.recent-result.wrong {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.recent-content {
  flex: 1;
  min-width: 0;
}

.recent-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-meta {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.meta-divider {
  margin: 0 var(--space-xs);
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .types-grid,
  .chapters-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

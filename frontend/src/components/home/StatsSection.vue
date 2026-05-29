<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Stat {
  value: number
  label: string
  suffix: string
  desc: string
}

const stats: Stat[] = [
  { value: 6, label: '课程模块', suffix: '个', desc: '系统知识体系' },
  { value: 100, label: '练习题目', suffix: '+', desc: '强化思维反思' },
  { value: 50, label: '学生作品', suffix: '+', desc: '践行创作成果' },
  { value: 20, label: '公益行动', suffix: '+', desc: '感悟社会价值' },
]

const counters = ref<number[]>(stats.map(() => 0))
const sectionVisible = ref(false)

function animateCounters() {
  stats.forEach((stat, i) => {
    const target = stat.value
    const duration = 2000
    const step = target / (duration / 16)
    let current = 0

    const timer = setInterval(() => {
      current += step
      if (current >= target) {
        counters.value[i] = target
        clearInterval(timer)
      } else {
        counters.value[i] = Math.floor(current)
      }
    }, 16)
  })
}

onMounted(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && !sectionVisible.value) {
        sectionVisible.value = true
        animateCounters()
      }
    },
    { threshold: 0.3 }
  )

  const el = document.querySelector('.stats-section')
  if (el) observer.observe(el)
})
</script>

<template>
  <section class="stats-section">
    <div class="container">
      <div class="stats-grid fade-up">
        <div
          v-for="(stat, index) in stats"
          :key="stat.label"
          class="stat-card"
          :style="{ transitionDelay: `${index * 0.1}s` }"
        >
          <div class="stat-value">
            <span class="stat-number">{{ counters[index] }}</span>
            <span class="stat-suffix">{{ stat.suffix }}</span>
          </div>
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-desc">{{ stat.desc }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stats-section {
  padding: var(--space-4xl) 0;
  background: var(--color-bg);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-xl);
}

.stat-card {
  text-align: center;
  padding: var(--space-2xl) var(--space-lg);
  border-radius: var(--radius-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  transition: all var(--duration-normal) var(--ease-out);
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

.stat-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
  margin-bottom: var(--space-sm);
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 900;
  color: var(--color-primary);
  font-family: var(--font-mono);
  line-height: 1;
}

.stat-suffix {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-primary-light);
}

.stat-label {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.stat-desc {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<script setup lang="ts">
import { defineAsyncComponent, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPortfolio, type PortfolioData } from '@/api/portfolio'

const PortfolioRadarChart = defineAsyncComponent(() => import('@/components/portfolio/PortfolioRadarChart.vue'))

const router = useRouter()
const loading = ref(true)

const student = ref({ name: '', major: '', grade: '2025 级', avatar: '' })
const stats = ref([
  { label: '学习时长', value: '0h', color: 'var(--color-learn)' },
  { label: '练习题数', value: '0', color: 'var(--color-practice)' },
  { label: '正确率', value: '0%', color: 'var(--color-create)' },
  { label: '作品数量', value: '0', color: 'var(--color-act)' },
])

const radarOption = ref({
  tooltip: {},
  radar: {
    indicator: [
      { name: '理论基础', max: 100, alignTicks: false },
      { name: '实践能力', max: 100, alignTicks: false },
      { name: '创新思维', max: 100, alignTicks: false },
      { name: '团队协作', max: 100, alignTicks: false },
      { name: '社会传播', max: 100, alignTicks: false },
      { name: '伦理意识', max: 100, alignTicks: false },
    ],
    shape: 'polygon',
    splitNumber: 5,
    axisName: { color: '#475569', fontSize: 12 },
    axisLabel: { show: false },
    splitLine: { lineStyle: { color: '#e2e8f0' } },
    splitArea: { areaStyle: { color: ['rgba(139,92,246,0.02)', 'rgba(139,92,246,0.04)'] } },
    axisLine: { lineStyle: { color: '#e2e8f0' } },
  },
  series: [{
    type: 'radar',
    data: [{
      value: [0, 0, 0, 0, 0, 0],
      name: '能力画像',
      areaStyle: { color: 'rgba(139, 92, 246, 0.15)' },
      lineStyle: { color: '#8b5cf6', width: 2 },
      itemStyle: { color: '#8b5cf6' },
    }],
  }],
})

const timeline = ref<{ date: string; title: string; type: string; color: string }[]>([])
const myProjects = ref<{ id: number; title: string; tags: string[] }[]>([])

const typeColorMap: Record<string, string> = {
  learn: 'var(--color-learn)',
  practice: 'var(--color-practice)',
  create: 'var(--color-create)',
  act: 'var(--color-act)',
}

onMounted(async () => {
  try {
    const data = await getPortfolio()
    student.value = { name: data.user.name, major: data.user.major || '', grade: data.user.grade || '', avatar: '' }
    stats.value = [
      { label: '学习时长', value: `${data.stats.study_hours}h`, color: 'var(--color-learn)' },
      { label: '练习题数', value: String(data.stats.total_exercises), color: 'var(--color-practice)' },
      { label: '正确率', value: `${data.stats.accuracy}%`, color: 'var(--color-create)' },
      { label: '作品数量', value: String(data.stats.project_count), color: 'var(--color-act)' },
    ]
    if (data.radar) {
      const keys = ['理论基础', '实践能力', '创新思维', '团队协作', '社会传播', '伦理意识']
      const series = radarOption.value.series[0]!
      const radarData = series.data[0]!
      radarData.value = keys.map(k => data.radar![k] || 0)
    }
    timeline.value = (data.timeline || []).map(t => ({
      date: t.date,
      title: t.title,
      type: t.type,
      color: typeColorMap[t.type] || 'var(--color-learn)',
    }))
    myProjects.value = (data.projects || []).map(p => ({
      id: p.id,
      title: p.title,
      tags: p.tags,
    }))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="portfolio-page">
    <!-- Hero -->
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="avatar-placeholder">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1>{{ student.name }}</h1>
          <p>{{ student.major }} · {{ student.grade }}</p>
        </div>
      </div>
    </section>

    <!-- Stats -->
    <section class="stats-section">
      <div class="container">
        <div class="stats-grid">
          <div v-for="stat in stats" :key="stat.label" class="stat-card">
            <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Radar chart -->
    <section class="radar-section">
      <div class="container">
        <h2 class="section-title">能力画像</h2>
        <div class="radar-card">
          <PortfolioRadarChart :option="radarOption" />
        </div>
      </div>
    </section>

    <!-- Timeline -->
    <section class="timeline-section">
      <div class="container">
        <h2 class="section-title">成长时间轴</h2>
        <div class="timeline">
          <div v-for="(item, i) in timeline" :key="i" class="timeline-item">
            <div class="timeline-dot" :style="{ background: item.color }"></div>
            <div class="timeline-content">
              <span class="timeline-date">{{ item.date }}</span>
              <p class="timeline-title">{{ item.title }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- My projects -->
    <section class="projects-section">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">我的作品</h2>
          <button class="view-all" @click="router.push('/create')">查看全部 →</button>
        </div>
        <div class="projects-grid">
          <div
            v-for="p in myProjects"
            :key="p.id"
            class="project-card"
            @click="router.push(`/create/project/${p.id}`)"
          >
            <div class="project-image">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                      stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="project-info">
              <h4>{{ p.title }}</h4>
              <div class="project-tags">
                <span v-for="t in p.tags" :key="t">{{ t }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.portfolio-page {
  padding-top: 60px;
}

.page-hero {
  padding: var(--space-3xl) 0 var(--space-2xl);
  background: var(--color-practice-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.hero-inner {
  text-align: center;
}

.avatar-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  background: var(--color-practice);
  border-radius: 50%;
  color: white;
  margin-bottom: var(--space-md);
  box-shadow: 0 4px 14px rgba(107, 76, 138, 0.2);
}

.hero-inner h1 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0;
  text-wrap: balance;
}

.hero-inner p {
  font-size: var(--text-muted);
  line-height: var(--leading-body);
  color: var(--color-text-secondary);
}

/* Stats */
.stats-section {
  padding: var(--space-xl) 0;
  margin-top: calc(-1 * var(--space-lg));
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
  box-shadow: var(--shadow-md);
}

.stat-value {
  font-size: 1.7rem;
  font-weight: 900;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  margin-bottom: var(--space-xs);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  letter-spacing: 0.03em;
}

/* Section title */
.section-title {
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-xl);
  letter-spacing: 0;
}

/* Radar */
.radar-section {
  padding: var(--space-3xl) 0;
}

.radar-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  max-width: 600px;
  margin: 0 auto;
}

/* Timeline */
.timeline-section {
  padding: var(--space-3xl) 0;
  background: var(--color-bg-alt);
}

.timeline {
  max-width: 600px;
  margin: 0 auto;
  position: relative;
  padding-left: 32px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 0;
  bottom: 0;
  width: 1.5px;
  background: var(--color-border);
}

.timeline-item {
  position: relative;
  padding-bottom: var(--space-lg);
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -32px;
  top: 4px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 3px solid var(--color-bg-alt);
  z-index: 1;
}

.timeline-date {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 2px;
}

.timeline-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
}

/* Projects */
.projects-section {
  padding: var(--space-3xl) 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
}

.section-header .section-title {
  margin-bottom: 0;
}

.view-all {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-practice);
  letter-spacing: 0.03em;
  transition: opacity var(--duration-fast);
}

.view-all:hover {
  opacity: 0.7;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.project-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.project-image {
  aspect-ratio: 16 / 10;
  background: var(--color-bg-alt);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.project-info {
  padding: var(--space-md);
}

.project-info h4 {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-compact);
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  letter-spacing: 0;
}

.project-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.project-tags span {
  font-size: 0.65rem;
  padding: 0.12rem 0.45rem;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-sm);
}

@media (max-width: 1024px) {
  .projects-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .projects-grid {
    grid-template-columns: 1fr;
  }
}
</style>

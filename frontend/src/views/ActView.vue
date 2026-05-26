<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getShowcase } from '../api/showcase'
import type { ShowcaseItemOut } from '../api/showcase'
import { getProjects } from '../api/project'
import type { Project } from '../api/project'

const router = useRouter()

// ── 动态展示数据 ────────────────────────────────────
const loading = ref(false)
const loadError = ref(false)
const showcaseData = ref<Record<string, ShowcaseItemOut[]>>({})
const studentProjects = ref<Project[]>([])

// 页面挂载时并行加载展示内容与学生作品
onMounted(async () => {
  loading.value = true
  loadError.value = false
  try {
    const [showcase, projects] = await Promise.all([getShowcase(), getProjects()])
    showcaseData.value = showcase || {}
    // 仅展示前 6 条已通过审核的作品
    studentProjects.value = (projects || [])
      .filter((p) => p.status === 'approved')
      .slice(0, 6)
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})

const actionSteps = [
  {
    num: '01',
    title: '理解真实问题',
    desc: '从社区、学校和课程项目中选择一个具体问题，先明确对象、场景和限制条件。',
  },
  {
    num: '02',
    title: '设计 AI 方案',
    desc: '把课堂学到的 AI 工具、调研方法和表达方式整理成可执行的小方案。',
  },
  {
    num: '03',
    title: '服务并复盘',
    desc: '在公益课、读书会和项目实践中记录反馈，形成可复盘的学习材料。',
  },
]

const outcomeCards = [
  {
    id: 'public-class',
    icon: '🏫',
    title: 'AI 公益课',
    subtitle: '走进社区与中小学',
    desc: '面向青少年和社区居民开展 AI 启蒙，练习把知识讲清楚。',
    count: '20+',
    label: '场公益课',
  },
  {
    id: 'reading-club',
    icon: '📚',
    title: '读书会',
    subtitle: '围绕 AI 主题开展共读',
    desc: '通过阅读、分享和讨论，训练学生提问、表达和形成观点的能力。',
    count: '12',
    label: '期读书会',
  },
  {
    id: 'field-project',
    icon: '🌍',
    title: '落地项目',
    subtitle: '完成项目实践与展示',
    desc: '把课堂知识转化为调研报告、活动方案、工具原型和展示材料。',
    count: '8',
    label: '个落地项目',
  },
]

// outcomeDetails 静态数据已替换为动态展示，详见下方模板内的三个板块

const portfolioFeatures = [
  { label: '学习时长', color: 'var(--color-learn)' },
  { label: '练习正确率', color: 'var(--color-primary)' },
  { label: '创意作品', color: 'var(--color-create)' },
  { label: '公益参与', color: 'var(--color-act)' },
]

function scrollToOutcome(id: string) {
  document.getElementById(id)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

function startAction() {
  document.getElementById('action-path')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}
</script>

<template>
  <div class="act-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path
                d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.841m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
          <h1>行 · 知行合一</h1>
          <p>把课堂学习延伸到社区、学校和项目实践中，记录每一次行动带来的成长。</p>
          <div class="hero-actions">
            <el-button type="success" size="large" round @click="startAction">
              开始开展行动
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <section id="action-path" class="path-section">
      <div class="container">
        <div class="section-header">
          <span class="section-kicker">行动路径</span>
          <h2>一次行动如何发生</h2>
          <p>先明确问题，再设计 AI 辅助方案，最后记录过程和反馈。</p>
        </div>

        <div class="steps-grid">
          <div v-for="step in actionSteps" :key="step.num" class="step-card">
            <span class="step-num">{{ step.num }}</span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="outcomes-nav-section">
      <div class="container">
        <div class="section-header compact">
          <span class="section-kicker">行动成果</span>
          <h2>三类成果在同一页查看</h2>
          <p>点击任意成果卡片，查看对应的介绍、数据和案例。</p>
        </div>

        <div class="outcome-card-grid">
          <button
            v-for="outcome in outcomeCards"
            :key="outcome.id"
            class="outcome-card"
            type="button"
            @click="scrollToOutcome(outcome.id)"
          >
            <span class="outcome-icon">{{ outcome.icon }}</span>
            <span class="outcome-body">
              <span class="outcome-title">{{ outcome.title }}</span>
              <span class="outcome-subtitle">{{ outcome.subtitle }}</span>
              <span class="outcome-desc">{{ outcome.desc }}</span>
              <span class="outcome-stat">
                <strong>{{ outcome.count }}</strong>
                <span>{{ outcome.label }}</span>
              </span>
            </span>
          </button>
        </div>
      </div>
    </section>

    <!-- ── 板块二：公益课社会价值 ──────────────── -->
    <section id="public-class" class="welfare-section">
      <div class="container">
        <div class="section-header">
          <span class="section-kicker">公益课</span>
          <h2>AI 公益课：社会价值实践</h2>
          <p>学生团队走进社区与中小学，将 AI 知识带给更多人。</p>
        </div>
        <div v-if="loading" class="dynamic-state">加载中...</div>
        <div v-else-if="loadError" class="dynamic-state dynamic-error">加载失败，请刷新页面重试</div>
        <div v-else-if="(showcaseData['welfare'] || []).length === 0" class="dynamic-state">内容建设中，敬请期待</div>
        <div v-else class="showcase-grid">
          <div
            v-for="item in (showcaseData['welfare'] || [])"
            :key="item.id"
            class="showcase-card"
          >
            <div v-if="item.cover_url" class="showcase-cover">
              <img :src="item.cover_url" :alt="item.title" />
            </div>
            <div class="showcase-body">
              <div class="showcase-title">{{ item.title }}</div>
              <div v-if="item.content" class="showcase-content">{{ item.content }}</div>
              <a
                v-if="item.link_url"
                :href="item.link_url"
                target="_blank"
                rel="noopener"
                class="showcase-link"
              >了解详情 →</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── 板块三：读书会活动 ────────────────── -->
    <section id="reading-club" class="reading-section">
      <div class="container">
        <div class="section-header">
          <span class="section-kicker">读书会</span>
          <h2>读书会：阅读与讨论</h2>
          <p>围绕 AI 主题展开共读，训练提问、表达和观点形成能力。</p>
        </div>
        <div v-if="loading" class="dynamic-state">加载中...</div>
        <div v-else-if="loadError" class="dynamic-state dynamic-error">加载失败，请刷新页面重试</div>
        <div v-else-if="(showcaseData['reading_club'] || []).length === 0" class="dynamic-state">内容建设中，敬请期待</div>
        <div v-else class="showcase-grid">
          <div
            v-for="item in (showcaseData['reading_club'] || [])"
            :key="item.id"
            class="showcase-card"
          >
            <div v-if="item.cover_url" class="showcase-cover">
              <img :src="item.cover_url" :alt="item.title" />
            </div>
            <div class="showcase-body">
              <div class="showcase-title">{{ item.title }}</div>
              <div v-if="item.content" class="showcase-content">{{ item.content }}</div>
              <a
                v-if="item.link_url"
                :href="item.link_url"
                target="_blank"
                rel="noopener"
                class="showcase-link"
              >了解详情 →</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── 板块一：实践作品展示 ───────────────── -->
    <section id="field-project" class="projects-showcase-section">
      <div class="container">
        <div class="section-header">
          <span class="section-kicker">落地项目</span>
          <h2>同学们的实践成果</h2>
          <p>完成大作业的同学，他们的作品在这里展示。</p>
        </div>
        <div v-if="loading" class="dynamic-state">加载中...</div>
        <div v-else-if="loadError" class="dynamic-state dynamic-error">加载失败，请刷新页面重试</div>
        <div v-else-if="studentProjects.length === 0" class="dynamic-state">暂无作品，快去提交你的大作业吧！</div>
        <div v-else class="project-grid">
          <div
            v-for="project in studentProjects"
            :key="project.id"
            class="project-card"
            @click="router.push(`/create/project/${project.id}`)"
          >
            <div class="project-cover">
              <img v-if="project.image_url" :src="project.image_url" :alt="project.title" />
              <div v-else class="project-cover-placeholder"></div>
            </div>
            <div class="project-body">
              <div class="project-title">{{ project.title }}</div>
              <div class="project-author">{{ project.author_name }}</div>
              <div class="project-desc">
                {{
                  project.description
                    ? project.description.slice(0, 80) + (project.description.length > 80 ? '...' : '')
                    : ''
                }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="portfolio-section">
      <div class="container">
        <div class="portfolio-card">
          <div class="portfolio-content">
            <span class="section-kicker">成长沉淀</span>
            <h3>查看我的成长档案</h3>
            <p>公益课、读书会和落地项目中的参与记录，会和学习、练习、创作数据一起形成个人成长记录。</p>
            <div class="portfolio-features">
              <span v-for="feature in portfolioFeatures" :key="feature.label" class="pf-item">
                <span class="pf-dot" :style="{ background: feature.color }"></span>
                {{ feature.label }}
              </span>
            </div>
          </div>
          <el-button type="success" size="large" round @click="router.push('/portfolio')">
            打开成长档案
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.act-page {
  padding-top: 64px;
}

.page-hero {
  padding: var(--space-3xl) 0;
  background: var(--color-act-bg);
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
  background: linear-gradient(135deg, var(--color-act-light), var(--color-act));
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
  max-width: 560px;
  margin: 0 auto;
  font-size: 1.05rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.hero-actions {
  margin-top: var(--space-xl);
}

.path-section,
.outcomes-nav-section,
.outcome-details-section,
.portfolio-section {
  padding: var(--space-3xl) 0;
}

.outcomes-nav-section,
.portfolio-section {
  background: var(--color-bg-alt);
}

.section-header {
  max-width: 640px;
  margin-bottom: var(--space-2xl);
}

.section-header.compact {
  margin-bottom: var(--space-xl);
}

.section-kicker {
  display: inline-block;
  margin-bottom: var(--space-xs);
  color: var(--color-act);
  font-size: 0.8rem;
  font-weight: 700;
}

.section-header h2 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.section-header p {
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.step-card {
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.step-num {
  display: inline-flex;
  margin-bottom: var(--space-lg);
  color: var(--color-act);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 900;
}

.step-card h3 {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.step-card p {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  line-height: 1.7;
}

.outcome-card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.outcome-card {
  display: flex;
  width: 100%;
  gap: var(--space-md);
  padding: var(--space-xl);
  text-align: left;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
}

.outcome-card:hover {
  transform: translateY(-2px);
  border-color: var(--color-act-light);
  box-shadow: var(--shadow-md);
}

.outcome-card:focus-visible {
  outline: 3px solid var(--color-act-light);
  outline-offset: 3px;
}

.outcome-icon {
  flex-shrink: 0;
  font-size: 2.2rem;
  line-height: 1;
}

.outcome-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.outcome-title {
  color: var(--color-text);
  font-size: 1.1rem;
  font-weight: 800;
}

.outcome-subtitle {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 600;
}

.outcome-desc {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  line-height: 1.6;
}

.outcome-stat {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
  margin-top: var(--space-sm);
}

.outcome-stat strong {
  color: var(--color-act);
  font-family: var(--font-mono);
  font-size: 1.5rem;
  font-weight: 900;
}

.outcome-stat span {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.outcome-details-section {
  background: var(--color-bg-card);
}

.detail-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-2xl);
  padding: var(--space-2xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  scroll-margin-top: 96px;
}

.detail-panel + .detail-panel {
  margin-top: var(--space-xl);
}

.detail-badge {
  display: inline-flex;
  margin-bottom: var(--space-md);
  padding: 0.25rem 0.7rem;
  color: var(--color-act);
  background: var(--color-act-bg);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 700;
}

.detail-main h2 {
  color: var(--color-text);
  font-size: 1.45rem;
  font-weight: 800;
  margin-bottom: var(--space-md);
}

.detail-main p {
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.detail-highlights {
  margin-top: var(--space-xl);
}

.detail-highlights h3,
.case-box h3 {
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 800;
  margin-bottom: var(--space-md);
}

.detail-highlights ul {
  display: grid;
  gap: var(--space-sm);
  padding-left: 1.2rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.detail-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm);
}

.detail-stat {
  padding: var(--space-md);
  background: var(--color-act-bg);
  border-radius: var(--radius-md);
  text-align: center;
}

.detail-stat strong {
  display: block;
  color: var(--color-act);
  font-family: var(--font-mono);
  font-size: 1.3rem;
  font-weight: 900;
  margin-bottom: 0.1rem;
}

.detail-stat span {
  color: var(--color-text-secondary);
  font-size: 0.78rem;
}

.case-box {
  padding: var(--space-lg);
  background: var(--color-bg-alt);
  border-radius: var(--radius-lg);
}

.case-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.case-item {
  padding: 0.35rem 0.7rem;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
}

.portfolio-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-xl);
  padding: var(--space-xl) var(--space-2xl);
  background: var(--color-act-bg);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-lg);
}

.portfolio-content h3 {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.portfolio-content p {
  max-width: 640px;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-md);
}

.portfolio-features {
  display: flex;
  gap: var(--space-lg);
  flex-wrap: wrap;
}

.pf-item {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.pf-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

@media (max-width: 960px) {
  .steps-grid,
  .outcome-card-grid,
  .detail-panel {
    grid-template-columns: 1fr;
  }

  .detail-side {
    max-width: none;
  }
}

@media (max-width: 768px) {
  .section-header {
    text-align: left;
  }

  .outcome-card {
    flex-direction: column;
  }

  .detail-panel {
    padding: var(--space-xl);
  }

  .detail-stats {
    grid-template-columns: 1fr;
  }

  .portfolio-card {
    flex-direction: column;
    align-items: flex-start;
  }
}

/* ── 三个动态内容板块 ─────────────────────────── */
.welfare-section,
.reading-section,
.projects-showcase-section {
  padding: var(--space-3xl) 0;
  scroll-margin-top: 96px;
}

/* 交替背景色 */
.welfare-section {
  background: var(--color-bg-alt);
}
.reading-section {
  background: var(--color-bg-card);
}
.projects-showcase-section {
  background: var(--color-bg-alt);
}

/* 加载/错误/空状态文本 */
.dynamic-state {
  text-align: center;
  padding: var(--space-2xl) 0;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}
.dynamic-error {
  color: #f56c6c;
}

/* 公益课 / 读书会 展示卡片 */
.showcase-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-lg);
}

.showcase-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: box-shadow var(--duration-fast);
}

.welfare-section .showcase-card {
  background: var(--color-bg-card);
}
.reading-section .showcase-card {
  background: var(--color-bg-alt);
}

.showcase-card:hover {
  box-shadow: var(--shadow-md);
}

.showcase-cover {
  aspect-ratio: 16 / 9;
  overflow: hidden;
}

.showcase-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.showcase-body {
  padding: var(--space-lg);
}

.showcase-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.showcase-content {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-md);
}

.showcase-link {
  display: inline-block;
  color: var(--color-act);
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: opacity var(--duration-fast);
}

.showcase-link:hover {
  opacity: 0.75;
}

/* 实践作品展示 */
.project-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.project-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
}

.project-card:hover {
  transform: translateY(-2px);
  border-color: var(--color-act-light);
  box-shadow: var(--shadow-md);
}

.project-cover {
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: var(--color-act-bg);
}

.project-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.project-cover-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--color-act-bg), var(--color-act-light));
  opacity: 0.6;
}

.project-body {
  padding: var(--space-md);
}

.project-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-author {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-xs);
}

.project-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 960px) {
  .project-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .project-grid {
    grid-template-columns: 1fr;
  }
}
</style>

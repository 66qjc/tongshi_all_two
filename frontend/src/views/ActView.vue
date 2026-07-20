<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getShowcase } from '../api/showcase'
import type { ShowcaseItemOut } from '../api/showcase'
import { getProjects } from '../api/project'
import type { Project } from '../api/project'
import AuthenticatedFileImage from '@/components/common/AuthenticatedFileImage.vue'

const router = useRouter()

// ── 动态展示数据 ────────────────────────────────────
const loading = ref(false)
const loadError = ref(false)
const projectLoadError = ref(false)
const showcaseData = ref<Record<string, ShowcaseItemOut[]>>({})
const studentProjects = ref<Project[]>([])

// 页面挂载时分别加载公开展示与已审作品；游客也可浏览作品广场。
onMounted(async () => {
  loading.value = true
  loadError.value = false
  projectLoadError.value = false
  try {
    const showcase = await getShowcase()
    showcaseData.value = showcase || {}
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }

  try {
    const projectRes = await getProjects()
    // 仅展示前 6 条已通过审核的作品
    studentProjects.value = (projectRes?.items || []).slice(0, 6)
  } catch {
    projectLoadError.value = true
  }
})

const outcomeCards = [
  {
    id: 'public-class',
    icon: '🏫',
    title: 'AI 公益课',
    subtitle: '走进社区与中小学',
    desc: '面向青少年和社区居民开展 AI 启蒙，练习把知识讲清楚。',
  },
  {
    id: 'reading-club',
    icon: '📚',
    title: '读书会',
    subtitle: '围绕 AI 主题开展共读',
    desc: '通过阅读、分享和讨论，训练学生提问、表达和形成观点的能力。',
  },
  {
    id: 'field-project',
    icon: '🌍',
    title: '落地项目',
    subtitle: '完成项目实践与展示',
    desc: '把课堂知识转化为调研报告、活动方案、工具原型和展示材料。',
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

function scrollToOutcomes() {
  document.getElementById('action-outcomes')?.scrollIntoView({
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
          <h1>悟 · 感悟价值</h1>
          <p>把课堂学习延伸到社区、学校和项目实践中，记录每一次行动带来的成长。</p>
          <div class="hero-actions">
            <el-button type="success" size="large" round @click="scrollToOutcomes">
              开始开展行动
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <section id="action-outcomes" class="outcomes-nav-section">
      <div class="container">
        <div class="section-header">
          <span class="section-kicker">行动成果</span>
          <h2>公益课 · 读书会 · 项目实践</h2>
          <p>点击下方卡片，即可定位到对应板块，浏览活动介绍与实践案例。</p>
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
              <button
                type="button"
                class="showcase-link"
                @click="router.push(`/act/showcase/${item.id}`)"
              >了解详情 →</button>
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
              <button
                type="button"
                class="showcase-link"
                @click="router.push(`/act/showcase/${item.id}`)"
              >了解详情 →</button>
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
          <h2>课程作品展示</h2>
          <p>浏览同学提交的课程作品与实践报告，了解课堂所学如何落到具体项目中。</p>
        </div>
        <div v-if="loading" class="dynamic-state">加载中...</div>
        <div v-else-if="projectLoadError" class="dynamic-state dynamic-error">作品加载失败，请稍后重试</div>
        <div v-else-if="studentProjects.length === 0" class="dynamic-state">暂无已审核作品，完成课程作业后可在此展示。</div>
        <div v-else class="project-grid">
          <div
            v-for="project in studentProjects"
            :key="project.id"
            class="project-card"
            @click="router.push(`/create/project/${project.id}`)"
          >
            <div class="project-cover">
              <AuthenticatedFileImage
                v-if="project.cover_file_id || project.images?.[0]?.file_id || project.images?.[0]?.image_url || project.image_url"
                :file-id="project.cover_file_id || project.images?.[0]?.file_id"
                :fallback-url="project.images?.[0]?.image_url || project.image_url"
                :alt="project.title"
              />
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
  padding-top: 60px;
}

.page-hero {
  padding: var(--space-3xl) 0 var(--space-2xl);
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
  width: 56px;
  height: 56px;
  background: var(--color-act);
  border-radius: var(--radius-md);
  color: white;
  margin-bottom: var(--space-lg);
  box-shadow: 0 4px 14px rgba(58, 125, 92, 0.2);
}

.hero-inner h1 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  letter-spacing: 0;
  text-wrap: balance;
}

.hero-inner p {
  max-width: 65ch;
  margin: 0 auto;
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

.hero-actions {
  margin-top: var(--space-xl);
}

.outcomes-nav-section,
.portfolio-section {
  padding: var(--space-3xl) 0;
  background: var(--color-bg-alt);
}

.section-header {
  max-width: 640px;
  margin-bottom: var(--space-2xl);
}

.section-kicker {
  display: inline-block;
  margin-bottom: var(--space-xs);
  color: var(--color-act);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.section-header h2 {
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0;
  text-wrap: balance;
}

.section-header p {
  color: var(--color-text-secondary);
  font-size: var(--text-muted);
  line-height: var(--leading-body);
  text-wrap: pretty;
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
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
}

.outcome-card:hover {
  transform: translateY(-2px);
  border-color: rgba(58, 125, 92, 0.25);
  box-shadow: var(--shadow-md);
}

.outcome-card:focus-visible {
  outline: 2px solid var(--color-act);
  outline-offset: 2px;
}

.outcome-icon {
  flex-shrink: 0;
  font-size: 2rem;
  line-height: 1;
}

.outcome-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.outcome-title {
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  letter-spacing: 0;
  text-wrap: balance;
}

.outcome-subtitle {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  font-weight: 600;
}

.outcome-desc {
  color: var(--color-text-secondary);
  font-size: var(--text-muted);
  line-height: var(--leading-body);
  text-wrap: pretty;
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
  border-radius: var(--radius-md);
  scroll-margin-top: 96px;
}

.detail-panel + .detail-panel {
  margin-top: var(--space-xl);
}

.detail-badge {
  display: inline-flex;
  margin-bottom: var(--space-md);
  padding: 0.2rem 0.6rem;
  color: var(--color-act);
  background: var(--color-act-bg);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.detail-main h2 {
  font-family: var(--font-sans);
  color: var(--color-text);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  margin-bottom: var(--space-md);
  letter-spacing: 0;
  text-wrap: balance;
}

.detail-main p {
  color: var(--color-text-secondary);
  font-size: var(--text-muted);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

.detail-highlights {
  margin-top: var(--space-xl);
}

.detail-highlights h3,
.case-box h3 {
  font-family: var(--font-sans);
  color: var(--color-text);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  margin-bottom: var(--space-md);
  letter-spacing: 0;
  text-wrap: balance;
}

.detail-highlights ul {
  display: grid;
  gap: var(--space-sm);
  padding-left: 1.2rem;
  color: var(--color-text-secondary);
  font-size: 0.85rem;
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
  border-radius: var(--radius-sm);
  text-align: center;
}

.detail-stat strong {
  display: block;
  color: var(--color-act);
  font-family: var(--font-mono);
  font-size: 1.2rem;
  font-weight: 900;
  margin-bottom: 0.1rem;
}

.detail-stat span {
  color: var(--color-text-secondary);
  font-size: 0.72rem;
}

.case-box {
  padding: var(--space-lg);
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
}

.case-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.case-item {
  padding: 0.3rem 0.6rem;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
}

.portfolio-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-xl);
  padding: var(--space-xl) var(--space-2xl);
  background: var(--color-act-bg);
  border: 1px solid rgba(58, 125, 92, 0.12);
  border-radius: var(--radius-md);
}

.portfolio-content h3 {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  letter-spacing: 0;
  text-wrap: balance;
}

.portfolio-content p {
  max-width: 640px;
  font-size: 0.85rem;
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
  font-size: 0.78rem;
  color: var(--color-text-secondary);
}

.pf-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

@media (max-width: 960px) {
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

.welfare-section {
  background: var(--color-bg-alt);
}
.reading-section {
  background: var(--color-bg-card);
}
.projects-showcase-section {
  background: var(--color-bg-alt);
}

.dynamic-state {
  text-align: center;
  padding: var(--space-2xl) 0;
  color: var(--color-text-secondary);
  font-size: 0.88rem;
}
.dynamic-error {
  color: #c0392b;
}

.showcase-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-lg);
}

.showcase-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
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
  padding: var(--space-md) var(--space-lg);
}

.showcase-title {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  letter-spacing: 0;
  text-wrap: balance;
}

.showcase-content {
  display: -webkit-box;
  overflow: hidden;
  font-size: 0.82rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-md);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 5;
}

.showcase-link {
  display: inline-block;
  padding: 0;
  color: var(--color-act);
  background: transparent;
  border: 0;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  letter-spacing: 0.03em;
  transition: opacity var(--duration-fast);
}

.showcase-link:hover {
  opacity: 0.75;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.project-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
}

.project-card:hover {
  transform: translateY(-2px);
  border-color: rgba(58, 125, 92, 0.25);
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
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0;
}

.project-author {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-xs);
}

.project-desc {
  font-size: 0.82rem;
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

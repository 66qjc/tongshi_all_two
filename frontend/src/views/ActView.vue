<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const actions = [
  {
    icon: '&#127979;',
    title: 'AI 公益课',
    subtitle: '走进社区与中小学',
    desc: '学生团队走进社区和中小学，为孩子们带来生动有趣的 AI 启蒙课程，将技术的种子播撒到更多人心中。',
    count: '20+',
    label: '场公益课',
  },
  {
    icon: '&#128218;',
    title: '读书会',
    subtitle: '思想碰撞的火花',
    desc: '定期组织 AI 相关书籍读书会，从《生命 3.0》到《智能时代》，在阅读与讨论中深化理解。',
    count: '12',
    label: '期读书会',
  },
  {
    icon: '&#128200;',
    title: 'AI 成长档案',
    subtitle: 'E-Portfolio 数字画像',
    desc: '自动汇聚学习时长、练习正确率、创意作品评价与公益参与度，生成多维度个人能力雷达图。',
    count: '100%',
    label: '覆盖每位学生',
  },
  {
    icon: '&#127758;',
    title: '落地项目',
    subtitle: '服务社会，创造价值',
    desc: '将课堂所学转化为实际的社会服务项目，用 AI 技术解决真实问题，创造可衡量的社会价值。',
    count: '8',
    label: '个落地项目',
  },
]

const timeline = [
  { date: '2026年3月', title: '首期 AI 公益课', desc: '走进西湖区某小学，为三年级学生带来"AI 是什么"启蒙课' },
  { date: '2026年4月', title: '读书会第一期', desc: '共读《生命 3.0：人工智能时代人类的进化与重生》' },
  { date: '2026年5月', title: '硬件作品展', desc: '首届 AI+硬件学生作品展览，12 件作品参展' },
  { date: '2026年6月', title: '社区服务月', desc: '联合三个社区开展"AI 科普进万家"系列活动' },
]
</script>

<template>
  <div class="act-page">
    <!-- Page hero -->
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <div class="hero-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.841m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1>行 · 知行合一</h1>
          <p>用 AI 温暖社会，在行动中看见成长</p>
        </div>
      </div>
    </section>

    <!-- Action cards -->
    <section class="actions-section">
      <div class="container">
        <div class="actions-grid">
          <div
            v-for="action in actions"
            :key="action.title"
            class="action-card"
          >
            <div class="action-icon" v-html="action.icon"></div>
            <div class="action-body">
              <div class="action-header">
                <h3>{{ action.title }}</h3>
                <span class="action-subtitle">{{ action.subtitle }}</span>
              </div>
              <p class="action-desc">{{ action.desc }}</p>
              <div class="action-stat">
                <span class="stat-num">{{ action.count }}</span>
                <span class="stat-label">{{ action.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Timeline -->
    <section class="timeline-section">
      <div class="container">
        <h2 class="section-title">行动时间轴</h2>
        <div class="timeline">
          <div
            v-for="(item, index) in timeline"
            :key="item.date"
            class="timeline-item"
          >
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <span class="timeline-date">{{ item.date }}</span>
              <h4 class="timeline-title">{{ item.title }}</h4>
              <p class="timeline-desc">{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Growth Portfolio CTA -->
    <section class="portfolio-section">
      <div class="container">
        <div class="portfolio-card">
          <div class="portfolio-content">
            <h3>查看我的成长档案</h3>
            <p>AI 成长档案自动汇聚你的学习、练习、创造与行动数据</p>
            <div class="portfolio-features">
              <span class="pf-item">
                <span class="pf-dot" style="background: var(--color-learn)"></span>
                学习时长
              </span>
              <span class="pf-item">
                <span class="pf-dot" style="background: var(--color-primary)"></span>
                练习正确率
              </span>
              <span class="pf-item">
                <span class="pf-dot" style="background: var(--color-create)"></span>
                创意作品
              </span>
              <span class="pf-item">
                <span class="pf-dot" style="background: var(--color-act)"></span>
                公益参与
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

/* Page hero */
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
  font-size: 1.05rem;
  color: var(--color-text-secondary);
}

/* Actions grid */
.actions-section {
  padding: var(--space-3xl) 0;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-xl);
}

.action-card {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--duration-normal) var(--ease-out);
}

.action-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-icon {
  font-size: 2.5rem;
  flex-shrink: 0;
  line-height: 1;
}

.action-body {
  flex: 1;
}

.action-header {
  margin-bottom: var(--space-sm);
}

.action-header h3 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-text);
}

.action-subtitle {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.action-desc {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-md);
}

.action-stat {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
}

.stat-num {
  font-size: 1.5rem;
  font-weight: 900;
  color: var(--color-act);
  font-family: var(--font-mono);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

/* Timeline */
.timeline-section {
  padding: var(--space-3xl) 0;
  background: var(--color-bg-alt);
}

.section-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-2xl);
  text-align: center;
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
  width: 2px;
  background: var(--color-border);
}

.timeline-item {
  position: relative;
  padding-bottom: var(--space-xl);
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -32px;
  top: 4px;
  width: 16px;
  height: 16px;
  background: var(--color-act);
  border-radius: 50%;
  border: 3px solid var(--color-bg-alt);
  z-index: 1;
}

.timeline-date {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-act);
  background: var(--color-act-bg);
  padding: 0.15rem 0.6rem;
  border-radius: var(--radius-full);
  margin-bottom: var(--space-sm);
}

.timeline-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.timeline-desc {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* Portfolio CTA */
.portfolio-section {
  padding: var(--space-3xl) 0;
}

.portfolio-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-xl) var(--space-2xl);
  background: var(--color-act-bg);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-lg);
}

.portfolio-content h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.portfolio-content p {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
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

@media (max-width: 768px) {
  .actions-grid {
    grid-template-columns: 1fr;
  }

  .action-card {
    flex-direction: column;
  }

  .portfolio-card {
    flex-direction: column;
    text-align: center;
    gap: var(--space-lg);
  }

  .portfolio-features {
    justify-content: center;
  }
}
</style>

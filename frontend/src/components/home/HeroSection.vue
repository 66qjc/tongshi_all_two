<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const entries = [
  {
    key: 'learn',
    mark: '学',
    title: '公开学习',
    desc: '浏览 AI 通识课程、图文课时与精选资料。',
    route: '/learn',
    tone: 'learn',
  },
  {
    key: 'practice',
    mark: '思',
    title: '登录练习',
    desc: '登录后完成题目练习，检查理解和错题。',
    route: '/practice',
    tone: 'practice',
  },
  {
    key: 'create',
    mark: '践',
    title: '实践作品',
    desc: '登录后查看作品展示，并提交自己的实践成果。',
    route: '/create',
    tone: 'create',
  },
  {
    key: 'act',
    mark: '悟',
    title: '看行动',
    desc: '查看公益课、读书会与社区行动记录。',
    route: '/act',
    tone: 'act',
  },
]
</script>

<template>
  <section class="hero">
    <div class="container hero-layout">
      <div class="hero-copy">
        <div class="hero-badge">
          <span class="hero-badge-mark" aria-hidden="true">
            <img src="/cjlu-logo.svg" alt="" class="hero-badge-logo" />
          </span>
          <span>中国计量大学 · 深度 AI 通识学习平台</span>
        </div>
        <h1>
          <span>学 · 思 · 践 · 悟</span>
          <strong>AI 通识，从这里开始</strong>
        </h1>
        <p>
          面向所有学习者开放的 AI 通识学习入口，串联基础理论、工具实践、伦理思辨和真实应用。游客可直接浏览公开课程，登录后继续保存学习进度。
        </p>
        <div class="hero-actions">
          <button class="btn-primary" type="button" @click="router.push('/learn')">
            进入公开学习馆
          </button>
          <button class="btn-secondary" type="button" @click="router.push('/login')">
            登录保存进度
          </button>
        </div>
        <div class="suggestion-panel">
          <strong>今日建议</strong>
          <span>先浏览一门公开课程，再进入作业与练习检查理解。</span>
        </div>
      </div>

      <div class="entry-grid" aria-label="学生常用入口">
        <button
          v-for="entry in entries"
          :key="entry.key"
          class="entry-card"
          :class="`entry-${entry.tone}`"
          type="button"
          @click="router.push(entry.route)"
        >
          <span class="entry-mark">{{ entry.mark }}</span>
          <span class="entry-main">
            <strong>{{ entry.title }}</strong>
            <span>{{ entry.desc }}</span>
          </span>
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  padding: calc(60px + var(--space-3xl)) 0 var(--space-2xl);
  background:
    linear-gradient(135deg, rgba(26, 61, 77, 0.96), rgba(45, 90, 110, 0.94)),
    var(--color-primary-dark);
}

.hero-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(360px, 1.05fr);
  gap: var(--space-3xl);
  align-items: center;
}

.hero-copy {
  color: var(--color-bg-card);
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: var(--space-lg);
  padding: 0.32rem 0.72rem;
  color: rgba(255, 253, 248, 0.82);
  background: rgba(255, 253, 248, 0.08);
  border: 1px solid rgba(255, 253, 248, 0.14);
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  font-weight: 700;
}

.hero-badge-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  background: rgba(255, 253, 248, 0.86);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.hero-badge-logo {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.hero-copy h1 {
  margin-bottom: var(--space-lg);
  font-family: var(--font-serif);
  line-height: 1.2;
}

.hero-copy h1 span,
.hero-copy h1 strong {
  display: block;
}

.hero-copy h1 span {
  margin-bottom: var(--space-sm);
  font-size: 1.2rem;
  font-weight: 700;
  color: rgba(255, 253, 248, 0.68);
}

.hero-copy h1 strong {
  max-width: 640px;
  font-size: 3rem;
  font-weight: 900;
  letter-spacing: 0;
}

.hero-copy p {
  max-width: 560px;
  color: rgba(255, 253, 248, 0.72);
  font-size: 1rem;
  line-height: 1.85;
}

.hero-actions {
  display: flex;
  gap: var(--space-md);
  margin-top: var(--space-xl);
  flex-wrap: wrap;
}

.suggestion-panel {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  max-width: 560px;
  margin-top: var(--space-lg);
  padding: 0.9rem 1rem;
  color: rgba(255, 253, 248, 0.78);
  background: rgba(255, 253, 248, 0.08);
  border: 1px solid rgba(255, 253, 248, 0.14);
  border-radius: var(--radius-sm);
}

.suggestion-panel strong {
  flex: 0 0 auto;
  color: var(--color-bg-card);
  font-size: 0.9rem;
}

.suggestion-panel span {
  min-width: 0;
  font-size: 0.86rem;
  line-height: 1.6;
}

.btn-primary,
.btn-secondary {
  padding: 0.78rem 1.4rem;
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  font-weight: 700;
  transition: transform 140ms var(--ease-out), box-shadow 140ms var(--ease-out);
}

.btn-primary {
  color: var(--color-primary-dark);
  background: var(--color-bg-card);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
}

.btn-secondary {
  color: var(--color-bg-card);
  background: rgba(255, 253, 248, 0.08);
  border: 1px solid rgba(255, 253, 248, 0.18);
}

.btn-primary:hover,
.btn-secondary:hover {
  transform: translateY(-1px);
}

.btn-primary:active,
.btn-secondary:active {
  transform: translateY(1px);
  box-shadow: none;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
}

.entry-card {
  display: flex;
  gap: var(--space-md);
  min-height: 156px;
  padding: var(--space-lg);
  color: var(--color-text);
  background: var(--color-bg-card);
  border: 1px solid rgba(255, 253, 248, 0.18);
  border-radius: var(--radius-md);
  text-align: left;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.12);
  transition: transform 160ms var(--ease-out), box-shadow 160ms var(--ease-out);
}

.entry-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.16);
}

.entry-card:active {
  transform: translateY(1px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
}

.entry-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  color: var(--color-bg-card);
  border-radius: var(--radius-sm);
  font-family: var(--font-serif);
  font-weight: 900;
}

.entry-learn .entry-mark {
  background: var(--color-learn);
}

.entry-practice .entry-mark {
  background: var(--color-practice);
}

.entry-create .entry-mark {
  background: var(--color-create);
}

.entry-act .entry-mark {
  background: var(--color-act);
}

.entry-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.entry-main strong {
  color: var(--color-text);
  font-size: 1.02rem;
}

.entry-main span {
  color: var(--color-text-secondary);
  font-size: 0.86rem;
  line-height: 1.65;
}

@media (max-width: 900px) {
  .hero {
    min-height: auto;
    padding: calc(60px + var(--space-2xl)) 0 var(--space-2xl);
  }

  .hero-layout {
    grid-template-columns: 1fr;
    gap: var(--space-2xl);
  }

  .hero-copy h1 strong {
    font-size: 2.2rem;
  }
}

@media (max-width: 768px) {
  .hero {
    padding: calc(60px + var(--space-xl)) 0 var(--space-xl);
  }

  .entry-grid {
    grid-template-columns: 1fr;
  }

  .entry-card {
    min-height: auto;
  }

  .suggestion-panel {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--space-xs);
  }
}
</style>

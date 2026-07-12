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
          <span class="hero-badge-mark">
            <img src="/cjlu-logo.svg" alt="中国计量大学校徽" class="hero-badge-logo" />
          </span>
          <span>中国计量大学 · AI 通识教育课程平台</span>
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
  padding: calc(62px + var(--space-3xl)) 0 var(--space-3xl);
  background:
    linear-gradient(145deg, rgba(18, 20, 38, 0.97) 0%, rgba(30, 40, 64, 0.95) 28%, rgba(45, 90, 110, 0.93) 65%, rgba(58, 125, 92, 0.90) 100%),
    var(--color-primary-dark);
  /* 底部渐变过渡到页面背景色 */
  position: relative;
}

/* 底部柔化过渡 */
.hero::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 48px;
  background: linear-gradient(to bottom, transparent, var(--color-bg));
  pointer-events: none;
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
  padding: 0.3rem 0.7rem;
  color: rgba(255, 253, 248, 0.78);
  background: rgba(255, 253, 248, 0.07);
  border: 1px solid rgba(255, 253, 248, 0.13);
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.hero-badge-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 20px;
  width: 20px;
  height: 20px;
  background: rgba(255, 253, 248, 0.9);
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
  line-height: 1.18;
  text-wrap: balance;
}

.hero-copy h1 span,
.hero-copy h1 strong {
  display: block;
}

.hero-copy h1 span {
  margin-bottom: var(--space-sm);
  font-size: 1.15rem;
  font-weight: 700;
  color: rgba(255, 253, 248, 0.6);
  letter-spacing: 0.06em;
}

.hero-copy h1 strong {
  max-width: 640px;
  font-size: var(--text-display-title);
  font-weight: 900;
  letter-spacing: -0.01em;
  line-height: 1.14;
}

.hero-copy p {
  max-width: 62ch;
  color: rgba(255, 253, 248, 0.68);
  font-size: var(--text-body);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

.hero-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: var(--space-xl);
  flex-wrap: wrap;
}

.suggestion-panel {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  max-width: 560px;
  margin-top: var(--space-lg);
  padding: 0.85rem 1rem;
  color: rgba(255, 253, 248, 0.72);
  background: rgba(255, 253, 248, 0.06);
  border: 1px solid rgba(255, 253, 248, 0.11);
  border-radius: var(--radius-md);
}

.suggestion-panel strong {
  flex: 0 0 auto;
  color: rgba(255, 253, 248, 0.88);
  font-size: 0.86rem;
  white-space: nowrap;
}

.suggestion-panel span {
  min-width: 0;
  font-size: var(--text-muted);
  line-height: var(--leading-compact);
  text-wrap: pretty;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.35rem;
  border-radius: var(--radius-md);
  font-size: 0.92rem;
  font-weight: 700;
  transition:
    transform 130ms var(--ease-out),
    box-shadow 130ms var(--ease-out),
    background 130ms var(--ease-out);
}

.btn-primary {
  color: var(--color-primary-dark);
  background: #fffdf8;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.16), 0 2px 6px rgba(0, 0, 0, 0.10);
}

.btn-primary:hover {
  background: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.2), 0 3px 8px rgba(0, 0, 0, 0.1);
}

.btn-secondary {
  color: rgba(255, 253, 248, 0.9);
  background: rgba(255, 253, 248, 0.07);
  border: 1px solid rgba(255, 253, 248, 0.16);
}

.btn-secondary:hover {
  background: rgba(255, 253, 248, 0.12);
  transform: translateY(-1px);
}

.btn-primary:active,
.btn-secondary:active {
  transform: translateY(1px);
  box-shadow: none;
}

/* ─── Entry Cards ─── */
.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.entry-card {
  display: flex;
  gap: 0.9rem;
  min-height: 152px;
  padding: var(--space-lg);
  color: var(--color-text);
  background: rgba(255, 253, 248, 0.97);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: var(--radius-lg);
  text-align: left;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14), 0 2px 6px rgba(0, 0, 0, 0.08);
  transition:
    transform 150ms var(--ease-out),
    box-shadow 150ms var(--ease-out);
}

.entry-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.18), 0 4px 10px rgba(0, 0, 0, 0.10);
}

.entry-card:active {
  transform: translateY(1px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

.entry-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  color: #fffdf8;
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: 1.1rem;
  font-weight: 900;
}

.entry-learn .entry-mark  { background: var(--color-learn); }
.entry-practice .entry-mark { background: var(--color-practice); }
.entry-create .entry-mark { background: var(--color-create); }
.entry-act .entry-mark    { background: var(--color-act); }

.entry-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.entry-main strong {
  color: var(--color-text);
  font-size: 0.98rem;
  font-weight: 800;
  line-height: 1.3;
}

.entry-main span {
  color: var(--color-text-secondary);
  font-size: 0.83rem;
  line-height: 1.65;
}

@media (max-width: 900px) {
  .hero {
    min-height: auto;
    padding: calc(62px + var(--space-2xl)) 0 var(--space-2xl);
  }

  .hero-layout {
    grid-template-columns: 1fr;
    gap: var(--space-2xl);
  }

  .hero-copy h1 strong {
    font-size: 2.1rem;
  }
}

@media (max-width: 768px) {
  .hero {
    padding: calc(62px + var(--space-xl)) 0 var(--space-xl);
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

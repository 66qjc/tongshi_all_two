<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const modules = [
  {
    key: 'learn',
    mark: '学',
    title: '课程学习',
    desc: '查看公开课程与学习资料，按教学节奏继续推进。',
    status: '进入公开学习馆查看课程与学习资料',
    actions: ['查看学习资料', '继续当前学习'],
    route: '/learn',
    color: 'var(--color-learn)',
  },
  {
    key: 'practice',
    mark: '思',
    title: '练习反思',
    desc: '通过在线练习和错题回看，确认自己是否真正理解。',
    status: '作业、练习和错题集中处理',
    actions: ['进入题库练习', '回看错题记录'],
    route: '/practice',
    color: 'var(--color-practice)',
  },
  {
    key: 'create',
    mark: '践',
    title: '实践创作',
    desc: '浏览作品、提交成果，把 AI 工具使用转化为作品表达。',
    status: '作品提交与展示从这里进入',
    actions: ['浏览学生作品', '提交实践成果'],
    route: '/create',
    color: 'var(--color-create)',
  },
  {
    key: 'act',
    mark: '悟',
    title: '行动感悟',
    desc: '查看公益课、读书会和社区行动，理解技术的社会价值。',
    status: '行动记录支持二级详情查看',
    actions: ['阅读行动案例', '查看公益图文'],
    route: '/act',
    color: 'var(--color-act)',
  },
]
</script>

<template>
  <section class="module-showcase">
    <div class="container">
      <div class="section-header fade-up">
        <span class="section-tag">四个入口</span>
        <h2 class="section-title">按入口选择，直接进入下一步</h2>
        <p class="section-desc">
          从这里进入学习、练习、作品和行动四个常用入口，课程内容以公开学习馆中的最新安排为准。
        </p>
      </div>

      <div class="modules-grid">
        <button
          v-for="(mod, index) in modules"
          :key="mod.key"
          class="module-card fade-up"
          type="button"
          :style="{ '--card-color': mod.color }"
          :data-fade-delay="`${index * 0.08}s`"
          @click="router.push(mod.route)"
        >
          <span class="module-mark">{{ mod.mark }}</span>
          <span class="module-main">
            <span class="module-topline">
              <strong>{{ mod.title }}</strong>
              <span>进入</span>
            </span>
            <span class="module-desc">{{ mod.desc }}</span>
            <span class="module-actions">
              <span v-for="action in mod.actions" :key="action">{{ action }}</span>
            </span>
            <span class="module-status">{{ mod.status }}</span>
          </span>
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.module-showcase {
  padding: var(--space-3xl) 0 var(--space-3xl);
  background: var(--color-bg);
}

.section-header {
  max-width: 680px;
  margin-bottom: var(--space-2xl);
}

.section-tag {
  display: inline-block;
  padding: 0.22rem 0.68rem;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  border: 1px solid rgba(45, 90, 110, 0.12);
  border-radius: var(--radius-full);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-md);
}

.section-title {
  margin-bottom: var(--space-sm);
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: -0.01em;
  text-wrap: balance;
}

.section-desc {
  max-width: 65ch;
  color: var(--color-text-secondary);
  font-size: var(--text-body);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.9rem;
}

.module-card {
  display: flex;
  flex-direction: column;
  min-height: 244px;
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-align: left;
  transition:
    transform 150ms var(--ease-out),
    box-shadow 150ms var(--ease-out),
    border-color 150ms var(--ease-out);
}

.module-card:hover {
  border-color: var(--card-color);
  box-shadow: var(--shadow-lg);
  transform: translateY(-3px);
}

.module-card:active {
  transform: translateY(1px);
  box-shadow: var(--shadow-sm);
}

.module-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: var(--space-lg);
  color: #fffdf8;
  background: var(--card-color);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: 1.05rem;
  font-weight: 900;
}

.module-main {
  display: flex;
  flex: 1;
  flex-direction: column;
}

.module-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: 0.45rem;
}

.module-topline strong {
  color: var(--color-text);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  text-wrap: balance;
}

.module-topline span {
  color: var(--card-color);
  font-size: 0.74rem;
  font-weight: 700;
  white-space: nowrap;
  opacity: 0.85;
}

.module-desc {
  color: var(--color-text-secondary);
  font-size: 0.85rem;
  line-height: 1.72;
}

.module-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 0.9rem;
}

.module-actions span {
  padding: 0.2rem 0.52rem;
  color: var(--card-color);
  background: transparent;
  border: 1px solid;
  border-color: color-mix(in srgb, var(--card-color) 30%, transparent);
  border-radius: var(--radius-sm);
  font-size: 0.72rem;
  font-weight: 700;
}

.module-status {
  margin-top: auto;
  padding-top: var(--space-md);
  color: var(--color-text-muted);
  font-size: 0.76rem;
  line-height: 1.55;
}

@media (max-width: 1024px) {
  .modules-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .module-showcase {
    padding: var(--space-2xl) 0;
  }

  .modules-grid {
    grid-template-columns: 1fr;
  }

  .module-card {
    min-height: auto;
  }
}
</style>

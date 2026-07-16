<script setup lang="ts">
const loopItems = [
  {
    step: '01',
    title: '学',
    desc: '浏览公开教程与阶段学习资料。',
  },
  {
    step: '02',
    title: '思',
    desc: '完成练习与作业，用错题巩固理解。',
  },
  {
    step: '03',
    title: '践',
    desc: '提交课程作品，展示实践成果。',
  },
  {
    step: '04',
    title: '悟',
    desc: '参与公益行动与读书会，拓展应用视野。',
  },
]

const orderItems = [
  '先进入公开教程，按目录阅读课程与资料。',
  '再完成练习或作业，检查是否真正理解。',
  '登录后提交作品，并浏览同学实践成果。',
  '最后查看行动页面，了解课程相关实践与分享。',
]
</script>

<template>
  <section class="stats-section">
    <div class="container">
      <div class="loop-layout fade-up">
        <div class="loop-copy">
          <span class="section-tag">学习路径</span>
          <h2>学 · 思 · 践 · 悟</h2>
          <p>
            按学 · 思 · 践 · 悟四步推进：先读公开教程，再完成练习，提交作品，并参与行动实践。课程与资料会持续更新，可随时从对应入口进入。
          </p>
        </div>

        <div class="loop-detail">
          <div class="flow-line">
            <div v-for="item in loopItems" :key="item.step" class="flow-step">
              <span class="loop-step">{{ item.step }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.desc }}</p>
            </div>
          </div>

          <div class="order-panel">
            <h3>建议学习顺序</h3>
            <ol>
              <li v-for="item in orderItems" :key="item">{{ item }}</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stats-section {
  padding: var(--space-3xl) 0;
  background: var(--color-bg-alt);
}

.loop-layout {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(0, 1.2fr);
  gap: var(--space-2xl);
  align-items: start;
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

.loop-copy h2 {
  margin-bottom: var(--space-sm);
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: -0.01em;
  text-wrap: balance;
}

.loop-copy p {
  max-width: 65ch;
  color: var(--color-text-secondary);
  font-size: var(--text-body);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

.loop-detail {
  display: grid;
  gap: 0.85rem;
}

.flow-line {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
}

/* 四步骤卡片：用左上角数字 + 中文字做区分，无侧边框 */
.flow-step {
  min-height: 164px;
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: box-shadow 150ms var(--ease-out), transform 150ms var(--ease-out);
}

.flow-step:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.loop-step {
  display: block;
  margin-bottom: 0.9rem;
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 900;
  letter-spacing: 0.04em;
  opacity: 0.7;
}

.flow-step strong {
  display: block;
  margin-bottom: 0.45rem;
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  text-wrap: balance;
}

.flow-step p {
  color: var(--color-text-secondary);
  font-size: var(--text-muted);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

/* 建议顺序面板 */
.order-panel {
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.order-panel h3 {
  margin-bottom: 0.9rem;
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  text-wrap: balance;
}

.order-panel ol {
  display: grid;
  gap: 0.6rem;
  padding-left: 1.2rem;
  color: var(--color-text-secondary);
  font-size: 0.86rem;
  line-height: 1.72;
}

.order-panel li::marker {
  color: var(--color-primary);
  font-weight: 700;
}

@media (max-width: 1024px) {
  .loop-layout {
    grid-template-columns: 1fr;
  }

  .flow-line {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .stats-section {
    padding: var(--space-2xl) 0;
  }

  .flow-line {
    grid-template-columns: 1fr;
  }

  .flow-step {
    min-height: auto;
  }
}
</style>

<script setup lang="ts">
const modules = [
  { num: '01', title: '人工智能概述', desc: '从图灵测试到深度学习，AI 发展全景扫描', icon: '&#9670;', tag: '基础' },
  { num: '02', title: '计算机基础知识', desc: '办公软件使用基础与计算思维入门', icon: '&#9632;', tag: '入门' },
  { num: '03', title: 'AI 理论基础', desc: '深度学习、大模型原理与核心算法', icon: '&#9679;', tag: '核心' },
  { num: '04', title: 'AI 工具使用', desc: '大模型、智能体应用及简单开发实践', icon: '&#9733;', tag: '实践' },
  { num: '05', title: 'AI 前沿与应用', desc: '结合专业的前沿应用场景探索', icon: '&#9830;', tag: '前沿' },
  { num: '06', title: 'AI 伦理与未来', desc: '技术向善，负责任的人工智能发展之路', icon: '&#9829;', tag: '思辨' },
]
</script>

<template>
  <section class="course-preview">
    <div class="container">
      <div class="section-header fade-up">
        <span class="section-tag">公开学习馆</span>
        <h2 class="section-title">按公开课程进入学习资料</h2>
        <p class="section-desc">
          课程内容以公开学习馆中的实际资料和课时为准<br />
        </p>
      </div>

      <div class="modules-grid fade-up">
        <div
          v-for="(ch, index) in modules"
          :key="ch.num"
          class="module-card"
          :style="{ '--index': index }"
        >
          <div class="module-num">{{ ch.num }}</div>
          <div class="module-content">
            <div class="module-top">
              <span class="module-tag" v-html="ch.tag"></span>
              <span class="module-icon" v-html="ch.icon"></span>
            </div>
            <h3 class="module-title">{{ ch.title }}</h3>
            <p class="module-desc">{{ ch.desc }}</p>
          </div>
          <div class="module-line"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.course-preview {
  padding: var(--space-3xl) 0;
  background: var(--color-bg-alt);
}

.section-header {
  text-align: center;
  margin-bottom: var(--space-2xl);
}

/* 与其他 section 统一的 tag 样式 */
.section-tag {
  display: inline-block;
  padding: 0.22rem 0.68rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  border: 1px solid rgba(45, 90, 110, 0.12);
  border-radius: var(--radius-full);
  letter-spacing: 0.04em;
  margin-bottom: var(--space-lg);
}

.section-title {
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: var(--space-md);
  letter-spacing: -0.01em;
  text-wrap: balance;
}

.section-desc {
  max-width: 65ch;
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
  text-wrap: pretty;
  margin: 0 auto;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.9rem;
}

.module-card {
  position: relative;
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition:
    transform var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
  overflow: hidden;
}

.module-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  border-color: rgba(74, 143, 166, 0.5);
}

/* 大号序号作为装饰，不喧宾夺主 */
.module-num {
  font-size: 2.6rem;
  font-weight: 900;
  color: var(--color-border-light);
  line-height: 1;
  margin-bottom: 0.9rem;
  font-family: var(--font-mono);
  transition: color var(--duration-fast) var(--ease-out);
  user-select: none;
}

.module-card:hover .module-num {
  color: rgba(74, 143, 166, 0.38);
}

.module-content {
  position: relative;
  z-index: 1;
}

.module-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.55rem;
}

.module-tag {
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  border: 1px solid rgba(45, 90, 110, 0.1);
  padding: 0.14rem 0.6rem;
  border-radius: var(--radius-full);
  letter-spacing: 0.04em;
}

.module-icon {
  font-size: 0.85rem;
  color: var(--color-border);
}

.module-title {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  color: var(--color-text);
  margin-bottom: 0.45rem;
  letter-spacing: 0;
  text-wrap: balance;
}

.module-desc {
  font-size: var(--text-muted);
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

/* 底部彩线：宽度由 0 → 100% 的 hover 动效 */
.module-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--gradient-cta);
  transition: width var(--duration-normal) var(--ease-out);
  border-radius: 0 2px 0 0;
}

.module-card:hover .module-line {
  width: 100%;
}

@media (max-width: 1024px) {
  .modules-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .modules-grid {
    grid-template-columns: 1fr;
  }
}
</style>

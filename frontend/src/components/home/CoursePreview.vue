<script setup lang="ts">
import { ref } from 'vue'

const modules = [
  { num: '01', title: '人工智能概述', desc: '从图灵测试到深度学习，AI 发展全景扫描', icon: '&#9670;', tag: '基础' },
  { num: '02', title: '计算机基础知识', desc: '办公软件使用基础与计算思维入门', icon: '&#9632;', tag: '入门' },
  { num: '03', title: 'AI 理论基础', desc: '深度学习、大模型原理与核心算法', icon: '&#9679;', tag: '核心' },
  { num: '04', title: 'AI 工具使用', desc: '大模型、智能体应用及简单开发实践', icon: '&#9733;', tag: '实践' },
  { num: '05', title: 'AI 前沿与应用', desc: '结合专业的前沿应用场景探索', icon: '&#9830;', tag: '前沿' },
  { num: '06', title: 'AI 伦理与未来', desc: '技术向善，负责任的人工智能发展之路', icon: '&#9829;', tag: '思辨' },
]

const hoveredIndex = ref(-1)
</script>

<template>
  <section class="course-preview">
    <div class="container">
      <div class="section-header fade-up">
        <span class="section-tag">课程大纲</span>
        <h2 class="section-title">六个模块，构建 AI 知识体系</h2>
        <p class="section-desc">
          从概念到实践，从理论到伦理<br />
          为理工科新生量身定制的 AI 通识课程
        </p>
      </div>

      <div class="modules-grid fade-up">
        <div
          v-for="(ch, index) in modules"
          :key="ch.num"
          class="module-card"
          :class="{ hovered: hoveredIndex === index }"
          :style="{ '--index': index }"
          @mouseenter="hoveredIndex = index"
          @mouseleave="hoveredIndex = -1"
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
  padding: var(--space-4xl) 0;
  background: var(--color-bg-alt);
}

.section-header {
  text-align: center;
  margin-bottom: var(--space-3xl);
}

.section-tag {
  display: inline-block;
  padding: 0.3rem 0.9rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  border-radius: var(--radius-full);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: var(--space-lg);
}

.section-title {
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  letter-spacing: -0.02em;
}

.section-desc {
  font-size: 1rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.module-card {
  position: relative;
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
  overflow: hidden;
}

.module-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-light);
}

.module-num {
  font-size: 3rem;
  font-weight: 900;
  color: var(--color-border);
  line-height: 1;
  margin-bottom: var(--space-md);
  transition: color var(--duration-normal) var(--ease-out);
  font-family: var(--font-mono);
}

.module-card:hover .module-num {
  color: var(--color-primary-light);
}

.module-content {
  position: relative;
  z-index: 1;
}

.module-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-sm);
}

.module-tag {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  padding: 0.15rem 0.6rem;
  border-radius: var(--radius-full);
  letter-spacing: 0.04em;
}

.module-icon {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.module-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.module-desc {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.module-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--gradient-cta);
  transition: width var(--duration-normal) var(--ease-out);
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

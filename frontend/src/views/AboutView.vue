<script setup lang="ts">
const modules = [
  { num: '01', title: '人工智能概述', desc: '了解 AI 的基本概念、发展脉络与常见应用', tag: '基础' },
  { num: '02', title: '计算机基础知识', desc: '建立必要的信息素养与计算思维基础', tag: '入门' },
  { num: '03', title: 'AI 理论基础', desc: '理解常见 AI 方法与大模型相关通识内容', tag: '核心' },
  { num: '04', title: 'AI 工具使用', desc: '学习常用 AI 工具的规范使用与实践方法', tag: '实践' },
  { num: '05', title: 'AI 前沿与应用', desc: '结合专业场景了解 AI 应用方向', tag: '前沿' },
  { num: '06', title: 'AI 伦理与未来', desc: '认识 AI 使用中的责任、风险与价值边界', tag: '思辨' },
]
</script>

<template>
  <div class="about-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <h1>关于平台</h1>
          <p>中国计量大学 · 深度 AI 通识教育课程平台</p>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="container">
        <div class="about-block">
          <h2>平台简介</h2>
          <p>
            本平台面向中国计量大学 AI 通识课程教学，提供公开教程阅读、练习作业、作品提交与行动实践等功能。
            游客可浏览公开学习内容；学生登录后可保存进度、完成练习与提交作品；教师与管理员负责课程、班级与内容运营。
          </p>
        </div>

        <div class="about-block">
          <h2>学习路径</h2>
          <p>平台围绕「学 · 思 · 践 · 悟」组织学习流程：</p>
          <div class="philosophy-grid">
            <div class="phil-card">
              <div class="phil-icon">
                <img src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png" alt="AI 通识课平台标识" />
              </div>
              <h3>学</h3>
              <p>阅读公开教程与阶段学习资料，建立系统认知</p>
            </div>
            <div class="phil-card">
              <div class="phil-icon">
                <img src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png" alt="AI 通识课平台标识" />
              </div>
              <h3>思</h3>
              <p>完成练习与作业，通过答题与错题巩固理解</p>
            </div>
            <div class="phil-card">
              <div class="phil-icon">
                <img src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png" alt="AI 通识课平台标识" />
              </div>
              <h3>践</h3>
              <p>提交课程作品与实践报告，展示学习成果</p>
            </div>
            <div class="phil-card">
              <div class="phil-icon">
                <img src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png" alt="AI 通识课平台标识" />
              </div>
              <h3>悟</h3>
              <p>参与公益课、读书会等行动，拓展应用与价值理解</p>
            </div>
          </div>
        </div>

        <div class="about-block">
          <h2>课程内容</h2>
          <p>课程与资料由教师和管理员在后台维护，会随教学安排更新。常见主题包括：</p>
          <div class="modules-grid">
            <div v-for="ch in modules" :key="ch.num" class="module-item">
              <span class="ch-num">{{ ch.num }}</span>
              <div class="ch-info">
                <div class="ch-top">
                  <h3>{{ ch.title }}</h3>
                  <span class="ch-tag">{{ ch.tag }}</span>
                </div>
                <p>{{ ch.desc }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="about-block">
          <h2>适用对象</h2>
          <p>
            主要服务中国计量大学参与 AI 通识课程的学生，同时支持游客浏览公开教程与资料。
            无需预先具备 AI 专业背景，可按课程安排逐步学习。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.about-page {
  padding-top: 60px;
}

.page-hero {
  padding: var(--space-3xl) 0;
  background: var(--color-primary-glow);
  border-bottom: 1px solid var(--color-border-light);
}

.hero-inner {
  text-align: center;
}

.hero-inner h1 {
  font-family: var(--font-sans);
  font-size: var(--text-page-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  text-wrap: balance;
}

.hero-inner p {
  max-width: 65ch;
  margin: 0 auto;
  font-size: var(--text-body);
  line-height: var(--leading-body);
  color: var(--color-text-secondary);
  text-wrap: pretty;
}

.content-section {
  padding: var(--space-3xl) 0;
}

.about-block {
  margin-bottom: var(--space-3xl);
}

.about-block h2 {
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
  text-wrap: balance;
}

.about-block > p {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
  max-width: 72ch;
  text-wrap: pretty;
}

.philosophy-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
  margin-top: var(--space-xl);
}

.phil-card {
  text-align: center;
  padding: var(--space-xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
}

.phil-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.phil-icon {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-sm);
}

.phil-icon img {
  display: block;
  width: 40px;
  height: 40px;
  object-fit: contain;
}

.phil-card h3 {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  text-wrap: balance;
}

.phil-card p {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.modules-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  margin-top: var(--space-lg);
}

.module-item {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
}

.module-item:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
}

.ch-num {
  font-size: 1.5rem;
  font-weight: 900;
  color: var(--color-border);
  font-family: var(--font-mono);
  flex-shrink: 0;
  width: 40px;
}

.ch-info {
  flex: 1;
}

.ch-top {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-xs);
}

.ch-top h3 {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 800;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  text-wrap: balance;
}

.ch-tag {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-full);
}

.ch-info p {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .philosophy-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .philosophy-grid {
    grid-template-columns: 1fr;
  }
}
</style>

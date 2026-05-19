<script setup lang="ts">
const chapters = [
  { num: '01', title: '人工智能概述', desc: '从图灵测试到深度学习，AI 发展全景扫描', tag: '基础' },
  { num: '02', title: '计算机基础知识', desc: '办公软件使用基础与计算思维入门', tag: '入门' },
  { num: '03', title: 'AI 理论基础', desc: '深度学习、大模型原理与核心算法', tag: '核心' },
  { num: '04', title: 'AI 工具使用', desc: '大模型、智能体应用及简单开发实践', tag: '实践' },
  { num: '05', title: 'AI 前沿与应用', desc: '结合专业的前沿应用场景探索', tag: '前沿' },
  { num: '06', title: 'AI 伦理与未来', desc: '技术向善，负责任的人工智能发展之路', tag: '思辨' },
]
</script>

<template>
  <div class="about-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <h1>关于平台</h1>
          <p>探 · 练 · 创 · 行 — AI 通识课教学平台</p>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="container">
        <div class="about-block">
          <h2>平台理念</h2>
          <p>本平台致力于为中国计量大学理工科大一学生提供系统的人工智能通识教育。我们相信 AI 教育不应止于知识传授，更应在实践中培养学生的综合能力。</p>
          <div class="philosophy-grid">
            <div class="phil-card">
              <div class="phil-icon" style="color: var(--color-learn)">探</div>
              <h3>学</h3>
              <p>六大核心章节，从 AI 概述到伦理思辨，系统构建知识体系</p>
            </div>
            <div class="phil-card">
              <div class="phil-icon" style="color: var(--color-practice)">练</div>
              <h3>练</h3>
              <p>在线练习即练即批，选择题与填空题巩固核心知识点</p>
            </div>
            <div class="phil-card">
              <div class="phil-icon" style="color: var(--color-create)">造</div>
              <h3>创</h3>
              <p>AI + 硬件创意实践，打破"AI 只是聊天框"的思维局限</p>
            </div>
            <div class="phil-card">
              <div class="phil-icon" style="color: var(--color-act)">行</div>
              <h3>行</h3>
              <p>走进社区和中小学，用 AI 温暖社会，锻炼综合软实力</p>
            </div>
          </div>
        </div>

        <div class="about-block">
          <h2>课程概览</h2>
          <div class="chapters-grid">
            <div v-for="ch in chapters" :key="ch.num" class="chapter-item">
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
          <p>本平台面向中国计量大学理工科大一学生，无需 AI 基础。无论你是自动化、机械工程、测控技术还是其他理工科专业，都能在这里找到适合自己的 AI 学习路径。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.about-page {
  padding-top: 64px;
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
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.hero-inner p {
  font-size: 1rem;
  color: var(--color-text-secondary);
}

.content-section {
  padding: var(--space-3xl) 0;
}

.about-block {
  margin-bottom: var(--space-3xl);
}

.about-block h2 {
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
}

.about-block > p {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
  max-width: 720px;
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
  font-size: 2rem;
  font-weight: 900;
  margin-bottom: var(--space-sm);
}

.phil-card h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.phil-card p {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.chapters-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.chapter-item {
  display: flex;
  gap: var(--space-lg);
  padding: var(--space-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) var(--ease-out);
}

.chapter-item:hover {
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
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
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

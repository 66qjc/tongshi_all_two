<template>
  <div class="privacy-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <h1>隐私政策</h1>
          <p>我们重视每一位用户的数据隐私</p>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="container">
        <div class="content-block">
          <h2>数据收集</h2>
          <p>本平台仅收集与教学活动直接相关的数据，包括：</p>
          <ul>
            <li>学习进度数据（章节完成状态、视频观看记录）</li>
            <li>练习数据（答题记录、正确率统计）</li>
            <li>作品提交数据（课程报告、演示视频链接）</li>
          </ul>
        </div>

        <div class="content-block">
          <h2>本地存储</h2>
          <p>平台使用浏览器 localStorage 存储以下信息：</p>
          <ul>
            <li>登录状态凭证（会话令牌）</li>
            <li>用户偏好设置（主题、字体大小等）</li>
            <li>部分练习数据的本地缓存，用于断网时继续做题</li>
          </ul>
          <p>这些数据仅存储在您的浏览器中，不会上传至第三方服务器。</p>
        </div>

        <div class="content-block">
          <h2>数据用途</h2>
          <p>收集的数据仅用于：</p>
          <ul>
            <li>跟踪学习进度，提供个性化学习建议</li>
            <li>生成 AI 成长档案（E-Portfolio）</li>
            <li>教师查看班级整体学习情况，优化教学方案</li>
          </ul>
          <p>我们不会将数据用于任何商业用途，不会出售或共享给第三方。</p>
        </div>

        <div class="content-block">
          <h2>数据保留与删除</h2>
          <p>学生数据在课程结束后保留一个学期。如需提前删除个人数据，请通过"联系我们"页面提交申请，我们将在 5 个工作日内处理。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.privacy-page {
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

.content-block {
  margin-bottom: var(--space-2xl);
  max-width: 720px;
}

.content-block h2 {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-md);
}

.content-block p {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
  margin-bottom: var(--space-sm);
}

.content-block ul {
  margin-left: var(--space-lg);
  margin-bottom: var(--space-md);
}

.content-block li {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
  list-style: disc;
}
</style>

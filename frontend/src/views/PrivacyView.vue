<template>
  <div class="privacy-page">
    <section class="page-hero">
      <div class="container">
        <div class="hero-inner">
          <h1>隐私政策</h1>
          <p>说明本平台如何收集、使用和保护与教学相关的信息</p>
        </div>
      </div>
    </section>

    <section class="content-section">
      <div class="container">
        <div class="content-block">
          <h2>适用范围</h2>
          <p>
            本政策适用于中国计量大学 AI 通识教育课程平台。平台用于课程学习、练习作业、作品提交与教学管理。
            游客可浏览公开内容；登录用户可使用进度保存、练习、作品等功能。
          </p>
        </div>

        <div class="content-block">
          <h2>我们收集的信息</h2>
          <p>为保障教学与平台运行，可能收集以下与业务直接相关的信息：</p>
          <ul>
            <li>账号信息：学号/工号、姓名、角色等用于登录与身份识别的信息</li>
            <li>学习数据：功能下线前产生的历史课程学习记录（平台不再新增课时阅读记录）、练习答题与作业完成情况</li>
            <li>作品数据：学生提交的课程作品、报告及相关附件信息</li>
            <li>教学管理数据：班级归属、作业发布与完成统计、审核相关记录</li>
            <li>运行日志：用于安全审计与故障排查的必要访问与操作记录</li>
          </ul>
        </div>

        <div class="content-block">
          <h2>本地存储</h2>
          <p>平台可能在浏览器中使用本地存储保存：</p>
          <ul>
            <li>登录会话相关凭证</li>
            <li>必要的界面偏好或临时草稿（如练习进度缓存）</li>
          </ul>
          <p>本地数据保存在您使用的浏览器中，用于维持登录状态和改善使用体验。</p>
        </div>

        <div class="content-block">
          <h2>信息如何使用</h2>
          <p>收集的信息仅用于教学与平台服务，包括：</p>
          <ul>
            <li>提供课程阅读、练习、作业、作品与消息等功能</li>
            <li>保存学习进度，支持学生继续学习</li>
            <li>支持教师查看班级学习情况、批改与审核相关工作</li>
            <li>保障系统安全、排查故障并改进服务质量</li>
          </ul>
          <p>我们不会将教学数据用于与课程无关的商业推广，也不会出售用户数据。</p>
        </div>

        <div class="content-block">
          <h2>信息共享与保护</h2>
          <p>
            除法律法规要求、学校教学管理需要，或为提供平台服务所必需的情形外，不会向无关第三方提供您的个人信息。
            平台采取合理的技术与管理措施保护数据安全，但请理解任何网络服务都无法保证绝对安全。
          </p>
        </div>

        <div class="content-block">
          <h2>保存与删除</h2>
          <p>
            学习与教学相关数据会在课程管理与学校管理需要的期限内保存。
            如需咨询个人数据相关问题，或申请处理账号相关事项，请通过「联系我们」页面提交，我们将在合理期限内予以回复。
          </p>
        </div>

        <div class="content-block">
          <h2>政策更新</h2>
          <p>
            我们可能根据功能调整或管理要求更新本政策。更新后的内容将在本页面发布，并自发布时起生效。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.privacy-page {
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

.content-block {
  margin-bottom: var(--space-2xl);
  max-width: 720px;
}

.content-block h2 {
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  line-height: var(--leading-title);
  letter-spacing: 0;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  text-wrap: balance;
}

.content-block p {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
  margin-bottom: var(--space-sm);
  text-wrap: pretty;
}

.content-block ul {
  margin-left: var(--space-lg);
  margin-bottom: var(--space-md);
}

.content-block li {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: var(--leading-body);
  list-style: disc;
  text-wrap: pretty;
}
</style>

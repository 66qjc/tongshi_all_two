<script setup lang="ts">
</script>

<template>
  <footer class="app-footer">
    <div class="footer-inner container">
      <div class="footer-grid">
        <!-- Brand -->
        <div class="footer-brand">
          <div class="footer-logo">
            <span class="footer-logo-mark">
              <img
                src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png"
                alt="中国计量大学 AI 通识课平台标识"
                width="36"
                height="36"
                class="footer-logo-icon"
              />
            </span>
            <span class="footer-logo-text">深度学思践行</span>
          </div>
          <p class="footer-desc">AI 通识课教学平台，助力每一位理工科新生探索人工智能的无限可能。</p>
        </div>

        <!-- Quick Links -->
        <div class="footer-links">
          <h4>课程模块</h4>
          <router-link to="/learn">深度学 · 积累知识</router-link>
          <router-link to="/practice">深度思 · 深化理解</router-link>
          <router-link to="/create">深度践 · 动手创作</router-link>
          <router-link to="/act">深度悟 · 感悟价值</router-link>
        </div>

        <div class="footer-links">
          <h4>平台资源</h4>
          <router-link to="/learn">公开学习馆</router-link>
          <router-link to="/create">项目展示</router-link>
          <router-link to="/act">社区行动</router-link>
        </div>

        <div class="footer-links">
          <h4>了解更多</h4>
          <router-link to="/about">关于平台</router-link>
          <router-link to="/privacy">隐私政策</router-link>
          <router-link to="/contact">联系我们</router-link>
        </div>
      </div>

      <div class="footer-bottom">
        <p>深度学思践行 AI 通识课平台 &mdash; 在学中思，在践中悟</p>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: #141428;
  color: rgba(255, 255, 255, 0.5);
  padding: var(--space-3xl) 0 0;
  margin-top: var(--space-3xl);
  /* 顶部微亮边，与页面正文分隔 */
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.footer-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: var(--space-2xl);
  padding-bottom: var(--space-2xl);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: var(--space-md);
}

.footer-logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  background: rgba(255, 253, 248, 0.92);
  border: 1px solid rgba(255, 253, 248, 0.2);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.28);
  transition: transform var(--duration-fast) var(--ease-out);
}

.footer-logo-mark:hover {
  transform: translateY(-1px);
}

.footer-logo-icon {
  display: block;
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.footer-logo-text {
  font-family: var(--font-sans);
  font-size: var(--text-card-title);
  font-weight: 900;
  color: rgba(255, 255, 255, 0.82);
  letter-spacing: 0;
  text-wrap: balance;
}

.footer-desc {
  font-size: var(--text-muted);
  line-height: var(--leading-body);
  max-width: 260px;
  text-wrap: pretty;
  color: rgba(255, 255, 255, 0.44);
}

.footer-links h4 {
  color: rgba(255, 255, 255, 0.65);
  font-size: 0.7rem;
  font-weight: 800;
  margin-bottom: var(--space-lg);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.footer-links a {
  display: block;
  font-size: var(--text-muted);
  line-height: var(--leading-compact);
  padding: 0.3rem 0;
  color: rgba(255, 255, 255, 0.44);
  transition: color var(--duration-fast);
}

.footer-links a:hover {
  color: rgba(255, 255, 255, 0.85);
}

.footer-bottom {
  padding: var(--space-lg) 0;
  text-align: center;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.24);
  letter-spacing: 0.04em;
}

@media (max-width: 768px) {
  .footer-grid {
    grid-template-columns: 1fr 1fr;
    gap: var(--space-xl);
  }

  .footer-brand {
    grid-column: 1 / -1;
  }
}

@media (max-width: 480px) {
  .footer-grid {
    grid-template-columns: 1fr;
  }
}
</style>

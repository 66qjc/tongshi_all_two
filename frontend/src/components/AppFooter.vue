<script setup lang="ts">
const currentYear = new Date().getFullYear()
</script>

<template>
  <footer class="app-footer">
    <div class="footer-inner container">
      <div class="footer-grid">
        <!-- Brand -->
        <div class="footer-brand">
          <div class="footer-logo">
            <svg viewBox="0 0 32 32" width="24" height="24">
              <defs>
                <linearGradient id="fLogo" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style="stop-color: var(--color-primary)" />
                  <stop offset="100%" style="stop-color: var(--color-learn)" />
                </linearGradient>
              </defs>
              <circle cx="16" cy="16" r="14" fill="url(#fLogo)" />
              <text x="16" y="21" text-anchor="middle" font-size="13" font-weight="700"
                    fill="white" font-family="sans-serif">探</text>
            </svg>
            <span>探 · 练 · 创 · 行</span>
          </div>
          <p class="footer-desc">AI 通识课教学平台，助力每一位理工科新生探索人工智能的无限可能。</p>
        </div>

        <!-- Quick Links -->
        <div class="footer-links">
          <h4>课程模块</h4>
          <router-link to="/learn">探 · 学无止境</router-link>
          <router-link to="/practice">练 · 学以致用</router-link>
          <router-link to="/create">造 · 智创未来</router-link>
          <router-link to="/act">行 · 知行合一</router-link>
        </div>

        <div class="footer-links">
          <h4>平台资源</h4>
          <router-link to="/learn">课程大纲</router-link>
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
        <p>&copy; {{ currentYear }} 探 · 练 · 创 · 行 AI 通识课平台 &mdash; 在做中学，在行中悟</p>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: var(--color-text);
  color: rgba(255, 255, 255, 0.7);
  padding: var(--space-4xl) 0 0;
  margin-top: var(--space-4xl);
}

.footer-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: var(--space-3xl);
  padding-bottom: var(--space-3xl);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

.footer-logo span {
  font-size: 1.1rem;
  font-weight: 700;
  color: white;
}

.footer-desc {
  font-size: 0.875rem;
  line-height: 1.7;
  max-width: 280px;
}

.footer-links h4 {
  color: white;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: var(--space-lg);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.footer-links a {
  display: block;
  font-size: 0.875rem;
  padding: var(--space-xs) 0;
  transition: color var(--duration-fast);
}

.footer-links a:hover {
  color: white;
}

.footer-bottom {
  padding: var(--space-xl) 0;
  text-align: center;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.4);
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

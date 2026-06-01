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
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
              <defs>
                <radialGradient id="inkGradFooter" cx="40%" cy="38%" r="60%">
                  <stop offset="0%" stop-color="#3d2e1a"/>
                  <stop offset="60%" stop-color="#1a1208"/>
                  <stop offset="100%" stop-color="#0d0a05"/>
                </radialGradient>
              </defs>
              <!-- 外环描边（金色） -->
              <circle cx="18" cy="18" r="17" fill="url(#inkGradFooter)" stroke="#c9a84c" stroke-width="1.2" opacity="0.9"/>
              <!-- 内圈装饰光晕 -->
              <circle cx="18" cy="18" r="14.5" fill="none" stroke="rgba(201,168,76,0.18)" stroke-width="0.6"/>
              <!-- 汉字 -->
              <text
                x="18" y="24"
                text-anchor="middle"
                font-size="16"
                font-weight="600"
                font-family="'STKaiti','KaiTi','FangSong','仿宋',serif"
                fill="rgba(255,255,255,0.95)"
                letter-spacing="0"
              >学</text>
            </svg>
            <span>学 · 思 · 践 · 悟</span>
          </div>
          <p class="footer-desc">AI 通识课教学平台，助力每一位理工科新生探索人工智能的无限可能。</p>
        </div>

        <!-- Quick Links -->
        <div class="footer-links">
          <h4>课程模块</h4>
          <router-link to="/learn">学 · 积累知识</router-link>
          <router-link to="/practice">思 · 深化理解</router-link>
          <router-link to="/create">践 · 动手创作</router-link>
          <router-link to="/act">悟 · 感悟价值</router-link>
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
        <p>&copy; {{ currentYear }} 学 · 思 · 践 · 悟 AI 通识课平台 &mdash; 在学中思，在践中悟</p>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: #1a1a2e;
  color: rgba(255, 255, 255, 0.55);
  padding: var(--space-3xl) 0 0;
  margin-top: var(--space-3xl);
}

.footer-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: var(--space-2xl);
  padding-bottom: var(--space-2xl);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

.footer-logo span {
  font-family: var(--font-serif);
  font-size: 1.05rem;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.08em;
}

.footer-desc {
  font-size: 0.82rem;
  line-height: 1.7;
  max-width: 280px;
}

.footer-links h4 {
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.78rem;
  font-weight: 600;
  margin-bottom: var(--space-lg);
  letter-spacing: 0.1em;
}

.footer-links a {
  display: block;
  font-size: 0.82rem;
  padding: var(--space-xs) 0;
  transition: color var(--duration-fast);
}

.footer-links a:hover {
  color: rgba(255, 255, 255, 0.9);
}

.footer-bottom {
  padding: var(--space-lg) 0;
  text-align: center;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 0.03em;
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

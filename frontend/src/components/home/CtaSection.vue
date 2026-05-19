<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <section class="cta-section">
    <div class="container">
      <div class="cta-card fade-up">
        <div class="cta-bg">
          <div class="cta-orb cta-orb-1"></div>
          <div class="cta-orb cta-orb-2"></div>
          <div class="cta-grid-pattern"></div>
        </div>

        <div class="cta-content">
          <h2 class="cta-title">
            在做中学，在行中悟
          </h2>
          <p class="cta-desc">
            加入 AI 通识课，构建你的数字成长档案<br />
            用技术温暖社会，从容拥抱智能时代
          </p>
          <div class="cta-actions">
            <button class="cta-btn primary" @click="router.push('/learn')">
              开始学习之旅
            </button>
            <button class="cta-btn secondary" @click="router.push('/act')">
              了解社区行动
            </button>
          </div>

          <div class="cta-modules">
            <div class="cta-module" @click="router.push('/learn')">
              <span class="cta-module-icon t">探</span>
              <span>学无止境</span>
            </div>
            <div class="cta-sep">·</div>
            <div class="cta-module" @click="router.push('/practice')">
              <span class="cta-module-icon p">练</span>
              <span>学以致用</span>
            </div>
            <div class="cta-sep">·</div>
            <div class="cta-module" @click="router.push('/create')">
              <span class="cta-module-icon c">造</span>
              <span>智创未来</span>
            </div>
            <div class="cta-sep">·</div>
            <div class="cta-module" @click="router.push('/act')">
              <span class="cta-module-icon a">行</span>
              <span>知行合一</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cta-section {
  padding: var(--space-4xl) 0;
  background: var(--color-bg-alt);
}

.cta-card {
  position: relative;
  padding: var(--space-4xl) var(--space-2xl);
  background: var(--gradient-hero);
  border-radius: var(--radius-xl);
  overflow: hidden;
  text-align: center;
}

.cta-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.cta-grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

.cta-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
}

.cta-orb-1 {
  width: 300px;
  height: 300px;
  background: rgba(79, 70, 229, 0.3);
  top: -100px;
  right: -50px;
  animation: float1 15s ease-in-out infinite;
}

.cta-orb-2 {
  width: 250px;
  height: 250px;
  background: rgba(6, 182, 212, 0.2);
  bottom: -80px;
  left: -30px;
  animation: float2 18s ease-in-out infinite;
}

@keyframes float1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-20px, 20px); }
}
@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -20px); }
}

.cta-content {
  position: relative;
  z-index: 1;
}

.cta-title {
  font-size: clamp(1.8rem, 4vw, 2.8rem);
  font-weight: 900;
  color: white;
  margin-bottom: var(--space-lg);
  letter-spacing: 0.04em;
}

.cta-desc {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.8;
  margin-bottom: var(--space-2xl);
}

.cta-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  margin-bottom: var(--space-2xl);
}

.cta-btn {
  padding: 0.85rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: var(--radius-full);
  transition: all var(--duration-normal) var(--ease-out);
}

.cta-btn.primary {
  color: var(--color-primary-dark);
  background: white;
}

.cta-btn.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(255, 255, 255, 0.25);
}

.cta-btn.secondary {
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.cta-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.18);
  transform: translateY(-2px);
}

.cta-modules {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-lg);
}

.cta-module {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: color var(--duration-fast);
}

.cta-module:hover {
  color: white;
}

.cta-module-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 800;
  border-radius: 6px;
  color: white;
}

.cta-module-icon.t { background: rgba(6, 182, 212, 0.3); }
.cta-module-icon.p { background: rgba(139, 92, 246, 0.3); }
.cta-module-icon.c { background: rgba(245, 158, 11, 0.3); }
.cta-module-icon.a { background: rgba(16, 185, 129, 0.3); }

.cta-sep {
  color: rgba(255, 255, 255, 0.2);
  font-size: 1.2rem;
}

@media (max-width: 640px) {
  .cta-card {
    padding: var(--space-3xl) var(--space-lg);
  }

  .cta-actions {
    flex-direction: column;
  }

  .cta-modules {
    flex-direction: column;
    gap: var(--space-sm);
  }

  .cta-sep {
    display: none;
  }

  .cta-desc br {
    display: none;
  }
}
</style>

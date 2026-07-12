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
          <div class="cta-text">
            <h2 class="cta-title">在学中思，在践中悟</h2>
            <p class="cta-desc">学思践悟，四维并进，让 AI 知识真正内化为你的能力与价值观。</p>
          </div>
          <div class="cta-actions">
            <button class="cta-btn primary" @click="router.push('/learn')">
              开始学习
            </button>
            <button class="cta-btn secondary" @click="router.push('/act')">
              公益行动
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cta-section {
  padding: var(--space-2xl) 0;
  background: var(--color-bg);
}

.cta-card {
  position: relative;
  padding: var(--space-xl) var(--space-2xl);
  background: var(--gradient-hero);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-xl);
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
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

.cta-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
}

.cta-orb-1 {
  width: 200px;
  height: 200px;
  background: rgba(45, 90, 110, 0.3);
  top: -60px;
  right: -20px;
  animation: float1 15s ease-in-out infinite;
}

.cta-orb-2 {
  width: 160px;
  height: 160px;
  background: rgba(58, 125, 92, 0.18);
  bottom: -50px;
  left: -10px;
  animation: float2 18s ease-in-out infinite;
}

@keyframes float1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-15px, 15px); }
}
@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(15px, -15px); }
}

.cta-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-xl);
}

.cta-text {
  flex: 1;
  min-width: 0;
}

.cta-title {
  font-family: var(--font-sans);
  font-size: var(--text-section-title);
  font-weight: 900;
  color: white;
  margin-bottom: var(--space-xs);
  line-height: var(--leading-title);
  letter-spacing: 0;
  text-wrap: balance;
}

.cta-desc {
  max-width: 65ch;
  font-size: var(--text-muted);
  color: rgba(255, 255, 255, 0.55);
  line-height: var(--leading-body);
  text-wrap: pretty;
}

.cta-actions {
  display: flex;
  gap: var(--space-md);
  flex-shrink: 0;
}

.cta-btn {
  padding: 0.65rem 1.4rem;
  font-size: 0.9rem;
  font-weight: 700;
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.cta-btn.primary {
  color: var(--color-primary-dark);
  background: white;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.cta-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
}

.cta-btn.secondary {
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.cta-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.18);
  transform: translateY(-1px);
}

@media (max-width: 768px) {
  .cta-card {
    padding: var(--space-xl) var(--space-lg);
  }

  .cta-content {
    flex-direction: column;
    text-align: center;
  }

  .cta-actions {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .cta-actions {
    flex-direction: column;
  }

  .cta-btn {
    text-align: center;
  }
}
</style>

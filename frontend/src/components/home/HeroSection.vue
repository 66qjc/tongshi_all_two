<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const heroRef = ref<HTMLElement>()
const mouseX = ref(0)
const mouseY = ref(0)
const loaded = ref(false)

// Floating particles
const particles = Array.from({ length: 20 }, (_, i) => ({
  id: i,
  x: Math.random() * 100,
  y: Math.random() * 100,
  size: Math.random() * 4 + 2,
  delay: Math.random() * 5,
  duration: Math.random() * 10 + 15,
}))

function handleMouseMove(e: MouseEvent) {
  if (!heroRef.value) return
  const rect = heroRef.value.getBoundingClientRect()
  mouseX.value = ((e.clientX - rect.left) / rect.width - 0.5) * 20
  mouseY.value = ((e.clientY - rect.top) / rect.height - 0.5) * 20
}

onMounted(() => {
  setTimeout(() => { loaded.value = true }, 100)
})
</script>

<template>
  <section ref="heroRef" class="hero" @mousemove="handleMouseMove">
    <!-- Animated background -->
    <div class="hero-bg">
      <div class="grid-pattern"></div>
      <div
        class="orb orb-1"
        :style="{ transform: `translate(${mouseX * 0.5}px, ${mouseY * 0.5}px)` }"
      ></div>
      <div
        class="orb orb-2"
        :style="{ transform: `translate(${mouseX * -0.3}px, ${mouseY * -0.3}px)` }"
      ></div>
      <div
        class="orb orb-3"
        :style="{ transform: `translate(${mouseX * 0.2}px, ${mouseY * 0.2}px)` }"
      ></div>
    </div>

    <!-- Floating particles -->
    <div class="particles">
      <div
        v-for="p in particles"
        :key="p.id"
        class="particle"
        :style="{
          left: p.x + '%',
          top: p.y + '%',
          width: p.size + 'px',
          height: p.size + 'px',
          animationDelay: p.delay + 's',
          animationDuration: p.duration + 's',
        }"
      ></div>
    </div>

    <!-- Content -->
    <div class="hero-content container" :class="{ loaded }">
      <div class="hero-badge">
        <span class="badge-dot"></span>
        面向理工科新生 · 人工智能通识课
      </div>

      <h1 class="hero-title">
        <span class="title-line">
          <span class="char t">探</span>
          <span class="char-dot">·</span>
          <span class="char p">练</span>
          <span class="char-dot">·</span>
          <span class="char c">创</span>
          <span class="char-dot">·</span>
          <span class="char a">行</span>
        </span>
        <span class="title-sub">在做中学，在行中悟</span>
      </h1>

      <p class="hero-desc">
        从 AI 基础理论到在线练习巩固，从硬件创意实践到社区公益行动<br />
        构建属于你的数字成长档案，从容拥抱智能时代
      </p>

      <div class="hero-actions">
        <button class="btn-primary" @click="router.push('/learn')">
          <span>开始探索</span>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M4 10h12m-4-4l4 4-4 4" stroke="currentColor" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button class="btn-secondary" @click="router.push('/create')">
          浏览学生作品
        </button>
      </div>

      <!-- Module quick access -->
      <div class="hero-modules">
        <div class="module-chip" @click="router.push('/learn')">
          <span class="chip-icon chip-learn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 6.25278V19.2528M12 6.25278C10.8321 5.47686 9.24649 5 7.5 5C5.75351 5 4.16789 5.47686 3 6.25278V19.2528C4.16789 18.4769 5.75351 18 7.5 18C9.24649 18 10.8321 18.4769 12 19.2528M12 6.25278C13.1679 5.47686 14.7535 5 16.5 5C18.2465 5 19.8321 5.47686 21 6.25278V19.2528C19.8321 18.4769 18.2465 18 16.5 18C14.7535 18 13.1679 18.4769 12 19.2528"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span>探 · 学</span>
        </div>
        <div class="module-chip" @click="router.push('/practice')">
          <span class="chip-icon chip-practice">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span>练 · 用</span>
        </div>
        <div class="module-chip" @click="router.push('/create')">
          <span class="chip-icon chip-create">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span>造 · 创</span>
        </div>
        <div class="module-chip" @click="router.push('/act')">
          <span class="chip-icon chip-act">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.841m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span>行 · 悟</span>
        </div>
      </div>
    </div>

    <!-- Scroll indicator -->
    <div class="scroll-hint" :class="{ loaded }">
      <div class="scroll-mouse">
        <div class="scroll-dot"></div>
      </div>
      <span>向下滚动</span>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--gradient-hero);
  padding-top: 64px;
}

/* ── Background ── */
.hero-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 70%);
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  transition: transform 0.3s ease-out;
  will-change: transform;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: rgba(79, 70, 229, 0.25);
  top: -200px;
  right: -100px;
  animation: float1 20s ease-in-out infinite;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: rgba(6, 182, 212, 0.15);
  bottom: -100px;
  left: -50px;
  animation: float2 25s ease-in-out infinite;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: rgba(245, 158, 11, 0.1);
  top: 40%;
  left: 60%;
  animation: float3 18s ease-in-out infinite;
}

@keyframes float1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-40px, 30px) scale(1.1); }
}
@keyframes float2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(30px, -40px) scale(1.05); }
}
@keyframes float3 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-20px, 20px) scale(0.95); }
}

/* ── Particles ── */
.particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.particle {
  position: absolute;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  animation: particleFloat linear infinite;
}

@keyframes particleFloat {
  0% {
    transform: translateY(0) translateX(0);
    opacity: 0;
  }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% {
    transform: translateY(-100vh) translateX(30px);
    opacity: 0;
  }
}

/* ── Content ── */
.hero-content {
  position: relative;
  z-index: 10;
  text-align: center;
  color: white;
  max-width: 800px;
  padding: var(--space-4xl) var(--space-xl);
}

.hero-content > * {
  opacity: 0;
  transform: translateY(24px);
  transition: all 0.8s var(--ease-out);
}

.hero-content.loaded > * {
  opacity: 1;
  transform: translateY(0);
}

.hero-content.loaded > *:nth-child(1) { transition-delay: 0.1s; }
.hero-content.loaded > *:nth-child(2) { transition-delay: 0.25s; }
.hero-content.loaded > *:nth-child(3) { transition-delay: 0.4s; }
.hero-content.loaded > *:nth-child(4) { transition-delay: 0.55s; }
.hero-content.loaded > *:nth-child(5) { transition-delay: 0.7s; }

/* Badge */
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.4rem 1rem;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: var(--space-2xl);
  backdrop-filter: blur(10px);
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

/* Title */
.hero-title {
  margin-bottom: var(--space-xl);
}

.title-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3em;
  font-size: clamp(3rem, 8vw, 5.5rem);
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.char {
  display: inline-block;
  background: linear-gradient(135deg, #fff 0%, rgba(255,255,255,0.8) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  transition: transform 0.4s var(--ease-spring);
}

.char:hover {
  transform: scale(1.1) rotate(-3deg);
}

.char.t { animation: charGlow 4s ease-in-out infinite 0s; }
.char.p { animation: charGlow 4s ease-in-out infinite 1s; }
.char.c { animation: charGlow 4s ease-in-out infinite 2s; }
.char.a { animation: charGlow 4s ease-in-out infinite 3s; }

@keyframes charGlow {
  0%, 100% { filter: drop-shadow(0 0 0 transparent); }
  50% { filter: drop-shadow(0 0 20px rgba(129, 140, 248, 0.5)); }
}

.char-dot {
  font-size: 0.6em;
  color: rgba(255, 255, 255, 0.3);
  font-weight: 300;
}

.title-sub {
  display: block;
  font-size: clamp(1.1rem, 2.5vw, 1.5rem);
  font-weight: 400;
  color: rgba(255, 255, 255, 0.6);
  margin-top: var(--space-md);
  letter-spacing: 0.15em;
}

/* Description */
.hero-desc {
  font-size: clamp(0.9rem, 1.5vw, 1.05rem);
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.8;
  margin-bottom: var(--space-2xl);
}

/* Actions */
.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  margin-bottom: var(--space-3xl);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.85rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-primary-dark);
  background: white;
  border-radius: var(--radius-full);
  transition: all var(--duration-normal) var(--ease-out);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(255, 255, 255, 0.25);
}

.btn-primary svg {
  transition: transform var(--duration-fast) var(--ease-out);
}

.btn-primary:hover svg {
  transform: translateX(4px);
}

.btn-secondary {
  padding: 0.85rem 2rem;
  font-size: 1rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-full);
  transition: all var(--duration-normal) var(--ease-out);
  backdrop-filter: blur(10px);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
}

/* Module chips */
.hero-modules {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.module-chip {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.5rem 1.1rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-full);
  font-size: 0.85rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
  backdrop-filter: blur(10px);
}

.module-chip:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.2);
  color: white;
  transform: translateY(-2px);
}

.chip-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
}

.chip-learn { background: rgba(6, 182, 212, 0.2); color: var(--color-learn-light); }
.chip-practice { background: rgba(139, 92, 246, 0.2); color: var(--color-practice-light); }
.chip-create { background: rgba(245, 158, 11, 0.2); color: var(--color-create-light); }
.chip-act { background: rgba(16, 185, 129, 0.2); color: var(--color-act-light); }

/* Scroll hint */
.scroll-hint {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  color: rgba(255, 255, 255, 0.35);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  opacity: 0;
  transition: opacity 1s var(--ease-out) 1.2s;
}

.scroll-hint.loaded {
  opacity: 1;
}

.scroll-mouse {
  width: 22px;
  height: 34px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 11px;
  display: flex;
  justify-content: center;
  padding-top: 6px;
}

.scroll-dot {
  width: 3px;
  height: 8px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 2px;
  animation: scrollDot 2s ease-in-out infinite;
}

@keyframes scrollDot {
  0%, 100% { transform: translateY(0); opacity: 1; }
  50% { transform: translateY(8px); opacity: 0.3; }
}

@media (max-width: 768px) {
  .hero-content {
    padding: var(--space-2xl) var(--space-lg);
  }

  .hero-actions {
    flex-direction: column;
  }

  .hero-modules {
    gap: var(--space-sm);
  }

  .hero-desc br {
    display: none;
  }
}
</style>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeModule = ref(0)

const modules = [
  {
    key: 'learn',
    icon: '📚',
    tagline: '积累知识',
    title: '学·积累知识',
    subtitle: '系统学习，循序渐进',
    desc: '系统学习 AI 通识课程，从概念到工具，循序渐进掌握人工智能基础知识体系。',
    features: [
      { icon: '&#9678;', text: '核心课程模块，系统构建 AI 知识图谱' },
      { icon: '&#9670;', text: '视频+图文配合，多层次学习体验' },
      { icon: '&#9679;', text: '随时复习，断点续播学习进度' },
    ],
    gradient: 'var(--gradient-card-learn)',
    color: 'var(--color-learn)',
    colorLight: 'var(--color-learn-light)',
    route: '/learn',
  },
  {
    key: 'practice',
    icon: '🧠',
    tagline: '深化理解',
    title: '思·深化理解',
    subtitle: '在线题库，检验成果',
    desc: '通过在线题库和专项练习，检验学习成果，反思知识盲点，强化对AI核心概念的理解。',
    features: [
      { icon: '&#9632;', text: '100+题目，覆盖课程核心知识点' },
      { icon: '&#9670;', text: '即时反馈，错题自动归类' },
      { icon: '&#9679;', text: '错题回顾，精准查漏补缺' },
    ],
    gradient: 'var(--gradient-card-practice)',
    color: 'var(--color-practice)',
    colorLight: 'var(--color-practice-light)',
    route: '/practice',
  },
  {
    key: 'create',
    icon: '🛠️',
    tagline: '动手创作',
    title: '践·动手创作',
    subtitle: '将所学付诸实践',
    desc: '将所学付诸实践，运用AI工具完成创意项目，展示个人作品，在动手中将知识内化为能力。',
    features: [
      { icon: '&#9733;', text: '项目实践，AI工具应用实战' },
      { icon: '&#9670;', text: '作品展示，瀑布流沉浸式浏览' },
      { icon: '&#9679;', text: 'AI工具应用，虚实交融创造体验' },
    ],
    gradient: 'var(--gradient-card-create)',
    color: 'var(--color-create)',
    colorLight: 'var(--color-create-light)',
    route: '/create',
  },
  {
    key: 'act',
    icon: '🌱',
    tagline: '感悟价值',
    title: '悟·感悟价值',
    subtitle: '公益行动，感悟意义',
    desc: '参与AI公益课程与社区行动，思考技术的社会价值与伦理责任，在服务中感悟AI对人类的意义。',
    features: [
      { icon: '&#9830;', text: '公益行动，走进社区与中小学' },
      { icon: '&#9670;', text: '社会价值，思考AI伦理与责任' },
      { icon: '&#9679;', text: '成长档案，能力可视化留存' },
    ],
    gradient: 'var(--gradient-card-act)',
    color: 'var(--color-act)',
    colorLight: 'var(--color-act-light)',
    route: '/act',
  },
]

let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => {
    activeModule.value = (activeModule.value + 1) % modules.length
  }, 6000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <section class="module-showcase">
    <div class="container">
      <!-- Section header -->
      <div class="section-header fade-up">
        <span class="section-tag">核心模块</span>
        <h2 class="section-title">学 · 思 · 践 · 悟 四维并进</h2>
        <p class="section-desc">
          从知识学习到深化反思，从实践创作到感悟价值<br />
          构建完整的 AI 通识成长闭环
        </p>
      </div>

      <!-- Module cards -->
      <div class="modules-grid">
        <div
          v-for="(mod, index) in modules"
          :key="mod.key"
          class="module-card fade-up"
          :class="{ active: activeModule === index }"
          :style="{ '--card-gradient': mod.gradient, '--card-color': mod.color, '--card-color-light': mod.colorLight, transitionDelay: `${index * 0.1}s` }"
          @mouseenter="activeModule = index"
          @click="router.push(mod.route)"
        >
          <div class="card-header">
            <div class="card-icon">{{ mod.icon }}</div>
            <span class="card-tagline">{{ mod.tagline }}</span>
          </div>

          <h3 class="card-title">{{ mod.title }}</h3>
          <p class="card-subtitle">{{ mod.subtitle }}</p>
          <p class="card-desc">{{ mod.desc }}</p>

          <ul class="card-features">
            <li v-for="feat in mod.features" :key="feat.text">
              <span class="feature-check" v-html="feat.icon"></span>
              {{ feat.text }}
            </li>
          </ul>

          <div class="card-footer">
            <span class="card-link">
              进入模块
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                <path d="M4 10h12m-4-4l4 4-4 4" stroke="currentColor" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </div>

          <!-- Glow effect -->
          <div class="card-glow"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.module-showcase {
  padding: var(--space-4xl) 0;
  background: var(--color-bg);
}

/* Section header */
.section-header {
  text-align: center;
  margin-bottom: var(--space-4xl);
}

.section-tag {
  display: inline-block;
  padding: 0.3rem 0.9rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  border-radius: var(--radius-full);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: var(--space-lg);
}

.section-title {
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  letter-spacing: -0.02em;
}

.section-desc {
  font-size: 1rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

/* Module grid */
.modules-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-xl);
}

/* Module card */
.module-card {
  position: relative;
  padding: var(--space-2xl);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
  overflow: hidden;
}

.module-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--card-color);
  opacity: 0;
  transition: opacity var(--duration-normal) var(--ease-out);
}

.module-card:hover,
.module-card.active {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: transparent;
}

.module-card:hover::before,
.module-card.active::before {
  opacity: 1;
}

.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--card-gradient);
  opacity: 0;
  transition: opacity var(--duration-normal) var(--ease-out);
  pointer-events: none;
  z-index: 0;
}

.module-card:hover .card-glow,
.module-card.active .card-glow {
  opacity: 0.4;
}

.module-card > *:not(.card-glow) {
  position: relative;
  z-index: 1;
}

/* Card content */
.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.card-icon {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 900;
  color: white;
  background: var(--card-color);
  border-radius: var(--radius-md);
  transition: transform var(--duration-normal) var(--ease-spring);
}

.module-card:hover .card-icon {
  transform: scale(1.08) rotate(-3deg);
}

.card-tagline {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--card-color);
  letter-spacing: 0.06em;
}

.card-title {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.card-subtitle {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-weight: 500;
  margin-bottom: var(--space-lg);
}

.card-desc {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: var(--space-xl);
}

/* Features */
.card-features {
  margin-bottom: var(--space-xl);
}

.card-features li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  padding: var(--space-sm) 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.feature-check {
  color: var(--card-color);
  font-size: 0.7rem;
  margin-top: 3px;
  flex-shrink: 0;
}

/* Footer */
.card-footer {
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}

.card-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--card-color);
  transition: all var(--duration-fast);
}

.card-link svg {
  transition: transform var(--duration-fast) var(--ease-out);
}

.module-card:hover .card-link svg {
  transform: translateX(4px);
}

@media (max-width: 1024px) {
  .modules-grid {
    grid-template-columns: 1fr;
    max-width: 560px;
    margin: 0 auto;
  }
}
</style>

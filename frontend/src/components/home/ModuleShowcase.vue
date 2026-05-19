<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeModule = ref(0)

const modules = [
  {
    key: 'learn',
    icon: '探',
    tagline: '学无止境',
    title: '探 · 学无止境',
    subtitle: '从零构建 AI 知识体系',
    desc: '六大核心章节覆盖人工智能全景：从概述、计算机基础、深度学习理论，到大模型与智能体工具应用、专业前沿探索以及 AI 伦理思辨。视频课程配合课件，让知识触手可及。',
    features: [
      { icon: '&#9678;', text: '六大核心章节，系统构建 AI 知识图谱' },
      { icon: '&#9670;', text: 'HLS 自适应码率视频，校园网流畅播放' },
      { icon: '&#9679;', text: '学习进度智能追踪，断点续播' },
      { icon: '&#9632;', text: '课件资料随时下载，离线也能学' },
    ],
    gradient: 'var(--gradient-card-learn)',
    color: 'var(--color-learn)',
    colorLight: 'var(--color-learn-light)',
    route: '/learn',
  },
  {
    key: 'practice',
    icon: '练',
    tagline: '学以致用',
    title: '练 · 学以致用',
    subtitle: '以题促学，巩固知识',
    desc: '告别纸质作业，在线即练即批。选择题与填空题覆盖六大章节核心知识点，实时反馈答题结果与解析。按章节分类练习，智能追踪学习进度，让每一次练习都有收获。',
    features: [
      { icon: '&#9632;', text: '选择题 + 填空题，覆盖全章节知识点' },
      { icon: '&#9670;', text: '即时批改反馈，错题自动归类' },
      { icon: '&#9679;', text: '按章节分类练习，精准查漏补缺' },
      { icon: '&#9733;', text: '练习进度与正确率可视化追踪' },
    ],
    gradient: 'var(--gradient-card-practice)',
    color: 'var(--color-practice)',
    colorLight: 'var(--color-practice-light)',
    route: '/practice',
  },
  {
    key: 'create',
    icon: '造',
    tagline: '智创未来',
    title: '造 · 智创未来',
    subtitle: '软硬融合，做中学',
    desc: '打破"AI 只是聊天框"的思维局限。每位学生将 AI 功能与物理硬件相结合——机器视觉分类、大模型驱动的机器人、智能传感器系统。上传课程报告、演示视频，展示你的创意作品。',
    features: [
      { icon: '&#9733;', text: 'AI + 硬件项目，虚实交融的创造体验' },
      { icon: '&#9670;', text: '优秀作品画廊，瀑布流沉浸式浏览' },
      { icon: '&#9679;', text: '教师一键打包下载，高效归档' },
      { icon: '&#9632;', text: '文件安全上传，魔数校验防恶意文件' },
    ],
    gradient: 'var(--gradient-card-create)',
    color: 'var(--color-create)',
    colorLight: 'var(--color-create-light)',
    route: '/create',
  },
  {
    key: 'act',
    icon: '行',
    tagline: '知行合一',
    title: '行 · 知行合一',
    subtitle: '用 AI 温暖社会',
    desc: '将技术学习升华为社会责任。走进社区和中小学开展 AI 公益课，参与读书会研讨，记录成长轨迹。AI 成长档案汇聚学习时长、练习正确率、创意作品评价，生成多维能力画像。',
    features: [
      { icon: '&#9830;', text: 'AI 公益课行动记录，走进社区与中小学' },
      { icon: '&#9670;', text: '读书会研讨，思想碰撞激发灵感' },
      { icon: '&#9679;', text: '电子成长档案（E-Portfolio），能力可视化' },
      { icon: '&#9632;', text: '雷达图 + 时间轴，看见自己的成长轨迹' },
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
        <h2 class="section-title">学 · 练 · 创 · 行 四位一体</h2>
        <p class="section-desc">
          从知识学习到练习巩固，从创意创造到行动传播<br />
          构建完整的 AI 素养成长闭环
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

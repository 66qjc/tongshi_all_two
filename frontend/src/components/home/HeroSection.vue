<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/* ── 四个模块数据（颜色取自全局设计令牌） ── */
interface OrbitModule {
  char: string
  name: string
  en: string
  desc: string
  route: string
  color: string
}
const modules: OrbitModule[] = [
  { char: '学', name: '公开学习', en: 'LEARN', desc: '浏览 AI 通识教程与阶段化学习资料，游客可直接阅读。', route: '/learn', color: 'var(--color-learn)' },
  { char: '思', name: '练习作业', en: 'PRACTICE', desc: '通过练习、作业与错题回顾检验理解，巩固每个知识点。', route: '/practice', color: 'var(--color-practice)' },
  { char: '践', name: '实践作品', en: 'CREATE', desc: '提交自己的实践成果，浏览同学们的创作与项目。', route: '/create', color: 'var(--color-create)' },
  { char: '悟', name: '公益行动', en: 'ACT', desc: '在公益课、读书会与真实行动中理解技术的价值。', route: '/act', color: 'var(--color-act)' },
]

const active = ref(0)
// active 始终落在 0~3，配合回退保证类型非空
const currentModule = computed<OrbitModule>(() => modules[active.value] ?? (modules[0] as OrbitModule))
const hoverIdx = ref<number | null>(null)
const manualIdx = ref<number | null>(null)

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const coarsePointer = window.matchMedia('(hover: none), (pointer: coarse)').matches

const heroEl = ref<HTMLElement | null>(null)
const copyEl = ref<HTMLElement | null>(null)
const orbitEl = ref<HTMLElement | null>(null)
const bgCanvas = ref<HTMLCanvasElement | null>(null)
// 柔光弧/点在挂载后直接查询缓存（比 SVG 模板 ref 更稳妥）
let arcEl: SVGCircleElement | null = null
let dotEl: SVGCircleElement | null = null

/* ══ 学习之环：流转柔光 + 节点联动 ══ */
const LOOP = 16000 // 柔光绕环一周毫秒数，越慢越稳
let progress = 0
let lastT: number | null = null
let ringRaf: number | null = null

function nearestIdx(p: number) {
  return Math.round(p / 25) % 4
}
function activeIdx() {
  if (hoverIdx.value !== null) return hoverIdx.value
  if (manualIdx.value !== null) return manualIdx.value
  return nearestIdx(progress)
}
function tick(now: number) {
  if (lastT === null) lastT = now
  const dt = now - lastT
  lastT = now
  // 无人交互时柔光持续流转；悬停/点选时驻留对焦
  if (hoverIdx.value === null && manualIdx.value === null) {
    progress = (progress + (dt / LOOP) * 100) % 100
  }
  if (arcEl) arcEl.setAttribute('stroke-dashoffset', String(-progress))
  if (dotEl) {
    const ang = (progress / 100) * Math.PI * 2 - Math.PI / 2
    dotEl.setAttribute('cx', String(100 + 78 * Math.cos(ang)))
    dotEl.setAttribute('cy', String(100 + 78 * Math.sin(ang)))
  }
  const idx = activeIdx()
  if (idx !== active.value) active.value = idx
  ringRaf = requestAnimationFrame(tick)
}
function startRing() {
  if (ringRaf === null && !reduceMotion) ringRaf = requestAnimationFrame(tick)
}
function stopRing() {
  if (ringRaf !== null) {
    cancelAnimationFrame(ringRaf)
    ringRaf = null
  }
}

function onEnter(i: number) {
  hoverIdx.value = i
}
function onLeave() {
  hoverIdx.value = null
}
function onNodeClick(i: number) {
  const m = modules[i]
  if (!m) return
  if (coarsePointer) {
    // 触摸：第一次点按驻留展示，第二次点按进入
    if (manualIdx.value === i) router.push(m.route)
    else manualIdx.value = i
  } else {
    router.push(m.route)
  }
}
function onTouchStart(e: TouchEvent) {
  if (!(e.target as HTMLElement).closest('.node')) manualIdx.value = null
}

/* ══ 极淡墨点漂移场（背景生命感） ══ */
interface Dot {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  s: number
}
let ctx: CanvasRenderingContext2D | null = null
let W = 0
let H = 0
let dots: Dot[] = []
const mouse = { x: -9999, y: -9999 }
let bgRaf: number | null = null
let bgRunning = true
let inView = true

function sizeCanvas() {
  const canvas = bgCanvas.value
  const hero = heroEl.value
  if (!canvas || !hero) return
  const DPR = Math.min(window.devicePixelRatio || 1, 2)
  const r = hero.getBoundingClientRect()
  W = Math.max(1, Math.round(r.width))
  H = Math.max(1, Math.round(r.height))
  canvas.width = W * DPR
  canvas.height = H * DPR
  canvas.style.width = W + 'px'
  canvas.style.height = H + 'px'
  ctx = canvas.getContext('2d')
  if (ctx) ctx.setTransform(DPR, 0, 0, DPR, 0, 0)
  seedDots()
  if (reduceMotion) drawDots()
}
function seedDots() {
  const n = Math.round(Math.min(64, Math.max(34, (W * H) / 26000)))
  dots = []
  for (let i = 0; i < n; i++) {
    dots.push({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.12,
      vy: (Math.random() - 0.5) * 0.12,
      r: Math.random() * 1.5 + 0.7,
      s: Math.random() * 1000,
    })
  }
}
function stepDots() {
  for (const p of dots) {
    const a = (Math.sin(p.x * 0.0016 + p.s) + Math.cos(p.y * 0.0015)) * Math.PI
    p.vx += Math.cos(a) * 0.006
    p.vy += Math.sin(a) * 0.006
    const dx = p.x - mouse.x
    const dy = p.y - mouse.y
    const d = Math.sqrt(dx * dx + dy * dy) || 1
    if (d < 130) {
      const f = (130 - d) / 130
      p.vx -= (dx / d) * f * 0.06
      p.vy -= (dy / d) * f * 0.06
    }
    p.vx *= 0.96
    p.vy *= 0.96
    const sp = Math.sqrt(p.vx * p.vx + p.vy * p.vy)
    const max = 0.32
    if (sp > max) {
      p.vx = (p.vx / sp) * max
      p.vy = (p.vy / sp) * max
    }
    p.x += p.vx
    p.y += p.vy
    if (p.x < -20) p.x = W + 20
    else if (p.x > W + 20) p.x = -20
    if (p.y < -20) p.y = H + 20
    else if (p.y > H + 20) p.y = -20
  }
}
function drawDots() {
  if (!ctx) return
  ctx.clearRect(0, 0, W, H)
  const LINK = 116
  ctx.lineWidth = 1
  for (let i = 0; i < dots.length; i++) {
    const p = dots[i]!
    for (let j = i + 1; j < dots.length; j++) {
      const q = dots[j]!
      const dx = p.x - q.x
      const dy = p.y - q.y
      if (Math.abs(dx) > LINK || Math.abs(dy) > LINK) continue
      const d = Math.sqrt(dx * dx + dy * dy)
      if (d < LINK) {
        ctx.strokeStyle = `rgba(45,90,110,${((1 - d / LINK) * 0.1).toFixed(3)})`
        ctx.beginPath()
        ctx.moveTo(p.x, p.y)
        ctx.lineTo(q.x, q.y)
        ctx.stroke()
      }
    }
  }
  for (const p of dots) {
    ctx.fillStyle = 'rgba(45,90,110,0.28)'
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fill()
  }
}
function bgFrame() {
  stepDots()
  drawDots()
  bgRaf = requestAnimationFrame(bgFrame)
}
function startBg() {
  if (bgRaf === null && bgRunning && inView && !reduceMotion) bgRaf = requestAnimationFrame(bgFrame)
}
function stopBg() {
  if (bgRaf !== null) {
    cancelAnimationFrame(bgRaf)
    bgRaf = null
  }
}
function onHeroMouseMove(e: MouseEvent) {
  const hero = heroEl.value
  if (!hero) return
  const r = hero.getBoundingClientRect()
  mouse.x = e.clientX - r.left
  mouse.y = e.clientY - r.top
}
function onHeroMouseLeave() {
  mouse.x = -9999
  mouse.y = -9999
}

/* ══ 克制的视差与磁吸按钮（transform，不触发布局） ══ */
let parRaf: number | null = null
const motionCleanups: Array<() => void> = []
function setupMotion() {
  if (reduceMotion || coarsePointer) return
  let tx = 0
  let ty = 0
  let cx = 0
  let cy = 0
  const onMove = (e: MouseEvent) => {
    tx = e.clientX / window.innerWidth - 0.5
    ty = e.clientY / window.innerHeight - 0.5
  }
  heroEl.value?.addEventListener('mousemove', onMove, { passive: true })
  const par = () => {
    cx += (tx - cx) * 0.05
    cy += (ty - cy) * 0.05
    if (copyEl.value) copyEl.value.style.transform = `translate(${(cx * 7).toFixed(2)}px,${(cy * 5).toFixed(2)}px)`
    if (orbitEl.value) orbitEl.value.style.transform = `translate(${(-cx * 9).toFixed(2)}px,${(-cy * 7).toFixed(2)}px)`
    parRaf = requestAnimationFrame(par)
  }
  parRaf = requestAnimationFrame(par)
  motionCleanups.push(() => heroEl.value?.removeEventListener('mousemove', onMove))

  heroEl.value?.querySelectorAll<HTMLElement>('[data-magnetic]').forEach((el) => {
    let r: DOMRect | null = null
    let mx = 0
    let my = 0
    let px = 0
    let py = 0
    let id: number | null = null
    const loop = () => {
      px += (mx - px) * 0.18
      py += (my - py) * 0.18
      el.style.transform = `translate(${px.toFixed(2)}px,${py.toFixed(2)}px)`
      if (Math.abs(px - mx) > 0.1 || Math.abs(py - my) > 0.1) id = requestAnimationFrame(loop)
      else {
        el.style.transform = ''
        id = null
      }
    }
    const enter = () => {
      r = el.getBoundingClientRect()
    }
    const move = (e: MouseEvent) => {
      if (!r) r = el.getBoundingClientRect()
      mx = (e.clientX - (r.left + r.width / 2)) * 0.14
      my = (e.clientY - (r.top + r.height / 2)) * 0.22
      if (id === null) id = requestAnimationFrame(loop)
    }
    const leave = () => {
      mx = 0
      my = 0
      r = null
      if (id === null) id = requestAnimationFrame(loop)
    }
    el.addEventListener('mouseenter', enter)
    el.addEventListener('mousemove', move)
    el.addEventListener('mouseleave', leave)
    motionCleanups.push(() => {
      el.removeEventListener('mouseenter', enter)
      el.removeEventListener('mousemove', move)
      el.removeEventListener('mouseleave', leave)
      if (id !== null) cancelAnimationFrame(id)
    })
  })
}

/* ══ 可见性节能 ══ */
let io: IntersectionObserver | null = null
function onVis() {
  bgRunning = !document.hidden
  if (bgRunning) {
    startBg()
    startRing()
  } else {
    stopBg()
    stopRing()
  }
}
let resizeT: number | undefined
function onResize() {
  window.clearTimeout(resizeT)
  resizeT = window.setTimeout(sizeCanvas, 120)
}

onMounted(() => {
  arcEl = heroEl.value?.querySelector<SVGCircleElement>('.pulse-arc') ?? null
  dotEl = heroEl.value?.querySelector<SVGCircleElement>('.pulse-dot') ?? null
  sizeCanvas()
  if (reduceMotion) {
    drawDots()
  } else {
    startBg()
    startRing()
    setupMotion()
    heroEl.value?.addEventListener('mousemove', onHeroMouseMove, { passive: true })
    heroEl.value?.addEventListener('mouseleave', onHeroMouseLeave)
  }
  document.addEventListener('visibilitychange', onVis)
  document.addEventListener('touchstart', onTouchStart, { passive: true })
  window.addEventListener('resize', onResize)
  if ('IntersectionObserver' in window && heroEl.value) {
    io = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (!entry) return
        inView = entry.isIntersecting
        if (inView) {
          startBg()
          startRing()
        } else {
          stopBg()
          stopRing()
        }
      },
      { threshold: 0.04 }
    )
    io.observe(heroEl.value)
  }
})

onUnmounted(() => {
  stopRing()
  stopBg()
  if (parRaf !== null) cancelAnimationFrame(parRaf)
  motionCleanups.forEach((fn) => fn())
  document.removeEventListener('visibilitychange', onVis)
  document.removeEventListener('touchstart', onTouchStart)
  window.removeEventListener('resize', onResize)
  heroEl.value?.removeEventListener('mousemove', onHeroMouseMove)
  heroEl.value?.removeEventListener('mouseleave', onHeroMouseLeave)
  io?.disconnect()
})
</script>

<template>
  <section ref="heroEl" class="hero" aria-label="平台首屏">
    <canvas ref="bgCanvas" class="hero-bg" aria-hidden="true"></canvas>

    <div class="hero-grid">
      <!-- 左栏文案 -->
      <div ref="copyEl" class="hero-copy">
        <span class="kicker">
          <img src="/cjlu-logo.svg" alt="" aria-hidden="true" />
          中国计量大学<span class="sep">·</span>AI 通识课平台
        </span>
        <h1 class="hero-title">
          <span class="cycle">学 · 思 · 践 · 悟</span>
          AI 通识，<span class="hl">从这里开始</span>
        </h1>
        <p class="hero-desc">面向所有学习者开放的 AI 通识学习入口，串联知识学习、理解训练、实践创作与社会行动。游客可直接浏览公开课程，登录后继续保存学习进度。</p>
        <div class="hero-ctas">
          <router-link class="btn btn-primary" to="/learn" data-magnetic>进入公开学习 <span class="arr">→</span></router-link>
          <router-link class="btn btn-ghost" to="/login" data-magnetic>登录保存进度</router-link>
        </div>
        <p class="hero-hint"><span class="pulse-dot"></span>学习之环持续流转，悬停或点按任意一字，点亮对应入口</p>
      </div>

      <!-- 右栏 · 学习之环 -->
      <div ref="orbitEl" class="hero-orbit">
        <div class="orbit-wrap">
          <svg class="ring" viewBox="0 0 200 200" aria-hidden="true">
            <circle cx="100" cy="100" r="78" fill="none" class="ring-base" />
            <circle cx="100" cy="100" r="78" fill="none" class="ring-ticks" />
            <circle
              class="pulse-arc"
              cx="100"
              cy="100"
              r="78"
              fill="none"
              pathLength="100"
              stroke-dasharray="15 85"
              stroke-dashoffset="0"
              transform="rotate(-90 100 100)"
              :style="{ stroke: currentModule.color }"
            />
            <circle class="pulse-dot" cx="100" cy="22" r="3.4" :style="{ fill: currentModule.color }" />
            <circle cx="100" cy="22" r="2.2" class="anchor" />
            <circle cx="178" cy="100" r="2.2" class="anchor" />
            <circle cx="100" cy="178" r="2.2" class="anchor" />
            <circle cx="22" cy="100" r="2.2" class="anchor" />
          </svg>

          <div class="orbit-core">
            <img src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png" alt="深度学思践悟平台标识" />
          </div>

          <button
            v-for="(m, i) in modules"
            :key="m.char"
            class="node"
            :class="{ 'is-active': i === active }"
            :data-i="i"
            type="button"
            :style="{ '--nc': m.color }"
            :aria-label="`${m.char} · ${m.name}`"
            @mouseenter="onEnter(i)"
            @mouseleave="onLeave"
            @focus="onEnter(i)"
            @blur="onLeave"
            @click="onNodeClick(i)"
          >
            <span class="node-char">{{ m.char }}</span>
          </button>
        </div>

        <!-- 模块信息板 -->
        <div class="orbit-panel" :style="{ '--pc': currentModule.color }" role="status" aria-live="polite">
          <div :key="active" class="p-swap">
            <span class="p-badge"><span>{{ currentModule.char }}</span></span>
            <div class="p-main">
              <div class="p-name">
                <span>{{ currentModule.name }}</span>
                <span class="en">{{ currentModule.en }}</span>
              </div>
              <p class="p-desc">{{ currentModule.desc }}</p>
            </div>
          </div>
          <router-link class="p-go" :to="currentModule.route">进入 <span class="arr">→</span></router-link>
        </div>
      </div>
    </div>

    <div class="scroll-cue" aria-hidden="true"><span>向下浏览</span><span class="chev"></span></div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  min-height: 100svh;
  padding: calc(62px + 2vh) clamp(1.1rem, 4vw, 2.6rem) 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.hero-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
  z-index: 0;
}
.hero-grid {
  position: relative;
  z-index: 2;
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.02fr) minmax(0, 0.98fr);
  gap: clamp(1.5rem, 4vw, 3rem);
  align-items: center;
  max-width: 1180px;
  width: 100%;
  margin: 0 auto;
}

/* 左栏文案 */
.hero-copy {
  max-width: 560px;
}
.kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.34rem 0.8rem 0.34rem 0.4rem;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  box-shadow: var(--shadow-sm);
}
.kicker img {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  object-fit: contain;
  background: #fff;
}
.kicker .sep {
  color: var(--color-border);
}
.hero-title {
  margin-top: 1.1rem;
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: clamp(2.1rem, 4.6vw, 3.3rem);
  line-height: 1.16;
  letter-spacing: 0.01em;
  color: var(--color-text);
  text-wrap: balance;
}
.hero-title .cycle {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.42em;
  font-weight: 700;
  letter-spacing: 0.28em;
  color: var(--color-primary);
}
.hero-title .hl {
  color: var(--color-primary);
}
.hero-desc {
  margin-top: 1rem;
  max-width: 50ch;
  font-size: 0.99rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
  text-wrap: pretty;
}
.hero-ctas {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1.5rem;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.82rem 1.4rem;
  font-size: 0.95rem;
  font-weight: 700;
  border-radius: var(--radius-md);
  transition: transform 0.18s var(--ease-out), background 0.18s var(--ease-out), border-color 0.18s var(--ease-out),
    box-shadow 0.18s var(--ease-out);
  will-change: transform;
}
.btn .arr {
  transition: transform 0.18s var(--ease-out);
}
.btn:hover .arr {
  transform: translateX(3px);
}
.btn-primary {
  color: #fff;
  background: var(--color-primary);
  box-shadow: 0 8px 22px rgba(45, 90, 110, 0.26);
}
.btn-primary:hover {
  background: var(--color-primary-dark);
}
.btn-ghost {
  color: var(--color-text);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
}
.btn-ghost:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.hero-hint {
  margin-top: 1.3rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}
.hero-hint .pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: hint 2.2s var(--ease-out) infinite;
}
@keyframes hint {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

/* 右栏 · 学习之环 */
.hero-orbit {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.1rem;
}
.orbit-wrap {
  position: relative;
  width: min(430px, 82vw);
  aspect-ratio: 1 / 1;
}
.ring {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
}
.ring-base {
  stroke: var(--color-border);
  stroke-width: 1;
}
.ring-ticks {
  stroke: var(--color-border-light);
  stroke-width: 1;
  stroke-dasharray: 1.5 5;
}
.pulse-arc {
  stroke-width: 2;
  stroke-linecap: round;
  transition: stroke 0.5s var(--ease-out);
}
.pulse-dot {
  transition: fill 0.5s var(--ease-out);
}
.anchor {
  fill: var(--color-border);
}

.orbit-core {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 37%;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 9%;
}
.orbit-core img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.node {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-bg-card);
  border: 1.5px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.35s var(--ease-out), background 0.35s var(--ease-out), border-color 0.35s var(--ease-out),
    box-shadow 0.35s var(--ease-out);
  will-change: transform;
  -webkit-tap-highlight-color: transparent;
}
.node .node-char {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: 1.7rem;
  color: var(--color-text);
  transition: color 0.3s var(--ease-out);
}
.node[data-i='0'] {
  left: 50%;
  top: 11%;
}
.node[data-i='1'] {
  left: 89%;
  top: 50%;
}
.node[data-i='2'] {
  left: 50%;
  top: 89%;
}
.node[data-i='3'] {
  left: 11%;
  top: 50%;
}
.node:hover,
.node:focus-visible {
  transform: translate(-50%, -50%) scale(1.1);
  border-color: var(--nc);
}
.node.is-active {
  background: var(--nc);
  border-color: var(--nc);
  transform: translate(-50%, -50%) scale(1.14);
  box-shadow: 0 0 0 8px color-mix(in srgb, var(--nc) 16%, transparent), 0 12px 28px color-mix(in srgb, var(--nc) 34%, transparent);
}
.node.is-active .node-char {
  color: #fff;
}

/* 模块信息板 */
.orbit-panel {
  position: relative;
  z-index: 2;
  width: min(430px, 82vw);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 1rem 1.2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: border-color 0.3s var(--ease-out);
}
.p-swap {
  flex: 1;
  min-width: 0;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 1rem;
  animation: panelIn 0.45s var(--ease-out);
}
@keyframes panelIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.p-badge {
  flex: 0 0 46px;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--pc, var(--color-primary));
  transition: background 0.35s var(--ease-out);
}
.p-badge span {
  font-family: var(--font-serif);
  font-weight: 900;
  font-size: 1.3rem;
  color: #fff;
}
.p-main {
  flex: 1;
  min-width: 0;
}
.p-name {
  font-weight: 800;
  font-size: 1rem;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}
.p-name .en {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
}
.p-desc {
  font-size: 0.83rem;
  color: var(--color-text-secondary);
  line-height: 1.55;
  margin-top: 0.15rem;
  min-height: 2.6em;
}
.p-go {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--pc, var(--color-primary));
  transition: color 0.3s var(--ease-out);
}
.p-go .arr {
  transition: transform 0.18s var(--ease-out);
}
.p-go:hover .arr {
  transform: translateX(3px);
}

/* 滚动提示 */
.scroll-cue {
  position: relative;
  z-index: 2;
  margin: 1.4rem auto 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  color: var(--color-text-muted);
}
.scroll-cue .chev {
  width: 13px;
  height: 13px;
  border-right: 2px solid var(--color-text-muted);
  border-bottom: 2px solid var(--color-text-muted);
  transform: rotate(45deg);
  animation: cue 1.9s var(--ease-out) infinite;
}
@keyframes cue {
  0% {
    transform: rotate(45deg) translate(-3px, -3px);
    opacity: 0;
  }
  45% {
    opacity: 1;
  }
  100% {
    transform: rotate(45deg) translate(4px, 4px);
    opacity: 0;
  }
}

/* 响应式 */
@media (max-width: 899px) {
  .hero {
    padding-top: calc(62px + 1vh);
  }
  .hero-grid {
    grid-template-columns: 1fr;
    gap: 1.6rem;
    align-items: start;
  }
  .hero-copy {
    max-width: 100%;
  }
  .hero-orbit {
    order: 2;
  }
  .orbit-wrap {
    width: min(360px, 80vw);
  }
  .orbit-panel {
    width: min(430px, 92vw);
  }
  .scroll-cue {
    display: none;
  }
}
@media (max-width: 480px) {
  .node {
    width: 56px;
    height: 56px;
  }
  .node .node-char {
    font-size: 1.45rem;
  }
  .orbit-panel {
    flex-wrap: wrap;
  }
}

/* 减少动态偏好 */
@media (prefers-reduced-motion: reduce) {
  .p-swap,
  .scroll-cue .chev,
  .hero-hint .pulse-dot {
    animation: none;
  }
}
</style>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getUnreadCount } from '@/api/announcement'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const scrolled = ref(false)
const mobileMenuOpen = ref(false)
const unreadCount = ref(0)

async function fetchUnreadCount() {
  if (!authStore.isLoggedIn || authStore.user?.role !== 'student') return
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.count
  } catch {}
}

const navItems = [
  { name: '学 · 积累知识', path: '/learn', icon: '&#9678;' },
  { name: '思 · 深化理解', path: '/practice', icon: '&#9632;' },
  { name: '践 · 动手创作', path: '/create', icon: '&#9733;' },
  { name: '悟 · 感悟价值', path: '/act', icon: '&#9830;' },
]

function handleScroll() {
  scrolled.value = window.scrollY > 20
}

function navigateTo(path: string) {
  router.push(path)
  mobileMenuOpen.value = false
}

function handleLogout() {
  authStore.logout()
  mobileMenuOpen.value = false
  router.push('/')
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
  fetchUnreadCount()
})
onUnmounted(() => window.removeEventListener('scroll', handleScroll))
</script>

<template>
  <header class="app-header" :class="{ scrolled }">
    <div class="header-inner container">
      <!-- Logo -->
      <router-link to="/" class="logo" @click="mobileMenuOpen = false">
        <span class="logo-icon">
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
            <defs>
              <radialGradient id="inkGrad" cx="40%" cy="38%" r="60%">
                <stop offset="0%" stop-color="#3d2e1a"/>
                <stop offset="60%" stop-color="#1a1208"/>
                <stop offset="100%" stop-color="#0d0a05"/>
              </radialGradient>
            </defs>
            <!-- 外环描边（金色） -->
            <circle cx="18" cy="18" r="17" fill="url(#inkGrad)" stroke="#c9a84c" stroke-width="1.2" opacity="0.9"/>
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
        </span>
        <span class="logo-text">
          <span class="logo-main">学 · 思 · 践 · 悟</span>
          <span class="logo-sub">AI 通识课平台</span>
        </span>
      </router-link>

      <!-- Desktop Nav -->
      <nav class="nav-desktop">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: route.path === item.path }"
        >
          {{ item.name }}
        </router-link>
      </nav>

      <!-- Right actions -->
      <div class="header-actions">
        <template v-if="authStore.isLoggedIn">
          <router-link v-if="authStore.user?.role === 'teacher'" to="/teacher" class="nav-link teacher-link">
            教师工作台
          </router-link>
          <router-link v-if="authStore.user?.role === 'admin'" to="/admin" class="nav-link teacher-link">
            后台管理
          </router-link>
          <router-link v-if="authStore.user?.role === 'student'" to="/inbox" class="notification-bell">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
          </router-link>
          <router-link to="/profile" class="nav-link">个人中心</router-link>
          <span class="user-name">{{ authStore.user?.name }}</span>
          <button class="btn-logout" @click="handleLogout">退出</button>
        </template>
        <template v-else>
          <button class="btn-login" @click="navigateTo('/login')">
            登录
          </button>
        </template>
      </div>

      <!-- Mobile hamburger -->
      <button class="hamburger" @click="mobileMenuOpen = !mobileMenuOpen"
              :class="{ open: mobileMenuOpen }">
        <span></span><span></span><span></span>
      </button>
    </div>

    <!-- Mobile Nav -->
    <transition name="slide-down">
      <div v-if="mobileMenuOpen" class="mobile-nav">
        <a
          v-for="item in navItems"
          :key="item.path"
          class="mobile-nav-link"
          @click="navigateTo(item.path)"
        >
          {{ item.name }}
        </a>
        <template v-if="authStore.isLoggedIn">
          <router-link v-if="authStore.user?.role === 'student'" to="/inbox"
                       class="mobile-nav-link" @click="mobileMenuOpen = false">
            消息通知{{ unreadCount > 0 ? ` (${unreadCount})` : '' }}
          </router-link>
          <router-link v-if="authStore.user?.role === 'teacher'" to="/teacher"
                       class="mobile-nav-link" @click="mobileMenuOpen = false">
            教师工作台
          </router-link>
          <router-link v-if="authStore.user?.role === 'admin'" to="/admin"
                       class="mobile-nav-link" @click="mobileMenuOpen = false">
            后台管理
          </router-link>
          <router-link to="/profile" class="mobile-nav-link" @click="mobileMenuOpen = false">
            个人中心
          </router-link>
          <button class="btn-login mobile-cta" @click="handleLogout">
            退出登录
          </button>
        </template>
        <template v-else>
          <button class="btn-login mobile-cta" @click="navigateTo('/login')">
            登录
          </button>
        </template>
      </div>
    </transition>
  </header>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(248, 245, 239, 0.78);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border-bottom: 1px solid transparent;
  transition: all var(--duration-normal) var(--ease-out);
}

.app-header.scrolled {
  background: rgba(248, 245, 239, 0.94);
  border-bottom-color: var(--color-border);
  box-shadow: var(--shadow-xs);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  text-decoration: none;
  flex-shrink: 0;
}

.logo-icon {
  display: flex;
  align-items: center;
  transition: transform var(--duration-normal) var(--ease-spring);
}

.logo:hover .logo-icon {
  transform: rotate(-8deg) scale(1.08);
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-main {
  font-family: var(--font-serif);
  font-size: 1rem;
  font-weight: 900;
  color: var(--color-text);
  letter-spacing: 0.08em;
}

.logo-sub {
  font-size: 0.6rem;
  color: var(--color-text-muted);
  font-weight: 500;
  letter-spacing: 0.1em;
}

/* Desktop Nav */
.nav-desktop {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.nav-link {
  padding: var(--space-sm) var(--space-md);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.nav-link:hover {
  color: var(--color-primary);
  background: var(--color-primary-glow);
}

.nav-link.active {
  color: var(--color-primary);
  font-weight: 600;
  position: relative;
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: 2px;
  left: var(--space-md);
  right: var(--space-md);
  height: 2px;
  background: var(--color-primary);
  border-radius: 1px;
}

/* Actions */
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.btn-login {
  padding: 0.45rem 1.2rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: white;
  background: var(--color-primary);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.btn-login:hover {
  background: var(--color-primary-light);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(45, 90, 110, 0.25);
}

.btn-login:active {
  transform: translateY(0);
}

.user-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-text);
}

.btn-logout {
  padding: 0.35rem 0.9rem;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.btn-logout:hover {
  border-color: #c0392b;
  color: #c0392b;
}

.teacher-link {
  color: var(--color-primary) !important;
  font-weight: 600 !important;
}

.notification-bell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.notification-bell:hover {
  color: var(--color-primary);
  background: var(--color-primary-glow);
}

.badge {
  position: absolute;
  top: 2px;
  right: 0;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 0.6rem;
  font-weight: 700;
  color: white;
  background: #c0392b;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

/* Hamburger */
.hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 32px;
  height: 32px;
  padding: 4px;
}

.hamburger span {
  display: block;
  height: 1.5px;
  background: var(--color-text);
  transition: all var(--duration-fast) var(--ease-out);
}

.hamburger.open span:nth-child(1) {
  transform: rotate(45deg) translateY(5px);
}
.hamburger.open span:nth-child(2) {
  opacity: 0;
}
.hamburger.open span:nth-child(3) {
  transform: rotate(-45deg) translateY(-5px);
}

/* Mobile Nav */
.mobile-nav {
  display: none;
  flex-direction: column;
  padding: var(--space-md) var(--space-xl) var(--space-xl);
  gap: var(--space-xs);
  border-top: 1px solid var(--color-border-light);
  background: rgba(248, 245, 239, 0.98);
}

.mobile-nav-link {
  padding: var(--space-md);
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.mobile-nav-link:hover {
  background: var(--color-primary-glow);
  color: var(--color-primary);
}

.mobile-cta {
  margin-top: var(--space-sm);
  text-align: center;
}

/* Transition */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all var(--duration-normal) var(--ease-out);
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 768px) {
  .nav-desktop,
  .header-actions {
    display: none;
  }

  .hamburger {
    display: flex;
  }

  .mobile-nav {
    display: flex;
  }
}
</style>

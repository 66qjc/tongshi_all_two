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
  { name: '探 · 学无止境', path: '/learn', icon: '&#9678;' },
  { name: '练 · 学以致用', path: '/practice', icon: '&#9632;' },
  { name: '造 · 智创未来', path: '/create', icon: '&#9733;' },
  { name: '行 · 知行合一', path: '/act', icon: '&#9830;' },
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
          <svg viewBox="0 0 32 32" width="28" height="28">
            <defs>
              <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color: var(--color-primary)" />
                <stop offset="100%" style="stop-color: var(--color-learn)" />
              </linearGradient>
            </defs>
            <circle cx="16" cy="16" r="14" fill="url(#logoGrad)" />
            <text x="16" y="21" text-anchor="middle" font-size="13" font-weight="700"
                  fill="white" font-family="sans-serif">探</text>
          </svg>
        </span>
        <span class="logo-text">
          <span class="logo-main">探 · 练 · 创 · 行</span>
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
          <router-link v-if="authStore.user?.role === 'student'" to="/inbox" class="notification-bell">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
          </router-link>
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
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid transparent;
  transition: all var(--duration-normal) var(--ease-out);
}

.app-header.scrolled {
  background: rgba(255, 255, 255, 0.92);
  border-bottom-color: var(--color-border);
  box-shadow: var(--shadow-xs);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
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
  transform: rotate(-10deg) scale(1.1);
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-main {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: 0.02em;
}

.logo-sub {
  font-size: 0.65rem;
  color: var(--color-text-muted);
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* Desktop Nav */
.nav-desktop {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.nav-link {
  padding: var(--space-sm) var(--space-md);
  font-size: 0.875rem;
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
  background: var(--color-primary-glow);
  font-weight: 600;
}

/* Actions */
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.btn-login {
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
  background: var(--gradient-cta);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.btn-login:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.35);
}

.btn-login:active {
  transform: translateY(0);
}

.user-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
}

.btn-logout {
  padding: 0.4rem 1rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.btn-logout:hover {
  border-color: #ef4444;
  color: #ef4444;
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
  border-radius: var(--radius-full);
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
  background: #ef4444;
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
  height: 2px;
  background: var(--color-text);
  border-radius: 2px;
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
}

.mobile-nav-link {
  padding: var(--space-md);
  font-size: 1rem;
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

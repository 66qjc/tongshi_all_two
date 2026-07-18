<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { getUnreadCount } from '@/api/announcement'
import { getNotificationUnreadCount, getNotifications, markNotificationRead, type StudentNotification } from '@/api/notification'
import { emitMessageRefresh, onMessageRefresh } from '@/utils/messageRefresh'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const scrolled = ref(false)
const mobileMenuOpen = ref(false)
const unreadCount = ref(0)
const recentNotifications = ref<StudentNotification[]>([])
const notificationDropdownOpen = ref(false)
let unreadTimer: number | undefined
let stopMessageRefresh: (() => void) | undefined

async function fetchUnreadCount() {
  if (!authStore.isLoggedIn || authStore.user?.role !== 'student') {
    unreadCount.value = 0
    recentNotifications.value = []
    notificationDropdownOpen.value = false
    return
  }
  try {
    const [announcementRes, notificationRes, recentRes] = await Promise.all([
      getUnreadCount(),
      getNotificationUnreadCount(),
      getNotifications({ unread_only: true }),
    ])
    unreadCount.value = announcementRes.count + notificationRes.count
    recentNotifications.value = recentRes.slice(0, 5)
  } catch {}
}

function closeNotificationDropdown() {
  notificationDropdownOpen.value = false
}

async function handleRecentNotification(item: StudentNotification) {
  try {
    if (!item.is_read) await markNotificationRead(item.id)
    closeNotificationDropdown()
    emitMessageRefresh()
    await router.push(item.action_url || '/student/notifications')
  } catch {
    ElMessage.error('通知标记已读失败，请稍后重试')
  }
}

function formatNotificationDate(dateStr?: string | null) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function getNotificationCategoryLabel(category?: string) {
  const labelMap: Record<string, string> = {
    assignment: '作业',
    grade: '成绩',
    course: '课程',
    project: '作品',
    system: '系统',
  }
  return labelMap[category || 'system'] || '通知'
}

const navItems = [
  { name: '深度学 · 积累知识', path: '/learn', icon: '&#9678;' },
  { name: '深度思 · 深化理解', path: '/practice', icon: '&#9632;' },
  { name: '深度践 · 动手创作', path: '/create', icon: '&#9733;' },
  { name: '深度悟 · 感悟价值', path: '/act', icon: '&#9830;' },
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
  unreadTimer = window.setInterval(fetchUnreadCount, 15000)
  stopMessageRefresh = onMessageRefresh(fetchUnreadCount)
})
onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  if (unreadTimer !== undefined) window.clearInterval(unreadTimer)
  stopMessageRefresh?.()
})

watch(
  () => route.fullPath,
  () => {
    fetchUnreadCount()
  },
)
</script>

<template>
  <header class="app-header" :class="{ scrolled }">
    <div class="header-inner container">
      <!-- Logo -->
      <router-link to="/" class="logo" @click="mobileMenuOpen = false">
        <span class="logo-icon">
          <img
            src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png"
            alt="中国计量大学 AI 通识课平台标识"
            width="38"
            height="38"
            class="logo-emblem"
          />
        </span>
        <span class="logo-text">
          <span class="logo-main">深度学思践悟</span>
          <span class="logo-sub">中国计量大学 · AI 通识课平台</span>
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
          <div
            v-if="authStore.user?.role === 'student'"
            class="notification-wrapper"
            @mouseenter="notificationDropdownOpen = true"
            @mouseleave="closeNotificationDropdown"
          >
            <router-link
              to="/student/notifications"
              class="notification-bell"
              aria-label="查看消息通知"
              @focus="notificationDropdownOpen = true"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                      stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
            </router-link>
            <div v-if="notificationDropdownOpen" class="notification-dropdown">
              <div class="notification-dropdown-header">
                <strong>最近通知</strong>
                <span v-if="unreadCount > 0">{{ unreadCount > 99 ? '99+' : unreadCount }} 条未读</span>
              </div>
              <div v-if="recentNotifications.length === 0" class="notification-empty">暂无新通知</div>
              <button
                v-for="item in recentNotifications"
                :key="item.id"
                type="button"
                class="notification-dropdown-item"
                @click="handleRecentNotification(item)"
              >
                <div class="notification-item-title">{{ item.title }}</div>
                <div class="notification-item-meta">
                  <span>{{ getNotificationCategoryLabel(item.category) }}</span>
                  <span>{{ formatNotificationDate(item.created_at) }}</span>
                </div>
              </button>
              <router-link
                to="/student/notifications"
                class="notification-dropdown-all"
                @click="closeNotificationDropdown"
              >
                查看全部
              </router-link>
            </div>
          </div>
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
  /* 初始：完全透明，滚动后过渡到磨砂白 */
  background: rgba(248, 245, 239, 0.72);
  backdrop-filter: blur(20px) saturate(170%);
  -webkit-backdrop-filter: blur(20px) saturate(170%);
  border-bottom: 1px solid transparent;
  transition:
    background var(--duration-normal) var(--ease-out),
    border-color var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out);
}

.app-header.scrolled {
  background: rgba(248, 245, 239, 0.96);
  border-bottom-color: var(--color-border-light);
  box-shadow: 0 1px 0 var(--color-border-light), var(--shadow-sm);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 62px;
}

/* ─── Logo ─── */
.logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  flex-shrink: 0;
}

.logo-icon {
  display: flex;
  align-items: center;
  transition: transform var(--duration-normal) var(--ease-spring);
}

.logo:hover .logo-icon {
  transform: scale(1.05);
}

.logo-emblem {
  display: block;
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.18;
}

.logo-main {
  font-family: var(--font-sans);
  font-size: 0.97rem;
  font-weight: 900;
  color: var(--color-text);
  letter-spacing: 0;
  text-wrap: balance;
}

.logo-sub {
  font-size: 0.6rem;
  color: var(--color-text-muted);
  font-weight: 600;
  letter-spacing: 0.01em;
}

/* ─── Desktop Nav ─── */
.nav-desktop {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-link {
  position: relative;
  padding: 0.42rem 0.85rem;
  font-size: 0.83rem;
  font-weight: 700;
  line-height: var(--leading-compact);
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  transition:
    color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.nav-link:hover {
  color: var(--color-primary);
  background: var(--color-primary-glow-hover);
}

.nav-link.active {
  color: var(--color-primary);
  background: var(--color-primary-glow);
  font-weight: 700;
}

/* 激活下划线：更精准居中 */
.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%);
  width: 18px;
  height: 2px;
  background: var(--color-primary);
  border-radius: 2px;
}

/* ─── Actions ─── */
.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-login {
  padding: 0.42rem 1.1rem;
  font-size: 0.84rem;
  font-weight: 600;
  color: #fffdf8;
  background: var(--color-primary);
  border-radius: var(--radius-md);
  box-shadow: 0 2px 8px rgba(45, 90, 110, 0.22);
  transition:
    background var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}

.btn-login:hover {
  background: var(--color-primary-light);
  transform: translateY(-1px);
  box-shadow: 0 5px 16px rgba(45, 90, 110, 0.28);
}

.btn-login:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(45, 90, 110, 0.18);
}

.user-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-text);
  padding: 0 4px;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-logout {
  padding: 0.33rem 0.82rem;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition:
    border-color var(--duration-fast),
    color var(--duration-fast),
    background var(--duration-fast);
}

.btn-logout:hover {
  border-color: #c0392b;
  color: #c0392b;
  background: rgba(192, 57, 43, 0.04);
}

.teacher-link {
  color: var(--color-primary) !important;
  font-weight: 700 !important;
}


.notification-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.notification-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 280px;
  padding: 10px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 248, 0.98);
  box-shadow: var(--shadow-lg);
  z-index: 1100;
}

.notification-dropdown::before {
  content: '';
  position: absolute;
  top: -10px;
  left: 0;
  right: 0;
  height: 10px;
}

.notification-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 2px 8px;
  font-size: 0.82rem;
  color: var(--color-text);
}

.notification-dropdown-header span {
  font-size: 0.72rem;
  color: var(--color-text-muted);
}

.notification-empty {
  padding: 18px 4px;
  text-align: center;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.notification-dropdown-item {
  display: block;
  width: 100%;
  padding: 9px 8px;
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition:
    background var(--duration-fast),
    color var(--duration-fast);
}

.notification-dropdown-item:hover {
  background: var(--color-primary-glow-hover);
  color: var(--color-primary);
}

.notification-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.82rem;
  font-weight: 700;
}

.notification-item-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
  font-size: 0.7rem;
  color: var(--color-text-muted);
}

.notification-dropdown-all {
  display: block;
  margin-top: 6px;
  padding: 8px;
  text-align: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--color-primary);
  border-radius: var(--radius-md);
  background: var(--color-primary-glow);
}

.notification-dropdown-all:hover {
  background: var(--color-primary-glow-hover);
}

.notification-bell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  transition:
    color var(--duration-fast),
    background var(--duration-fast);
}

.notification-bell:hover {
  color: var(--color-primary);
  background: var(--color-primary-glow-hover);
}

.badge {
  position: absolute;
  top: 3px;
  right: 1px;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  font-size: 0.58rem;
  font-weight: 700;
  color: white;
  background: #c0392b;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  /* 微妙白边，视觉上与图标分开 */
  box-shadow: 0 0 0 1.5px rgba(248, 245, 239, 0.9);
}

/* ─── Hamburger ─── */
.hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 32px;
  height: 32px;
  padding: 4px;
  border-radius: var(--radius-md);
  transition: background var(--duration-fast);
}

.hamburger:hover {
  background: var(--color-primary-glow);
}

.hamburger span {
  display: block;
  height: 1.5px;
  background: var(--color-text);
  border-radius: 1px;
  transition: all var(--duration-fast) var(--ease-out);
}

.hamburger.open span:nth-child(1) {
  transform: rotate(45deg) translateY(5px) translateX(3px);
}
.hamburger.open span:nth-child(2) {
  opacity: 0;
  transform: scaleX(0.5);
}
.hamburger.open span:nth-child(3) {
  transform: rotate(-45deg) translateY(-5px) translateX(3px);
}

/* ─── Mobile Nav ─── */
.mobile-nav {
  display: none;
  flex-direction: column;
  padding: var(--space-sm) var(--space-lg) var(--space-lg);
  gap: 2px;
  border-top: 1px solid var(--color-border-light);
  background: rgba(248, 245, 239, 0.98);
}

.mobile-nav-link {
  padding: 0.72rem var(--space-md);
  font-size: var(--text-body);
  font-weight: 600;
  line-height: var(--leading-compact);
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    background var(--duration-fast),
    color var(--duration-fast);
}

.mobile-nav-link:hover {
  background: var(--color-primary-glow-hover);
  color: var(--color-primary);
}

.mobile-cta {
  margin-top: var(--space-sm);
  text-align: center;
}

/* ─── 动画 ─── */
.slide-down-enter-active,
.slide-down-leave-active {
  transition:
    opacity var(--duration-normal) var(--ease-out),
    transform var(--duration-normal) var(--ease-out);
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-6px);
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

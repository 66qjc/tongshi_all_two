<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { name: '教师管理', path: '/admin/teachers', icon: '&#9783;' },
  { name: '内容管理', path: '/admin/showcase', icon: '&#128196;' },
]

function isActive(path: string) {
  return route.path === path
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="admin-layout">
    <header class="admin-header">
      <div class="header-left">
        <div class="logo-wrap">
          <svg viewBox="0 0 32 32" width="24" height="24">
            <defs>
              <linearGradient id="aLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color: var(--color-primary)" />
                <stop offset="100%" style="stop-color: var(--color-act)" />
              </linearGradient>
            </defs>
            <circle cx="16" cy="16" r="14" fill="url(#aLogoGrad)" />
            <text x="16" y="21" text-anchor="middle" font-size="13" font-weight="700"
                  fill="white" font-family="sans-serif">管</text>
          </svg>
          <span class="logo-text">AI通识课管理后台</span>
        </div>
      </div>
      <div class="header-right">
        <span class="admin-name">{{ authStore.user?.name || '管理员' }}</span>
        <button class="btn-logout" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <div class="admin-body">
      <aside class="admin-sidebar">
        <nav class="sidebar-nav">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="sidebar-link"
            :class="{ active: isActive(item.path) }"
          >
            <span class="sidebar-icon" v-html="item.icon"></span>
            {{ item.name }}
          </router-link>
        </nav>
      </aside>

      <main class="admin-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-layout {
  min-height: 100vh;
  background: var(--color-bg-alt);
}

.admin-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-xl);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
}

.header-left {
  display: flex;
  align-items: center;
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.logo-text {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.admin-name {
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
  cursor: pointer;
  background: transparent;
  transition: all var(--duration-fast);
}

.btn-logout:hover {
  border-color: #f56c6c;
  color: #f56c6c;
}

.admin-body {
  display: flex;
  padding-top: 56px;
  min-height: 100vh;
}

.admin-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  padding: var(--space-lg) 0;
  position: fixed;
  top: 56px;
  bottom: 0;
  left: 0;
  overflow-y: auto;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: 0 var(--space-sm);
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
  text-decoration: none;
}

.sidebar-link:hover {
  background: var(--color-primary-glow);
  color: var(--color-primary);
}

.sidebar-link.active {
  background: var(--color-primary-glow);
  color: var(--color-primary);
  font-weight: 600;
}

.sidebar-icon {
  font-size: 1rem;
  width: 20px;
  text-align: center;
}

.admin-main {
  flex: 1;
  margin-left: 200px;
  padding: var(--space-xl);
}

@media (max-width: 768px) {
  .admin-sidebar {
    width: 60px;
  }

  .sidebar-link {
    justify-content: center;
    padding: var(--space-sm);
  }

  .sidebar-link span:not(.sidebar-icon) {
    display: none;
  }

  .admin-main {
    margin-left: 60px;
  }

  .admin-name {
    display: none;
  }
}
</style>

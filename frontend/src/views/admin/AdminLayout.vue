<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { name: '教师管理', path: '/admin/teachers', icon: '&#9783;' },
  { name: '公共课程', path: '/admin/public-courses', icon: '&#9670;' },
  { name: '内容管理', path: '/admin/showcase', icon: '&#128196;' },
  { name: '密码重置', path: '/admin/password-reset', icon: '&#128273;' },
  { name: '数据回收站', path: '/admin/recycle-bin', icon: '&#9851;' },
  { name: '审计日志', path: '/admin/audit-logs', icon: '&#128220;' },
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
          <img
            src="/cjlu-xuesijianxing-favicon-sharp-20260606-190113.png"
            alt="AI 通识课平台标识"
            width="24"
            height="24"
            class="site-logo-icon"
          />
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
  font-family: var(--font-sans);
}

.admin-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-xl);
  background: rgba(255, 253, 248, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
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

.site-logo-icon {
  display: block;
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.logo-text {
  font-size: 1rem;
  font-weight: 700;
  font-family: var(--font-serif);
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
  border-radius: var(--radius-md);
  cursor: pointer;
  background: transparent;
  transition: all var(--duration-fast);
}

.btn-logout:hover {
  border-color: #c0392b;
  color: #c0392b;
}

.admin-body {
  display: flex;
  padding-top: 60px;
  min-height: 100vh;
}

.admin-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  padding: var(--space-lg) 0;
  position: fixed;
  top: 60px;
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
  border-left: 3px solid transparent;
  transition: all var(--duration-fast);
  text-decoration: none;
}

.sidebar-link:hover {
  color: var(--color-primary);
  border-left-color: var(--color-border);
}

.sidebar-link.active {
  color: #2d5a6e !important;
  font-weight: 600;
  border-left-color: #2d5a6e;
  background: rgba(45, 90, 110, 0.04);
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
  min-width: 0;
}

@media (max-width: 768px) {
  .admin-sidebar {
    width: 60px;
  }

  .sidebar-link {
    justify-content: center;
    padding: var(--space-sm);
    border-left: none;
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

@media (max-width: 480px) {
  .admin-header {
    padding: 0 var(--space-sm);
  }

  .admin-sidebar {
    width: 48px;
  }

  .sidebar-nav {
    padding: 0 4px;
  }

  .sidebar-link {
    padding: 8px 4px;
  }

  .admin-main {
    margin-left: 48px;
    padding: var(--space-sm);
    min-width: 0;
  }

  .logo-text {
    font-size: 0.9rem;
  }

  .btn-logout {
    padding: 0.35rem 0.6rem;
    font-size: 0.76rem;
  }
}
</style>

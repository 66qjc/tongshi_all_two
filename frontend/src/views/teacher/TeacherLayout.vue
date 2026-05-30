<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { name: '概述', path: '/teacher', icon: '&#9673;' },
  { name: '课程管理', path: '/teacher/courses', icon: '&#9670;' },
  { name: '班级管理', path: '/teacher/classes', icon: '&#9881;' },
  { name: '发布题目', path: '/teacher/publish', icon: '&#9993;' },
  { name: '学生成绩', path: '/teacher/grades', icon: '&#9783;' },
  { name: '作品审核', path: '/teacher/reviews', icon: '&#10003;' },
  { name: '资料管理', path: '/teacher/materials', icon: '&#9776;' },
  { name: '学生管理', path: '/teacher/student-admin', icon: '&#9782;' },
  { name: '题库管理', path: '/teacher/questions', icon: '&#9998;' },
]

function isActive(path: string) {
  return route.path === path
}
</script>

<template>
  <div class="teacher-layout">
    <header class="teacher-header">
      <div class="header-left">
        <router-link to="/" class="logo-link">
          <svg viewBox="0 0 32 32" width="24" height="24">
            <defs>
              <linearGradient id="tLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color: var(--color-primary)" />
                <stop offset="100%" style="stop-color: var(--color-learn)" />
              </linearGradient>
            </defs>
            <circle cx="16" cy="16" r="14" fill="url(#tLogoGrad)" />
            <text x="16" y="21" text-anchor="middle" font-size="13" font-weight="700" fill="white" font-family="sans-serif">师</text>
          </svg>
          <span class="logo-text">教师工作台</span>
        </router-link>
      </div>
      <div class="header-right">
        <span class="teacher-name">{{ authStore.user?.name || '教师' }}</span>
        <button class="btn-student-view" @click="router.push('/')">
          返回学生端
        </button>
      </div>
    </header>

    <div class="teacher-body">
      <aside class="teacher-sidebar">
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

      <main class="teacher-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.teacher-layout {
  min-height: 100vh;
  background: var(--color-bg-alt);
}

.teacher-header {
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

.logo-link {
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

.teacher-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
}

.btn-student-view {
  padding: 0.4rem 1rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.btn-student-view:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.teacher-body {
  display: flex;
  padding-top: 56px;
  min-height: 100vh;
}

.teacher-sidebar {
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

.teacher-main {
  flex: 1;
  margin-left: 200px;
  padding: var(--space-xl);
}

@media (max-width: 768px) {
  .teacher-sidebar {
    width: 60px;
  }

  .sidebar-link {
    justify-content: center;
    padding: var(--space-sm);
  }

  .sidebar-link span:not(.sidebar-icon) {
    display: none;
  }

  .teacher-main {
    margin-left: 60px;
  }

  .teacher-name {
    display: none;
  }
}
</style>

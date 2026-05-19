<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="not-found-page">
    <div class="container">
      <div class="not-found-content">
        <div class="error-code">404</div>
        <h1>页面未找到</h1>
        <p>你访问的页面不存在或已被移除</p>
        <div class="actions">
          <button class="btn-primary" @click="router.push('/')">返回首页</button>
          <button class="btn-secondary" @click="router.back()">返回上一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.not-found-page {
  padding-top: 64px;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.not-found-content {
  text-align: center;
  padding: var(--space-4xl) 0;
}

.error-code {
  font-size: clamp(4rem, 15vw, 8rem);
  font-weight: 900;
  color: var(--color-border);
  font-family: var(--font-mono);
  line-height: 1;
  margin-bottom: var(--space-md);
}

.not-found-content h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.not-found-content p {
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2xl);
}

.actions {
  display: flex;
  justify-content: center;
  gap: var(--space-md);
}

.btn-primary {
  padding: 0.7rem 1.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-secondary {
  padding: 0.7rem 1.5rem;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
}

.btn-secondary:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
</style>

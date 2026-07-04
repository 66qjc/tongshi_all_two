<script setup lang="ts">
import type { Lesson } from '@/api/lesson'

defineProps<{
  prevLesson: Lesson | null
  nextLesson: Lesson | null
}>()

const emit = defineEmits<{
  (e: 'prev'): void
  (e: 'next'): void
}>()
</script>

<template>
  <nav class="prev-next-nav">
    <button
      type="button"
      class="nav-card prev"
      :class="{ disabled: !prevLesson }"
      :disabled="!prevLesson"
      @click="emit('prev')"
    >
      <div class="nav-label">← 上一课</div>
      <div class="nav-title">{{ prevLesson?.title || '没有上一课' }}</div>
    </button>
    <button
      type="button"
      class="nav-card next"
      :class="{ disabled: !nextLesson }"
      :disabled="!nextLesson"
      @click="emit('next')"
    >
      <div class="nav-label">下一课 →</div>
      <div class="nav-title">{{ nextLesson?.title || '没有下一课' }}</div>
    </button>
  </nav>
</template>

<style scoped>
.prev-next-nav {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 48px;
  padding-top: 28px;
  border-top: 1px solid var(--color-border);
}

.nav-card {
  padding: 18px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition: border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out);
}

.nav-card:hover:not(.disabled) {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.nav-card.next {
  text-align: right;
}

.nav-card.disabled {
  opacity: 0.55;
  cursor: not-allowed;
  background: var(--color-bg-alt);
}

.nav-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.nav-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .prev-next-nav {
    grid-template-columns: 1fr;
  }

  .nav-card.next {
    text-align: left;
  }
}
</style>

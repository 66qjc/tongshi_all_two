<script setup lang="ts">
import type { Lesson } from '@/api/lesson'

defineProps<{
  lessons: Lesson[]
  activeLessonId?: number | null
}>()

const emit = defineEmits<{
  (e: 'select', lesson: Lesson): void
}>()
</script>

<template>
  <aside class="course-toc">
    <div class="toc-header">
      <div class="toc-title">课程目录</div>
    </div>
    <nav class="toc-list">
      <button
        v-for="(lesson, index) in lessons"
        :key="lesson.id"
        type="button"
        class="toc-item"
        :class="{ active: lesson.id === activeLessonId }"
        @click="emit('select', lesson)"
      >
        <span class="toc-num">{{ index + 1 }}</span>
        <span class="toc-text">{{ lesson.title }}</span>
      </button>
      <div v-if="!lessons.length" class="toc-empty">暂无课时</div>
    </nav>
  </aside>
</template>

<style scoped>
.course-toc {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.toc-header {
  padding: 20px 18px 12px;
  border-bottom: 1px solid var(--color-border-light);
  flex-shrink: 0;
}

.toc-title {
  font-size: 0.82rem;
  font-weight: 800;
  color: var(--color-text);
}

.toc-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.toc-item {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 10px;
  padding: 10px;
  margin-bottom: 4px;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  text-align: left;
  transition: background 160ms var(--ease-out), border-color 160ms var(--ease-out), color 160ms var(--ease-out);
}

.toc-item:hover {
  background: var(--color-border-light);
  color: var(--color-text);
}

.toc-item.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-color: rgba(45, 106, 122, 0.24);
  font-weight: 700;
}

.toc-num {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-border-light);
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
  color: var(--color-text-muted);
}

.toc-item.active .toc-num {
  background: var(--color-primary);
  color: var(--color-bg-card);
}

.toc-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toc-empty {
  padding: 24px 18px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}
</style>

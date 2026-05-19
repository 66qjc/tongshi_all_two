<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  src?: string
  title?: string
}>()

const currentPage = ref(1)
const totalPages = ref(1)
const scale = ref(1)

const canPrev = computed(() => currentPage.value > 1)
const canNext = computed(() => currentPage.value < totalPages.value)

function prevPage() {
  if (canPrev.value) currentPage.value--
}

function nextPage() {
  if (canNext.value) currentPage.value++
}

function zoomIn() {
  if (scale.value < 2) scale.value = Math.round((scale.value + 0.25) * 100) / 100
}

function zoomOut() {
  if (scale.value > 0.5) scale.value = Math.round((scale.value - 0.25) * 100) / 100
}

function fitWidth() {
  scale.value = 1
}
</script>

<template>
  <div class="pdf-viewer">
    <template v-if="src">
      <!-- PDF content area -->
      <div class="pdf-content">
        <iframe :src="src" class="pdf-iframe" title="PDF document" />
      </div>

      <!-- Controls -->
      <div class="pdf-controls">
        <div class="page-controls">
          <button class="ctrl-btn" :disabled="!canPrev" @click="prevPage">
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <span class="page-info">第 {{ currentPage }} / {{ totalPages }} 页</span>
          <button class="ctrl-btn" :disabled="!canNext" @click="nextPage">
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M4 10h12m-4-4l4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>

        <div class="zoom-controls">
          <button class="ctrl-btn" @click="zoomOut">−</button>
          <span class="zoom-info">{{ Math.round(scale * 100) }}%</span>
          <button class="ctrl-btn" @click="zoomIn">+</button>
          <button class="ctrl-btn fit-btn" @click="fitWidth">适配</button>
        </div>
      </div>
    </template>

    <div v-else class="placeholder">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
        <path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <p>教师暂未上传文档</p>
    </div>
  </div>
</template>

<style scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 500px;
  background: var(--color-bg-alt);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.pdf-content {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-md);
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: var(--radius-sm);
}

.pdf-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-border);
}

.page-controls,
.zoom-controls {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.ctrl-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
}

.ctrl-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.ctrl-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.fit-btn {
  width: auto;
  padding: 0 var(--space-sm);
  font-size: 0.75rem;
}

.page-info,
.zoom-info {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  min-width: 80px;
  text-align: center;
}

.placeholder {
  width: 100%;
  height: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  color: var(--color-text-muted);
}

.placeholder p {
  font-size: 0.9rem;
}
</style>

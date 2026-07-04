<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'
import type { Lesson } from '@/api/lesson'
import { resolveFileUrl } from '@/utils/url'
import MaterialRichCard from '@/components/common/MaterialRichCard.vue'

const props = defineProps<{
  lesson: Lesson | null
  materials: Material[]
  fileUrlResolver?: (material: Material) => string
}>()

const emit = defineEmits<{
  (e: 'preview', material: Material): void
}>()

type Segment =
  | { type: 'html'; html: string }
  | { type: 'material'; materialId: number; materialType: 'video' | 'pdf'; material?: Material }

const materialMap = computed(() => {
  const map = new Map<number, Material>()
  props.materials.forEach((material) => map.set(material.id, material))
  return map
})

const segments = computed<Segment[]>(() => {
  const result: Segment[] = []
  const content = props.lesson?.content || ''
  const regex = /<div\b(?=[^>]*class=["'][^"']*\blesson-material\b[^"']*["'])(?=[^>]*data-material-id=["'](\d+)["'])(?=[^>]*data-material-type=["'](video|pdf)["'])[^>]*>(?:<\/div>)?/gi
  let lastIndex = 0
  let match: RegExpExecArray | null = null
  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      result.push({ type: 'html', html: content.slice(lastIndex, match.index) })
    }
    result.push({
      type: 'material',
      materialId: Number(match[1]),
      materialType: match[2] as 'video' | 'pdf',
      material: materialMap.value.get(Number(match[1])),
    })
    lastIndex = regex.lastIndex
  }
  if (lastIndex < content.length) {
    result.push({ type: 'html', html: content.slice(lastIndex) })
  }
  return result
})

function materialFileUrl(material: Material): string {
  if (props.fileUrlResolver) return resolveFileUrl(props.fileUrlResolver(material))
  if (material.file_id) return resolveFileUrl(`/api/files/${material.file_id}`)
  return resolveFileUrl(material.url)
}
</script>

<template>
  <article class="lesson-reader">
    <header v-if="lesson" class="lesson-header">
      <div class="lesson-meta">
        <span class="lesson-tag">课时</span>
        <span class="lesson-updated">更新于 {{ lesson.updated_at?.slice(0, 10) || '-' }}</span>
      </div>
      <h1 class="lesson-title">{{ lesson.title }}</h1>
    </header>

    <div v-if="!lesson" class="lesson-empty">请从左侧目录选择课时开始学习。</div>

    <div v-else class="lesson-body">
      <template v-for="(segment, index) in segments" :key="index">
        <div v-if="segment.type === 'html'" class="lesson-html" v-html="segment.html" />
        <div v-else-if="segment.type === 'material'" class="lesson-material-embed">
          <template v-if="segment.material">
            <div v-if="segment.materialType === 'video'" class="video-wrapper">
              <video
                class="lesson-video"
                :src="materialFileUrl(segment.material)"
                controls
                preload="metadata"
              />
            </div>
            <MaterialRichCard
              v-else-if="segment.materialType === 'pdf'"
              :material="segment.material"
              @preview="emit('preview', $event)"
            />
          </template>
          <div v-else class="material-missing">
            <span class="missing-icon">!</span>
            <span>资料已失效或不可用。</span>
          </div>
        </div>
      </template>
      <div v-if="!segments.length" class="lesson-empty">本课时暂无内容。</div>
    </div>
  </article>
</template>

<style scoped>
.lesson-reader {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  padding: 48px 56px;
}

.lesson-header {
  margin-bottom: 36px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--color-border-light);
}

.lesson-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.lesson-tag {
  padding: 4px 10px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-full);
  font-weight: 600;
}

.lesson-title {
  font-size: 1.9rem;
  font-weight: 800;
  color: var(--color-text);
  line-height: 1.3;
  letter-spacing: 0;
  margin: 0;
}

.lesson-body {
  font-size: 1rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.lesson-body :deep(h2) {
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 40px 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border-light);
}

.lesson-body :deep(h3) {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 28px 0 12px;
}

.lesson-body :deep(p) {
  margin-bottom: 16px;
}

.lesson-body :deep(ul),
.lesson-body :deep(ol) {
  margin: 16px 0;
  padding-left: 24px;
}

.lesson-body :deep(li) {
  margin-bottom: 8px;
}

.lesson-body :deep(img) {
  width: 100%;
  border-radius: var(--radius-md);
  margin: 24px 0;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-border);
}

.lesson-body :deep(blockquote) {
  margin: 24px 0;
  padding: 16px 20px;
  border: 1px solid rgba(45, 106, 122, 0.2);
  background: var(--color-primary-light);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  font-style: italic;
}

.lesson-body :deep(code) {
  font-family: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace;
  background: var(--color-border-light);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  color: var(--color-text);
}

.lesson-body :deep(pre) {
  background: rgb(31, 41, 55);
  color: rgb(243, 244, 246);
  padding: 20px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin: 20px 0;
  font-size: 0.9rem;
}

.lesson-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.lesson-material-embed {
  margin: 24px 0;
}

.video-wrapper {
  width: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: rgb(12, 18, 24);
  box-shadow: var(--shadow-md);
}

.lesson-video {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: block;
}

.material-missing {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  background: var(--color-bg-alt);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.missing-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-warning-light, var(--color-border-light));
  color: var(--color-warning, var(--color-text-muted));
  font-weight: 800;
}

.lesson-empty {
  text-align: center;
  padding: 64px 0;
  color: var(--color-text-muted);
  font-size: 0.95rem;
}

@media (max-width: 900px) {
  .lesson-reader {
    padding: 28px 20px;
  }

  .lesson-title {
    font-size: 1.5rem;
  }
}
</style>

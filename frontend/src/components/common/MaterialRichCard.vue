<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'
import AuthenticatedFileImage from '@/components/common/AuthenticatedFileImage.vue'

const props = withDefaults(defineProps<{
  material: Material
  manage?: boolean
  /** 扁平紧凑模式：小封面 + 多行摘要，适合教师端阶段资料列表 */
  compact?: boolean
}>(), {
  manage: false,
  compact: false,
})

const emit = defineEmits<{
  (e: 'preview', material: Material): void
  (e: 'edit', material: Material): void
  (e: 'delete', material: Material): void
  (e: 'rebuild', material: Material): void
}>()

const typeLabel = computed(() => {
  if (props.material.type === 'video') return '视频'
  if (props.material.type === 'pdf') return 'PDF'
  return '链接'
})

const summaryText = computed(() => {
  const raw = props.material.preview?.summary || '暂无资料摘要，可在新窗口打开文件查看。'
  if (!props.compact) return raw
  // 紧凑模式展示更完整摘要：约 3 行可见，仍截断超长正文避免整页被撑爆
  const maxLen = 180
  const normalized = raw.replace(/\s+/g, ' ').trim()
  return normalized.length > maxLen ? `${normalized.slice(0, maxLen)}…` : normalized
})

const metaText = computed(() => {
  const parts = [props.material.size]
  if (props.material.type === 'pdf' && props.material.preview?.page_count) {
    parts.push(`${props.material.preview.page_count} 页`)
  }
  if (props.material.type === 'video' && props.material.preview?.duration_seconds) {
    const minutes = Math.max(1, Math.round(props.material.preview.duration_seconds / 60))
    parts.push(`${minutes} 分钟`)
  }
  if (props.material.preview?.resolution) parts.push(props.material.preview.resolution)
  if (props.material.date) parts.push(props.material.date)
  return parts.filter(Boolean).join(' · ')
})

const statusText = computed(() => {
  const status = props.material.preview?.status
  if (status === 'ready') return '预览就绪'
  if (status === 'processing') return '预览生成中'
  if (status === 'failed') return '预览生成失败'
  return '可打开原文件'
})
</script>

<template>
  <article class="material-rich-card" :class="{ compact }">
    <div class="cover">
      <AuthenticatedFileImage
        v-if="material.preview?.cover_file_id"
        :file-id="material.preview?.cover_file_id"
        :alt="material.title"
      />
      <span v-else class="cover-fallback">{{ typeLabel }}</span>
    </div>
    <div class="body">
      <div class="main-line">
        <div class="title-block">
          <div class="title-row">
            <el-tag size="small" effect="plain">{{ typeLabel }}</el-tag>
            <el-tag size="small" :type="material.preview?.status === 'failed' ? 'danger' : 'info'" effect="plain">
              {{ statusText }}
            </el-tag>
          </div>
          <h3 :title="material.title">{{ material.title }}</h3>
          <p class="summary" :title="material.preview?.summary || summaryText">{{ summaryText }}</p>
          <p class="meta">{{ metaText }}</p>
          <p v-if="material.preview?.status === 'failed' && material.preview.error_message" class="error">
            {{ material.preview.error_message }}
          </p>
        </div>
        <div class="actions">
          <el-button type="primary" size="small" @click="emit('preview', material)">预览</el-button>
          <template v-if="manage">
            <el-button size="small" @click="emit('edit', material)">编辑</el-button>
            <el-button size="small" @click="emit('rebuild', material)">重建预览</el-button>
            <el-button type="danger" text size="small" @click="emit('delete', material)">删除</el-button>
          </template>
        </div>
      </div>
    </div>
  </article>
</template>

<style scoped>
.material-rich-card {
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
}

.cover {
  aspect-ratio: 4 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--color-bg-alt);
  color: var(--color-text-muted);
  font-weight: 700;
}

.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-fallback {
  font-size: 0.85rem;
}

.body {
  min-width: 0;
}

.main-line {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.title-block {
  min-width: 0;
}

.title-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

h3 {
  margin: 0 0 8px;
  font-size: 1rem;
  color: var(--color-text);
}

.summary {
  margin: 0 0 8px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.meta,
.error {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.error {
  color: var(--color-danger);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 扁平紧凑：横排封面 + 多行摘要，教师端阶段资料可读性优先 */
.material-rich-card.compact {
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 14px;
  padding: 12px 14px;
  align-items: flex-start;
}

.material-rich-card.compact .cover {
  width: 96px;
  height: 72px;
  aspect-ratio: auto;
  flex-shrink: 0;
  margin-top: 2px;
}

.material-rich-card.compact .main-line {
  flex-direction: row;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.material-rich-card.compact .title-row {
  margin-bottom: 4px;
}

.material-rich-card.compact h3 {
  margin: 0 0 4px;
  font-size: 0.98rem;
  font-weight: 700;
  line-height: 1.4;
  white-space: normal;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.material-rich-card.compact .summary {
  margin: 0 0 6px;
  font-size: 0.84rem;
  line-height: 1.55;
  white-space: normal;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  color: var(--color-text-secondary);
}

.material-rich-card.compact .meta {
  margin: 0;
  font-size: 0.78rem;
}

.material-rich-card.compact .error {
  margin: 4px 0 0;
  font-size: 0.78rem;
  white-space: normal;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.material-rich-card.compact .actions {
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  max-width: 220px;
  padding-top: 2px;
}

@media (max-width: 900px) {
  .material-rich-card.compact .main-line {
    flex-direction: column;
    align-items: stretch;
  }

  .material-rich-card.compact .actions {
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .material-rich-card {
    grid-template-columns: 1fr;
  }

  .material-rich-card.compact {
    grid-template-columns: 72px minmax(0, 1fr);
  }

  .material-rich-card.compact .cover {
    width: 72px;
    height: 54px;
  }
}
</style>

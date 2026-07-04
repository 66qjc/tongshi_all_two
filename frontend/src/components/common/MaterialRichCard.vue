<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'
import { resolveFileUrl } from '@/utils/url'

const props = defineProps<{
  material: Material
  manage?: boolean
}>()

const emit = defineEmits<{
  (e: 'preview', material: Material): void
  (e: 'edit', material: Material): void
  (e: 'delete', material: Material): void
  (e: 'rebuild', material: Material): void
}>()

const coverUrl = computed(() => {
  const fileId = props.material.preview?.cover_file_id
  return fileId ? resolveFileUrl(`/api/files/${fileId}`) : ''
})

const typeLabel = computed(() => {
  if (props.material.type === 'video') return '视频'
  if (props.material.type === 'pdf') return 'PDF'
  return '链接'
})

const summaryText = computed(() => {
  return props.material.preview?.summary || '暂无资料摘要，可在新窗口打开文件查看。'
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
  <article class="material-rich-card">
    <div class="cover">
      <img v-if="coverUrl" :src="coverUrl" :alt="material.title" />
      <span v-else>{{ typeLabel }}</span>
    </div>
    <div class="body">
      <div class="title-row">
        <el-tag size="small" effect="plain">{{ typeLabel }}</el-tag>
        <el-tag size="small" :type="material.preview?.status === 'failed' ? 'danger' : 'info'" effect="plain">
          {{ statusText }}
        </el-tag>
      </div>
      <h3>{{ material.title }}</h3>
      <p class="summary">{{ summaryText }}</p>
      <p class="meta">{{ metaText }}</p>
      <p v-if="material.preview?.status === 'failed' && material.preview.error_message" class="error">
        {{ material.preview.error_message }}
      </p>
      <div class="actions">
        <el-button type="primary" size="small" @click="emit('preview', material)">预览</el-button>
        <template v-if="manage">
          <el-button size="small" @click="emit('edit', material)">编辑</el-button>
          <el-button size="small" @click="emit('rebuild', material)">重建预览</el-button>
          <el-button type="danger" text size="small" @click="emit('delete', material)">删除</el-button>
        </template>
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

.body {
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

@media (max-width: 640px) {
  .material-rich-card {
    grid-template-columns: 1fr;
  }
}
</style>

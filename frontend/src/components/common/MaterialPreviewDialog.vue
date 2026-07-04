<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'
import { getMaterialFileUrl } from '@/api/material'
import { resolveFileUrl } from '@/utils/url'

const props = defineProps<{
  visible: boolean
  material: Material | null
  // 游客阅读公开课程时优先使用外部传入的公开资料预览 URL。
  previewUrl?: string
}>()

const emit = defineEmits<{ (e: 'update:visible', val: boolean): void }>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

const resolvedPreviewUrl = computed(() => {
  if (props.previewUrl) return resolveFileUrl(props.previewUrl)
  if (!props.material) return ''
  return resolveFileUrl(getMaterialFileUrl(props.material.id))
})

const isVideo = computed(() => props.material?.type === 'video')
const isPdf = computed(() => props.material?.type === 'pdf')

function openInNewWindow() {
  if (resolvedPreviewUrl.value) window.open(resolvedPreviewUrl.value, '_blank', 'noopener')
}
</script>

<template>
  <el-dialog v-model="dialogVisible" title="资料预览" width="80%" destroy-on-close>
    <div v-if="material && resolvedPreviewUrl" class="material-preview-dialog">
      <video v-if="isVideo" class="preview-video" :src="resolvedPreviewUrl" controls preload="metadata" />
      <object v-else-if="isPdf" class="preview-pdf" :data="resolvedPreviewUrl" type="application/pdf">
        <div class="preview-fallback">浏览器无法直接预览 PDF，请在新窗口打开。</div>
      </object>
      <div v-else class="preview-fallback">该资料类型暂不支持站内预览。</div>
    </div>
    <div v-else class="preview-fallback">暂无可预览文件。</div>
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
      <el-button type="primary" :disabled="!resolvedPreviewUrl" @click="openInNewWindow">在新窗口打开</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.material-preview-dialog {
  min-height: 60vh;
}

.preview-video,
.preview-pdf {
  width: 100%;
  height: 68vh;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-alt);
}

.preview-fallback {
  padding: 48px 0;
  text-align: center;
  color: var(--color-text-muted);
}
</style>

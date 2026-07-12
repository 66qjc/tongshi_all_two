<script setup lang="ts">
import { computed } from 'vue'
import type { Material } from '@/api/material'
import { useAuthenticatedFileUrl } from '@/composables/useAuthenticatedFileUrl'

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

function resolvePreviewSource() {
  if (!props.material) return ''
  if (props.previewUrl) return props.previewUrl
  if (props.material.file_id) return `/api/files/${props.material.file_id}`
  if (props.material.url) return props.material.url
  return ''
}

const previewSourceUrl = computed(resolvePreviewSource)

const previewEnabled = computed(() => Boolean(props.visible && props.material && previewSourceUrl.value))
const {
  resolvedUrl,
  loading: previewLoading,
  error: previewError,
  retryOnce,
} = useAuthenticatedFileUrl(
  previewSourceUrl,
  { enabled: previewEnabled },
)

const isVideo = computed(() => props.material?.type === 'video')
const isPdf = computed(() => props.material?.type === 'pdf')

function handlePreviewError(event: Event) {
  const target = event.currentTarget
  const failedUrl = target instanceof HTMLVideoElement
    ? target.getAttribute('src') || ''
    : target instanceof HTMLObjectElement
      ? target.getAttribute('data') || ''
      : ''
  void retryOnce(failedUrl)
}

function openInNewWindow() {
  if (resolvedUrl.value) window.open(resolvedUrl.value, '_blank', 'noopener')
}
</script>

<template>
  <el-dialog v-model="dialogVisible" title="资料预览" width="80%" destroy-on-close>
    <div v-if="material && previewSourceUrl" class="material-preview-dialog">
      <div v-if="previewLoading" class="preview-fallback">文件加载中，请稍候。</div>
      <div v-else-if="previewError" class="preview-fallback">{{ previewError }}</div>
      <video v-else-if="isVideo && resolvedUrl" :key="resolvedUrl" class="preview-video" :src="resolvedUrl" controls preload="metadata" @error="handlePreviewError" />
      <object v-else-if="isPdf && resolvedUrl" :key="resolvedUrl" class="preview-pdf" :data="resolvedUrl" type="application/pdf" @error="handlePreviewError">
        <div class="preview-fallback">浏览器无法直接预览 PDF，请在新窗口打开。</div>
      </object>
      <div v-else class="preview-fallback">该资料类型暂不支持站内预览。</div>
    </div>
    <div v-else class="preview-fallback">暂无可预览文件。</div>
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
      <el-button type="primary" :disabled="!resolvedUrl" @click="openInNewWindow">在新窗口打开</el-button>
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

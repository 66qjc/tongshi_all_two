<script setup lang="ts">
import { computed } from 'vue'
import { useAuthenticatedFileUrl } from '@/composables/useAuthenticatedFileUrl'

const props = defineProps<{
  visible: boolean
  title?: string
  url?: string
  fileId?: number
}>()

const emit = defineEmits<{ (e: 'update:visible', val: boolean): void }>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

const sourceUrl = computed(() => props.fileId ? `/api/files/${props.fileId}` : props.url || '')
const enabled = computed(() => props.visible && Boolean(sourceUrl.value))
const { resolvedUrl, loading, error } = useAuthenticatedFileUrl(sourceUrl, { enabled })

function openInNewWindow() {
  if (resolvedUrl.value) window.open(resolvedUrl.value, '_blank', 'noopener')
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title || '资料预览'"
    width="520px"
    destroy-on-close
  >
    <div v-if="sourceUrl" class="preview-card">
      <p class="preview-title">文件已准备好</p>
      <p v-if="loading && !resolvedUrl" class="preview-desc">正在获取文件访问地址，请稍候。</p>
      <p v-else-if="error && !resolvedUrl" class="preview-desc">{{ error }}</p>
      <p v-else class="preview-desc">请在新窗口打开资料。若浏览器无法直接预览，可在新窗口中下载后查看。</p>
      <el-button type="primary" :disabled="!resolvedUrl" @click="openInNewWindow">在新窗口打开</el-button>
    </div>
    <div v-else class="preview-empty">暂无可预览文件。</div>
    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.preview-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 16px;
  text-align: center;
  background: var(--color-bg-alt);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.preview-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
}

.preview-desc {
  max-width: 360px;
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.preview-empty {
  text-align: center;
  padding: 40px 0;
  color: #999;
}
</style>

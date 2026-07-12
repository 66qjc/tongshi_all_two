<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import VuePdfEmbed, { GlobalWorkerOptions } from 'vue-pdf-embed/dist/index.essential.mjs'
// vue-pdf-embed 内部使用的是 pdfjs-dist 的 legacy 构建，worker 必须同样使用 legacy 版本，
// 否则主程序与 worker 构建不匹配，会导致 PDF 在浏览器里无法打开或一直卡在渲染中。
import PdfWorker from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'
import type { Material } from '@/api/material'

GlobalWorkerOptions.workerSrc = PdfWorker

const props = defineProps<{
  material: Material | null
  fileUrl: string
  fileLoading?: boolean
  fileError?: string
}>()

const emit = defineEmits<{
  (e: 'file-error', failedUrl: string): void
}>()

const type = computed(() => props.material?.type)
const pdfStatus = ref<'loading' | 'ready' | 'error'>('loading')
const pdfErrorText = ref('')
const pdfPageTotal = ref(0)
const visiblePdfPageCount = ref(2)

const metaText = computed(() => {
  if (!props.material) return ''
  const parts: string[] = []
  if (props.material.type === 'pdf' && props.material.preview?.page_count) {
    parts.push(`${props.material.preview.page_count} 页`)
  } else if (props.material.type === 'pdf' && props.material.pages) {
    parts.push(`${props.material.pages} 页`)
  }
  if (props.material.type === 'video' && props.material.preview?.duration_seconds) {
    const minutes = Math.max(1, Math.round(props.material.preview.duration_seconds / 60))
    parts.push(`${minutes} 分钟`)
  } else if (props.material.type === 'video' && props.material.duration) {
    parts.push(props.material.duration)
  }
  if (props.material.size) parts.push(props.material.size)
  if (props.material.date) parts.push(props.material.date)
  return parts.join(' · ')
})

const summaryText = computed(() => {
  if (!props.material) return ''
  if (props.material.preview?.summary) return props.material.preview.summary
  if (props.material.type === 'link') return '该资料为外部学习链接，请在新窗口打开阅读。'
  return '暂无资料摘要，可先阅读正文内容，再结合课程任务完成学习记录。'
})

const pdfPagesToRender = computed(() => {
  const total = pdfPageTotal.value || visiblePdfPageCount.value
  const count = Math.max(1, Math.min(visiblePdfPageCount.value, total))
  return Array.from({ length: count }, (_, index) => index + 1)
})

const hasMorePdfPages = computed(
  () =>
    props.material?.type === 'pdf' &&
    props.fileUrl &&
    pdfStatus.value !== 'error' &&
    (pdfPageTotal.value === 0 || visiblePdfPageCount.value < pdfPageTotal.value),
)

const pdfFailureHandler = computed(() => {
  const failedUrl = props.fileUrl
  return (error: unknown) => handlePdfFailed(error, failedUrl)
})

watch(
  () => [props.material?.id, props.material?.type, props.fileUrl],
  () => {
    pdfErrorText.value = ''
    pdfPageTotal.value = 0
    visiblePdfPageCount.value = 2
    pdfStatus.value = props.material?.type === 'pdf' && props.fileUrl ? 'loading' : 'ready'
  },
  { immediate: true },
)

function describePdfError(error: unknown) {
  if (error instanceof Error && error.message) return error.message
  return '当前 PDF 暂时无法渲染。'
}

function handlePdfLoaded(doc: { numPages?: number }) {
  pdfErrorText.value = ''
  pdfPageTotal.value = doc.numPages || 0
  pdfStatus.value = 'loading'
}

function handlePdfRendered() {
  pdfErrorText.value = ''
  pdfStatus.value = 'ready'
}

function handlePdfFailed(error: unknown, failedUrl: string) {
  if (!failedUrl || failedUrl !== props.fileUrl) return
  pdfErrorText.value = describePdfError(error)
  pdfStatus.value = 'error'
  emitFileError(failedUrl)
}

function handleVideoError(event: Event) {
  const video = event.currentTarget as HTMLVideoElement | null
  emitFileError(video?.getAttribute('src') || '')
}

function emitFileError(failedUrl: string) {
  if (!failedUrl) return
  emit('file-error', failedUrl)
}

function loadMorePdfPages() {
  const nextPageCount = visiblePdfPageCount.value + 2
  visiblePdfPageCount.value = pdfPageTotal.value
    ? Math.min(pdfPageTotal.value, nextPageCount)
    : nextPageCount
  pdfStatus.value = 'loading'
}
</script>

<template>
  <article class="material-inline-reader">
    <div v-if="!material" class="reader-empty">
      <h2>暂无可阅读资料</h2>
      <p>当前课程还没有配置 PDF、视频或链接资料。</p>
    </div>

    <template v-else>
      <header class="reader-head">
        <p class="reader-kicker">
          {{ type === 'pdf' ? 'PDF 资料' : type === 'video' ? '视频资料' : '外部链接' }}
        </p>
        <h2>{{ material.title }}</h2>
        <p v-if="metaText" class="reader-meta">{{ metaText }}</p>
        <p v-if="summaryText" class="reader-summary">{{ summaryText }}</p>
      </header>

      <section v-if="type === 'pdf'" class="reader-frame pdf-frame">
        <div class="pdf-document">
          <div v-if="fileLoading || pdfStatus === 'loading'" class="pdf-status">PDF 渲染中，请稍候。</div>
          <div v-if="fileError" class="reader-fallback pdf-error">
            <h3>浏览器无法直接显示 PDF</h3>
            <p>{{ fileError || pdfErrorText || '可以使用下方按钮在新窗口打开原资料。' }}</p>
            <a v-if="fileUrl" :href="fileUrl" target="_blank" rel="noopener" class="open-link">打开原资料</a>
          </div>
          <VuePdfEmbed
            v-if="fileUrl && !fileError && pdfStatus !== 'error'"
            :key="fileUrl"
            :source="fileUrl"
            :page="pdfPagesToRender"
            class="pdf-embed"
            @loaded="handlePdfLoaded"
            @rendered="handlePdfRendered"
            @loading-failed="pdfFailureHandler"
            @rendering-failed="pdfFailureHandler"
          />
          <object
            v-else-if="fileUrl && !fileError && pdfStatus === 'error'"
            :key="`fallback-${fileUrl}`"
            :data="fileUrl"
            type="application/pdf"
            class="pdf-object-fallback"
            aria-label="PDF 备用预览"
          >
            <div class="reader-fallback">
              <h3>浏览器无法直接显示 PDF</h3>
              <p>{{ pdfErrorText || '可以使用下方按钮在新窗口打开原资料。' }}</p>
              <a :href="fileUrl" target="_blank" rel="noopener" class="open-link">打开原资料</a>
            </div>
          </object>
          <button
            v-if="hasMorePdfPages"
            type="button"
            class="pdf-more-button"
            @click="loadMorePdfPages"
          >
            加载更多页面
          </button>
        </div>
        <div class="pdf-open-row">
          <span>浏览器无法直接显示 PDF 时，可以在新窗口打开原资料。</span>
          <a v-if="fileUrl" :href="fileUrl" target="_blank" rel="noopener" class="open-link">打开原资料</a>
        </div>
      </section>

      <section v-else-if="type === 'video'" class="reader-frame video-frame">
        <div v-if="fileLoading" class="reader-fallback">视频加载中，请稍候。</div>
        <div v-else-if="fileError" class="reader-fallback">视频加载失败，请刷新后重试。</div>
        <video v-else :key="fileUrl" :src="fileUrl" controls preload="metadata" class="video-player" @error="handleVideoError" />
      </section>

      <section v-else class="reader-frame link-frame">
        <div class="link-panel">
          <h3>{{ material.title }}</h3>
          <p>{{ summaryText }}</p>
          <a :href="fileUrl" target="_blank" rel="noopener" class="open-link">
            打开原资料
          </a>
        </div>
      </section>
    </template>
  </article>
</template>

<style scoped>
.material-inline-reader {
  min-width: 0;
}

.reader-head {
  padding: 22px 26px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.reader-kicker {
  margin: 0 0 6px;
  color: var(--color-learn);
  font-size: 0.78rem;
  font-weight: 900;
}

.reader-head h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 1.35rem;
  line-height: var(--leading-title);
  font-weight: 900;
  text-wrap: balance;
}

.reader-meta {
  margin: 8px 0 0;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.reader-summary {
  margin: 12px 0 0;
  max-width: 72ch;
  color: var(--color-text-secondary);
  line-height: 1.7;
  text-wrap: pretty;
}

.reader-frame {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-top: 0;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.pdf-frame {
  min-height: 74vh;
  padding: 20px;
  background: var(--color-bg-alt);
}

.pdf-document {
  display: grid;
  justify-items: center;
  gap: 18px;
}

.pdf-embed {
  width: min(100%, 880px);
}

.pdf-embed :deep(canvas),
.pdf-embed :deep(.vue-pdf-embed__page) {
  max-width: 100%;
}

.pdf-embed :deep(canvas) {
  display: block;
  height: auto !important;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.12);
}

.pdf-status {
  color: var(--color-text-secondary);
  font-weight: 700;
  text-align: center;
}

.pdf-more-button {
  justify-self: center;
  padding: 10px 18px;
  color: var(--color-learn);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-weight: 800;
}

.pdf-more-button:hover {
  border-color: rgba(45, 106, 122, 0.38);
  background: rgba(45, 106, 122, 0.08);
}

.pdf-object-fallback {
  width: min(100%, 880px);
  min-height: 70vh;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
}

.video-player {
  display: block;
  width: 100%;
  min-height: 74vh;
  border: 0;
  background: var(--color-bg-alt);
}

.video-player {
  height: auto;
  min-height: 420px;
}

.pdf-open-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
  padding: 12px 14px;
  color: var(--color-text-secondary);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.link-frame,
.reader-empty {
  padding: 42px;
}

.link-panel,
.reader-empty {
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.link-panel h3,
.reader-empty h2,
.reader-fallback h3 {
  margin: 0 0 10px;
  color: var(--color-text);
  font-size: 1.1rem;
}

.reader-fallback {
  display: grid;
  place-items: center;
  min-height: 360px;
  padding: 32px;
  color: var(--color-text-secondary);
  text-align: center;
}

.open-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 12px;
  padding: 9px 14px;
  color: var(--color-bg-card);
  background: var(--color-learn);
  border-radius: var(--radius-sm);
  font-weight: 800;
}

@media (max-width: 900px) {
  .reader-head {
    padding: 18px;
  }

  .reader-head h2 {
    font-size: 1.12rem;
  }

  .pdf-frame,
  .video-player {
    min-height: 70vh;
  }

  .pdf-frame {
    padding: 12px;
  }

  .pdf-open-row {
    display: grid;
  }

  .link-frame,
  .reader-empty {
    padding: 24px;
  }
}
</style>

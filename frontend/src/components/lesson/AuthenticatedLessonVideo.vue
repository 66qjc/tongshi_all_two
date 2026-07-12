<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useAuthenticatedFileUrl } from '@/composables/useAuthenticatedFileUrl'

const props = withDefaults(defineProps<{
  sourceUrl: string
  resumePosition?: number
}>(), {
  resumePosition: 0,
})

const emit = defineEmits<{
  (e: 'video-progress', payload: { currentTime: number; duration: number; ended: boolean }): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const source = computed(() => props.sourceUrl)
const enabled = computed(() => Boolean(props.sourceUrl))
const beforeUrlRenewalPosition = ref(0)
const mediaFailed = ref(false)
let lastResolvedSource = props.sourceUrl
const {
  resolvedUrl,
  loading,
  error,
  retryOnce,
} = useAuthenticatedFileUrl(source, { enabled })

function emitProgress(ended = false) {
  const video = videoRef.value
  if (!video) return
  beforeUrlRenewalPosition.value = Math.floor(video.currentTime || 0)
  emit('video-progress', {
    currentTime: beforeUrlRenewalPosition.value,
    duration: Math.floor(video.duration || 0),
    ended,
  })
}

function restorePosition() {
  const video = videoRef.value
  if (!video) return
  const position = beforeUrlRenewalPosition.value || props.resumePosition || 0
  if (position > 0 && (!video.duration || position < video.duration - 2)) {
    video.currentTime = position
  }
  emitProgress()
}

async function handleVideoError(event: Event) {
  const video = event.currentTarget as HTMLVideoElement | null
  const failedUrl = video?.getAttribute('src') || ''
  if (!failedUrl || failedUrl !== resolvedUrl.value) return
  if (video) beforeUrlRenewalPosition.value = Math.floor(video.currentTime || 0)
  mediaFailed.value = false
  await retryOnce(failedUrl)
  if (failedUrl !== resolvedUrl.value) return
  if (error.value) mediaFailed.value = true
}

watch(
  () => props.sourceUrl,
  (nextSource, previousSource) => {
    if (nextSource === previousSource) return
    beforeUrlRenewalPosition.value = props.resumePosition || 0
    mediaFailed.value = false
  },
  { immediate: true },
)

watch(resolvedUrl, async (nextUrl, previousUrl) => {
  const sourceUnchanged = lastResolvedSource === props.sourceUrl
  lastResolvedSource = props.sourceUrl
  if (!nextUrl || nextUrl === previousUrl) return
  const video = videoRef.value
  if (video && previousUrl && sourceUnchanged) {
    beforeUrlRenewalPosition.value = Math.floor(video.currentTime || beforeUrlRenewalPosition.value)
  }
  mediaFailed.value = false
  await nextTick()
  videoRef.value?.load()
})

onBeforeUnmount(() => {
  const video = videoRef.value
  if (!video) return
  video.pause()
  video.removeAttribute('src')
  video.load()
})
</script>

<template>
  <div class="authenticated-video">
    <div v-if="mediaFailed" class="video-state">{{ error || '视频加载失败，请稍后重试。' }}</div>
    <div v-else-if="loading && !resolvedUrl" class="video-state">视频加载中，请稍候。</div>
    <div v-else-if="error && !resolvedUrl" class="video-state">{{ error }}</div>
    <video
      v-else-if="resolvedUrl"
      :key="resolvedUrl"
      ref="videoRef"
      class="lesson-video"
      :src="resolvedUrl"
      controls
      preload="metadata"
      @loadedmetadata="restorePosition"
      @timeupdate="emitProgress()"
      @ended="emitProgress(true)"
      @error="handleVideoError"
    />
    <div v-else class="video-state">视频暂时无法播放。</div>
  </div>
</template>

<style scoped>
.authenticated-video,
.lesson-video {
  width: 100%;
}

.lesson-video {
  display: block;
}

.video-state {
  padding: 32px 16px;
  text-align: center;
  color: var(--color-text-muted);
}
</style>

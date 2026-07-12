<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuthenticatedFileUrl } from '@/composables/useAuthenticatedFileUrl'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  fileId?: number | null
  fallbackUrl?: string
}>(), {
  fileId: null,
  fallbackUrl: '',
})

const sourceUrl = computed(() => props.fileId ? `/api/files/${props.fileId}` : props.fallbackUrl)
const enabled = computed(() => Boolean(sourceUrl.value))
const imageFailed = ref(false)
const { resolvedUrl, error, retryOnce } = useAuthenticatedFileUrl(sourceUrl, { enabled })

watch(sourceUrl, () => {
  imageFailed.value = false
})

watch(resolvedUrl, (nextUrl, previousUrl) => {
  if (nextUrl && nextUrl !== previousUrl) imageFailed.value = false
})

async function handleImageError(event: Event) {
  const image = event.currentTarget as HTMLImageElement | null
  const failedUrl = image?.getAttribute('src') || ''
  if (!failedUrl || failedUrl !== resolvedUrl.value) return

  imageFailed.value = false
  await retryOnce(failedUrl)
  if (failedUrl !== resolvedUrl.value) return
  if (error.value) imageFailed.value = true
}
</script>

<template>
  <img
    v-if="resolvedUrl && !imageFailed"
    v-bind="$attrs"
    :src="resolvedUrl"
    @error="handleImageError"
  />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  src?: string
  title?: string
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const playing = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(1)
const playbackRate = ref(1)
const showRates = ref(false)

const rates = [0.5, 0.75, 1, 1.25, 1.5, 2]

function togglePlay() {
  if (!videoRef.value) return
  if (videoRef.value.paused) {
    videoRef.value.play()
    playing.value = true
  } else {
    videoRef.value.pause()
    playing.value = false
  }
}

function onTimeUpdate() {
  if (!videoRef.value) return
  currentTime.value = videoRef.value.currentTime
}

function onLoadedMetadata() {
  if (!videoRef.value) return
  duration.value = videoRef.value.duration
}

function seek(e: MouseEvent) {
  if (!videoRef.value || !duration.value) return
  const bar = e.currentTarget as HTMLElement
  const rect = bar.getBoundingClientRect()
  const ratio = (e.clientX - rect.left) / rect.width
  videoRef.value.currentTime = ratio * duration.value
}

function setRate(rate: number) {
  if (!videoRef.value) return
  videoRef.value.playbackRate = rate
  playbackRate.value = rate
  showRates.value = false
}

function setVolume(e: Event) {
  if (!videoRef.value) return
  const val = Number((e.target as HTMLInputElement).value)
  videoRef.value.volume = val
  volume.value = val
}

function toggleFullscreen() {
  const el = videoRef.value?.parentElement
  if (!el) return
  if (document.fullscreenElement) {
    document.exitFullscreen()
  } else {
    el.requestFullscreen()
  }
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

watch(() => props.src, () => {
  playing.value = false
  currentTime.value = 0
  duration.value = 0
})
</script>

<template>
  <div class="video-player">
    <template v-if="src">
      <video
        ref="videoRef"
        :src="src"
        class="video-element"
        @timeupdate="onTimeUpdate"
        @loadedmetadata="onLoadedMetadata"
        @ended="playing = false"
        @click="togglePlay"
      />

      <!-- Controls overlay -->
      <div class="controls-overlay">
        <!-- Progress bar -->
        <div class="progress-bar" @click="seek">
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: duration ? (currentTime / duration * 100) + '%' : '0%' }"></div>
          </div>
        </div>

        <div class="controls-row">
          <button class="ctrl-btn" @click.stop="togglePlay">
            <svg v-if="!playing" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z"/>
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>
          </button>

          <span class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>

          <div class="rate-control">
            <button class="ctrl-btn rate-btn" @click.stop="showRates = !showRates">
              {{ playbackRate }}x
            </button>
            <div v-if="showRates" class="rate-menu">
              <button v-for="r in rates" :key="r" class="rate-option"
                      :class="{ active: playbackRate === r }" @click.stop="setRate(r)">
                {{ r }}x
              </button>
            </div>
          </div>

          <div class="volume-control">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
            <input type="range" min="0" max="1" step="0.1" :value="volume"
                   class="volume-slider" @input="setVolume" />
          </div>

          <button class="ctrl-btn" @click.stop="toggleFullscreen">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
          </button>
        </div>
      </div>
    </template>

    <div v-else class="placeholder">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
        <path d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"
              stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <p>教师暂未上传视频</p>
    </div>
  </div>
</template>

<style scoped>
.video-player {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 16 / 9;
}

.video-element {
  width: 100%;
  height: 100%;
  display: block;
  cursor: pointer;
}

.controls-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  padding: var(--space-xl) var(--space-md) var(--space-sm);
}

.progress-bar {
  cursor: pointer;
  padding: var(--space-xs) 0;
}

.progress-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary-light);
  border-radius: 2px;
  transition: width 0.1s linear;
}

.controls-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.ctrl-btn {
  color: white;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity var(--duration-fast);
}

.ctrl-btn:hover {
  opacity: 0.8;
}

.time-display {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.8);
  font-family: var(--font-mono);
  margin-left: var(--space-xs);
}

.rate-control {
  position: relative;
  margin-left: auto;
}

.rate-btn {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-sm);
}

.rate-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: var(--space-xs);
  background: rgba(0, 0, 0, 0.9);
  border-radius: var(--radius-sm);
  padding: var(--space-xs);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rate-option {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.7);
  padding: 4px 12px;
  border-radius: 4px;
  text-align: center;
  white-space: nowrap;
}

.rate-option:hover,
.rate-option.active {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.8);
}

.volume-slider {
  width: 60px;
  height: 4px;
  accent-color: white;
}

.placeholder {
  width: 100%;
  height: 100%;
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

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import HeroSection from '../components/home/HeroSection.vue'
import ModuleShowcase from '../components/home/ModuleShowcase.vue'
import CoursePreview from '../components/home/CoursePreview.vue'
import StatsSection from '../components/home/StatsSection.vue'
import CtaSection from '../components/home/CtaSection.vue'
import AnnouncementPopup from '../components/AnnouncementPopup.vue'

const observer = ref<IntersectionObserver | null>(null)
const fadeTimeouts = new Map<Element, ReturnType<typeof setTimeout>>()

onMounted(() => {
  observer.value = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const el = entry.target as HTMLElement
        const delay = el.dataset.fadeDelay || '0s'
        const delayMs = parseFloat(delay) * 1000

        // 清除该元素之前的未完成定时器
        if (fadeTimeouts.has(el)) {
          clearTimeout(fadeTimeouts.get(el))
          fadeTimeouts.delete(el)
        }

        if (entry.isIntersecting) {
          el.style.transitionDelay = delay
          el.setAttribute('data-visible', '')
        } else {
          el.style.transitionDelay = delay
          el.removeAttribute('data-visible')
        }

        // 动画完成后清除 transitionDelay，避免影响 hover 过渡
        const timeout = setTimeout(() => {
          el.style.transitionDelay = ''
          fadeTimeouts.delete(el)
        }, delayMs + 700)
        fadeTimeouts.set(el, timeout)
      })
    },
    { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
  )

  document.querySelectorAll('.fade-up').forEach((el) => {
    observer.value?.observe(el)
  })
})

onUnmounted(() => {
  fadeTimeouts.forEach((timeout) => clearTimeout(timeout))
  fadeTimeouts.clear()
  observer.value?.disconnect()
})
</script>

<template>
  <div class="home">
    <HeroSection />
    <ModuleShowcase />
    <CoursePreview />
    <StatsSection />
    <CtaSection />
    <AnnouncementPopup />
  </div>
</template>

<style scoped>
.home {
  overflow: hidden;
}
</style>

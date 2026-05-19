<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import HeroSection from '../components/home/HeroSection.vue'
import ModuleShowcase from '../components/home/ModuleShowcase.vue'
import CoursePreview from '../components/home/CoursePreview.vue'
import StatsSection from '../components/home/StatsSection.vue'
import CtaSection from '../components/home/CtaSection.vue'
import AnnouncementPopup from '../components/AnnouncementPopup.vue'

const router = useRouter()

const observer = ref<IntersectionObserver | null>(null)

onMounted(() => {
  observer.value = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible')
        }
      })
    },
    { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
  )

  document.querySelectorAll('.fade-up').forEach((el) => {
    observer.value?.observe(el)
  })
})

onUnmounted(() => {
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

<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import BackToTop from './components/BackToTop.vue'

const route = useRoute()
const useTransition = computed(() => !route.path.startsWith('/admin') && !route.path.startsWith('/teacher'))
</script>

<template>
  <AppHeader />
  <main>
    <RouterView v-slot="{ Component, route: viewRoute }">
      <template v-if="Component">
        <Transition v-if="useTransition" name="page-fade">
          <component :is="Component" :key="viewRoute.fullPath" />
        </Transition>
        <component v-else :is="Component" :key="viewRoute.fullPath" />
      </template>
    </RouterView>
  </main>
  <AppFooter />
  <BackToTop />
</template>

<style scoped>
main {
  min-height: calc(100vh - 64px - 200px);
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
</style>

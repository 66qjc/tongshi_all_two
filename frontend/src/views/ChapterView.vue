<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getChapterContents } from '@/api/chapter'
import VideoPlayer from './content/VideoPlayer.vue'
import PdfViewer from './content/PdfViewer.vue'

const route = useRoute()
const router = useRouter()
const chapterId = computed(() => Number(route.params.chapterId) || 1)

interface ChapterContent {
  id: number
  chapter_id: number
  type: 'video' | 'pdf'
  title: string
  url: string
  duration?: string
  pages?: number
}

const contents = ref<ChapterContent[]>([])
const chapterTitle = ref('加载中...')
const loading = ref(true)

async function fetchContents() {
  loading.value = true
  try {
    const data = await getChapterContents(chapterId.value)
    contents.value = data
    if (data.length > 0 && data[0].chapter) {
      chapterTitle.value = data[0].chapter
    } else {
      chapterTitle.value = `第 ${String(chapterId.value).padStart(2, '0')} 章`
    }
    selectedId.value = null
  } finally {
    loading.value = false
  }
}

watch(chapterId, fetchContents, { immediate: true })

const selectedId = ref<number | null>(null)

const selectedContent = computed(() => {
  if (selectedId.value) {
    return contents.value.find(c => c.id === selectedId.value)
  }
  return contents.value[0] || null
})

function selectContent(id: number) {
  selectedId.value = id
}
</script>

<template>
  <div class="chapter-page">
    <!-- Header -->
    <section class="chapter-hero">
      <div class="container">
        <button class="back-btn" @click="router.push('/learn')">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          返回课程列表
        </button>
        <div class="chapter-info">
          <span class="chapter-num">第 {{ String(chapterId).padStart(2, '0') }} 章</span>
          <h1>{{ chapterTitle }}</h1>
        </div>
      </div>
    </section>

    <!-- Content area -->
    <section class="content-section">
      <div class="container">
        <div class="content-layout">
          <!-- Sidebar: content list -->
          <aside class="content-sidebar">
            <h3 class="sidebar-title">课程目录</h3>
            <div class="content-list">
              <div
                v-for="item in contents"
                :key="item.id"
                class="content-item"
                :class="{ active: selectedContent?.id === item.id }"
                @click="selectContent(item.id)"
              >
                <span class="content-type-icon">
                  <svg v-if="item.type === 'video'" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 2l5 5h-5V4z"/>
                  </svg>
                </span>
                <div class="content-info">
                  <span class="content-title">{{ item.title }}</span>
                  <span class="content-meta">
                    {{ item.type === 'video' ? item.duration : `${item.pages} 页` }}
                  </span>
                </div>
              </div>
            </div>

            <div v-if="contents.length > 0" class="sidebar-footer">
              共 {{ contents.length }} 个资料
            </div>
          </aside>

          <!-- Main: player area -->
          <main class="content-main">
            <div v-if="selectedContent" class="player-wrapper">
              <h2 class="player-title">{{ selectedContent.title }}</h2>
              <VideoPlayer
                v-if="selectedContent.type === 'video'"
                :src="selectedContent.url || undefined"
                :title="selectedContent.title"
              />
              <PdfViewer
                v-else
                :src="selectedContent.url || undefined"
                :title="selectedContent.title"
              />
            </div>
            <div v-else class="empty-state">
              <p>暂无课程内容</p>
            </div>
          </main>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.chapter-page {
  padding-top: 64px;
  min-height: 100vh;
  background: var(--color-bg-alt);
}

.chapter-hero {
  padding: var(--space-xl) 0;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-md);
  transition: color var(--duration-fast);
}

.back-btn:hover {
  color: var(--color-learn);
}

.chapter-info {
  display: flex;
  align-items: baseline;
  gap: var(--space-md);
}

.chapter-num {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-learn);
  background: var(--color-learn-bg);
  padding: 0.2rem 0.8rem;
  border-radius: var(--radius-full);
}

.chapter-info h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
}

.content-section {
  padding: var(--space-xl) 0;
}

.content-layout {
  display: flex;
  gap: var(--space-xl);
  align-items: flex-start;
}

.content-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  position: sticky;
  top: 80px;
}

.sidebar-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-md);
}

.content-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.content-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--duration-fast);
  border-left: 3px solid transparent;
}

.content-item:hover {
  background: var(--color-learn-bg);
}

.content-item.active {
  background: var(--color-learn-bg);
  border-left-color: var(--color-learn);
}

.content-type-icon {
  color: var(--color-text-muted);
  margin-top: 2px;
  flex-shrink: 0;
}

.content-item.active .content-type-icon {
  color: var(--color-learn);
}

.content-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.content-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.content-meta {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.sidebar-footer {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.content-main {
  flex: 1;
  min-width: 0;
}

.player-wrapper {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
}

.player-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
}

.empty-state {
  text-align: center;
  padding: var(--space-4xl) 0;
  color: var(--color-text-muted);
  font-size: 1rem;
}

@media (max-width: 768px) {
  .content-layout {
    flex-direction: column;
  }

  .content-sidebar {
    width: 100%;
    position: static;
  }

  .chapter-info {
    flex-direction: column;
    gap: var(--space-sm);
  }
}
</style>

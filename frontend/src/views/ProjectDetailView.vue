<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProject, toggleLike as apiToggleLike, type Project } from '@/api/project'

const route = useRoute()
const router = useRouter()

const project = ref<Project | null>(null)
const loading = ref(true)
const liked = ref(false)
const relatedProjects = ref<{ id: number; title: string; author: string }[]>([])

const projectId = computed(() => Number(route.params.id))

onMounted(async () => {
  try {
    project.value = await getProject(projectId.value)
  } finally {
    loading.value = false
  }
})

async function toggleLike() {
  if (!project.value || liked.value) return
  const result = await apiToggleLike(project.value.id)
  if (result.liked && project.value) {
    project.value.likes = result.likes
    liked.value = true
  }
}
</script>

<template>
  <div class="detail-page">
    <div class="container">
      <button class="back-btn" @click="router.push('/create')">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M16 10H4m4-4l-4 4 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回作品列表
      </button>

      <div v-if="project" class="detail-content">
        <!-- Image placeholder -->
        <div class="project-image">
          <div class="image-placeholder">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>作品图片</span>
          </div>
        </div>

        <!-- Title & like -->
        <div class="project-header">
          <div>
            <h1>{{ project.title }}</h1>
            <p class="project-author">{{ project.author_name }} · {{ project.major }}</p>
          </div>
          <button class="like-btn" :class="{ liked }" @click="toggleLike">
            <svg width="20" height="20" viewBox="0 0 24 24" :fill="liked ? 'currentColor' : 'none'">
              <path d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ project.likes }}
          </button>
        </div>

        <!-- Description -->
        <section class="detail-section">
          <h3>作品介绍</h3>
          <p>{{ project.description }}</p>
        </section>

        <!-- Tags -->
        <section class="detail-section">
          <h3>技术栈</h3>
          <div class="tags">
            <span v-for="tag in project.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </section>

        <!-- Video -->
        <section v-if="project.video_url" class="detail-section">
          <h3>演示视频</h3>
          <a :href="project.video_url" target="_blank" rel="noopener" class="video-link">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            观看演示视频
          </a>
        </section>

        <!-- External link -->
        <section v-if="project.link_url" class="detail-section">
          <h3>项目链接</h3>
          <a :href="project.link_url" target="_blank" rel="noopener" class="external-link">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"
                    stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ project.link_url }}
          </a>
        </section>

        <!-- Related projects -->
        <section v-if="relatedProjects.length > 0" class="detail-section">
          <h3>相关作品</h3>
          <div class="related-grid">
            <div
              v-for="rp in relatedProjects"
              :key="rp.id"
              class="related-card"
              @click="router.push(`/create/project/${rp.id}`)"
            >
              <div class="related-image">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
                        stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <div class="related-info">
                <h4>{{ rp.title }}</h4>
                <p>{{ rp.author }}</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div v-else class="not-found">
        <h2>作品未找到</h2>
        <p>该作品可能已被移除或链接无效</p>
        <button class="btn-back" @click="router.push('/create')">返回作品列表</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-page {
  padding-top: 80px;
  padding-bottom: var(--space-3xl);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xl);
  transition: color var(--duration-fast);
}

.back-btn:hover {
  color: var(--color-create);
}

.project-image {
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-xl);
}

.image-placeholder {
  aspect-ratio: 16 / 9;
  background: var(--color-bg-alt);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.project-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-xl);
}

.project-header h1 {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-xs);
}

.project-author {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.like-btn {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast);
  flex-shrink: 0;
}

.like-btn:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.like-btn.liked {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
}

.like-btn.liked svg {
  animation: heartBeat 0.4s var(--ease-spring);
}

@keyframes heartBeat {
  0% { transform: scale(1); }
  30% { transform: scale(1.35); }
  60% { transform: scale(0.9); }
  100% { transform: scale(1); }
}

.detail-section {
  margin-bottom: var(--space-xl);
}

.detail-section h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-md);
}

.detail-section p {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.tag {
  padding: 0.3rem 0.8rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-create);
  background: var(--color-create-bg);
  border-radius: var(--radius-full);
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.video-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.6rem 1.2rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-create);
  background: var(--color-create-bg);
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.video-link:hover {
  background: rgba(245, 158, 11, 0.12);
}

.external-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 0.6rem 1.2rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-primary);
  background: var(--color-primary-glow);
  border: 1px solid rgba(79, 70, 229, 0.15);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
  word-break: break-all;
}

.external-link:hover {
  background: rgba(79, 70, 229, 0.12);
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
}

.related-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.related-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.related-image {
  aspect-ratio: 16 / 10;
  background: var(--color-bg-alt);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.related-info {
  padding: var(--space-md);
}

.related-info h4 {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 2px;
}

.related-info p {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.not-found {
  text-align: center;
  padding: var(--space-4xl) 0;
}

.not-found h2 {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.not-found p {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-xl);
}

.btn-back {
  padding: 0.6rem 1.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: var(--color-create);
  border-radius: var(--radius-full);
}

@media (max-width: 768px) {
  .related-grid {
    grid-template-columns: 1fr;
  }

  .project-header {
    flex-direction: column;
    gap: var(--space-md);
  }
}
</style>
